/**
 * API 客户端模块
 *
 * 封装所有与后端 API 的通信逻辑，包括：
 * - request()：通用请求函数，处理响应和错误
 * - api 对象：按模块组织所有 API 调用（会话、Agent、模型、技能、通知、文件上传）
 * - streamChat()：SSE 流式聊天函数，逐步读取 AI 回复
 *
 * 优化记录：
 * - [重试机制] request() 支持自动重试（最多 2 次），5xx 和超时自动重试，4xx 不重试
 * - [超时控制] 普通请求 30s 超时，流式请求 120s 超时，使用 AbortController 实现
 * - [取消支持] streamChat() 支持外部 abortSignal 取消正在进行的流式请求
 * - [强类型] 所有 API 方法使用泛型返回值和强类型参数，消除 any 类型
 */

const API_BASE = "/api";

function getStreamBase(): string {
  if (typeof window !== "undefined") {
    const be = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (be) return be;
    if (window.location.port === "3000") return "http://localhost:8000/api";
  }
  return API_BASE;
}

const REQUEST_TIMEOUT = 30000; // 30s timeout for normal requests
const MAX_RETRIES = 2;

/** 解析后端错误响应，提取用户友好的错误消息 */
async function parseErrorResponse(res: Response): Promise<string> {
  try {
    const data = await res.json();
    return data.message || data.detail || "请求失败，请稍后再试。";
  } catch {
    return `请求失败 (${res.status})，请稍后再试。`;
  }
}

/** 通用请求函数 — 封装 fetch，自动处理 JSON 序列化、超时和重试 */
async function request<T>(path: string, options?: RequestInit, retries = MAX_RETRIES): Promise<T> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);

    try {
      const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        const msg = await parseErrorResponse(res);
        // 4xx errors should not be retried
        if (res.status >= 400 && res.status < 500) {
          throw new Error(msg);
        }
        // 5xx errors: retry if attempts remain
        if (attempt < retries) {
          await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
          continue;
        }
        throw new Error(msg);
      }
      return res.json();
    } catch (err) {
      clearTimeout(timeoutId);
      if (err instanceof DOMException && err.name === "AbortError") {
        if (attempt < retries) {
          await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
          continue;
        }
        throw new Error("请求超时，请检查网络后重试。");
      }
      // Network errors: retry
      if (attempt < retries && err instanceof TypeError) {
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
        continue;
      }
      throw err;
    }
  }
  throw new Error("请求失败，请稍后再试。");
}

/** API 对象 — 按功能模块组织所有后端接口调用 */
export const api = {
  // 会话管理接口
  sessions: {
    list: () => request<{ sessions: import("@/types").Session[] }>("/sessions"),
    create: (title?: string) => request<import("@/types").Session>("/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    }),
    update: (id: string, data: { title?: string; pinned?: boolean }) =>
      request<import("@/types").Session>(`/sessions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    delete: (id: string) => request(`/sessions/${id}`, { method: "DELETE" }),
    clearAll: () => request<{ ok: boolean; deleted_count: number }>("/sessions", { method: "DELETE" }),
    getMessages: (id: string) => request<{ messages: import("@/types").Message[]; summary: string }>(`/sessions/${id}/messages`),
    exportMarkdown: async (id: string): Promise<Blob> => {
      const base = getStreamBase().replace("/api", "");
      const res = await fetch(`${base}/api/sessions/${id}/export?format=markdown`);
      if (!res.ok) throw new Error("Export failed");
      return res.blob();
    },
  },
  // 用量统计接口
  stats: {
    get: () => request<{
      total_sessions: number;
      total_messages: number;
      today_messages: number;
      week_messages: number;
      month_messages: number;
      top_models: { model: string; count: number }[];
      top_skills: { skill: string; count: number }[];
    }>("/stats"),
  },
  // Agent 管理接口
  agents: {
    /** 获取所有 Agent 列表 */
    list: () => request<{ agents: import("@/types").Agent[] }>("/agents"),
    /** 创建新 Agent */
    create: (data: Partial<import("@/types").Agent>) =>
      request<import("@/types").Agent>("/agents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    /** 更新 Agent 配置 */
    update: (id: string, data: Partial<import("@/types").Agent>) =>
      request<import("@/types").Agent>(`/agents/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    /** 删除 Agent（默认 Agent 不可删除） */
    delete: (id: string) => request(`/agents/${id}`, { method: "DELETE" }),
    /** 获取可绑定的技能列表 */
    availableSkills: () => request<{ skills: { id: string; name: string; description: string; icon: string }[] }>("/agents/available-skills"),
  },
  // 模型管理接口
  models: {
    /** 获取可用模型列表（已配置 API Key 的模型） */
    list: () => request<{ models: import("@/types").Model[] }>("/models"),
    /** 添加自定义模型 */
    create: (data: import("@/types").ModelCreate) =>
      request<import("@/types").Model>("/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    /** 更新自定义模型配置 */
    update: (id: string, data: import("@/types").ModelUpdate) =>
      request<import("@/types").Model>(`/models/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    /** 删除自定义模型 */
    delete: (id: string) => request(`/models/${id}`, { method: "DELETE" }),
    /** 测试模型连接是否正常 */
    test: (id: string) => request<{ success: boolean; message: string; capabilities?: string[] }>(`/models/${id}/test`, { method: "POST" }),
  },
  // 技能管理接口
  skills: {
    /** 获取所有技能列表（内置 + 自定义） */
    list: () => request<{ skills: import("@/types").Skill[] }>("/skills"),
    /** 创建自定义技能 */
    create: (data: import("@/types").SkillCreate) =>
      request<import("@/types").Skill>("/skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    /** 更新自定义技能 */
    update: (id: string, data: import("@/types").SkillUpdate) =>
      request<import("@/types").Skill>(`/skills/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }),
    /** 删除自定义技能 */
    delete: (id: string) => request(`/skills/${id}`, { method: "DELETE" }),
    /** 切换技能启用/禁用状态 */
    toggle: (id: string) => request(`/skills/${id}/toggle`, { method: "PATCH" }),
    /** 获取技能配置 */
    getConfig: (id: string) => request<{ skill_id: string; config_schema: import("@/types").SkillConfigSchemaItem[]; config: Record<string, string> }>(`/skills/${id}/config`),
    /** 保存技能配置 */
    saveConfig: (id: string, config: Record<string, string>) =>
      request<{ ok: boolean }>(`/skills/${id}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      }),
  },
  /** 文件上传 — 使用 FormData 发送，返回文件 ID 和访问 URL */
  upload: async (file: File): Promise<import("@/types").FileInfo> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/files/upload`, { method: "POST", body: formData });
    if (!res.ok) {
      let detail = "Upload failed";
      try {
        const errData = await res.json();
        detail = errData.detail || detail;
      } catch {}
      throw new Error(detail);
    }
    return res.json();
  },
};

const configApi = {
  search: {
    get: (): Promise<{ provider: string; api_key_configured: boolean; api_key_masked: string }> =>
      request("/config/search"),
    update: (data: { provider: string; api_key: string }): Promise<{ provider: string; api_key_configured: boolean; api_key_masked: string }> =>
      request("/config/search", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
  },
  providers: {
    get: (): Promise<{ providers: ProviderConfig[] }> =>
      request("/config/providers"),
    update: (providerId: string, data: { api_key: string }): Promise<{ message: string }> =>
      request(`/config/providers/${providerId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
  },
};

export { configApi };

interface ProviderConfig {
  id: string;
  name: string;
  type: string;
  env_key: string;
  api_key_configured: boolean;
  api_key_masked: string;
  supports_search: boolean;
  base_url: string;
  models: { id: string; name: string }[];
}

/**
 * SSE 流式聊天
 *
 * 通过 POST /api/chat/stream 建立 SSE 连接，使用 ReadableStream 逐步读取 AI 回复。
 * 每个 SSE 事件是一个 JSON 对象，包含 type（content/done/skill）和对应数据。
 *
 * @param message - 用户输入的消息
 * @param sessionId - 当前会话 ID（为空时后端自动创建新会话）
 * @param agentId - 使用的 Agent ID
 * @param onEvent - SSE 事件回调（content=回复片段，done=完成，skill=技能触发）
 * @param onError - 错误回调
 * @param onDone - 完成回调
 * @param files - 附件文件路径列表
 * @param fileInfos - 附件文件元信息
 * @param mode - 回复模式：simple（简洁）或 think（深度思考）
 */
export async function streamChat(
  message: string,
  sessionId: string | null,
  agentId: string,
  onEvent: (event: import("@/types").SSEEvent) => void,
  onError: (err: Error) => void,
  onDone: () => void,
  files?: string[],
  fileInfos?: import("@/types").FileInfo[],
  mode?: "simple" | "think",
  abortSignal?: AbortSignal,
  enableSearch?: boolean
) {
  // 发送 POST 请求建立 SSE 连接，支持 120s 超时和外部取消
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120000);

  // 合并外部 abort signal
  if (abortSignal) {
    abortSignal.addEventListener("abort", () => controller.abort());
  }

  let res: Response;
  try {
    res = await fetch(`${getStreamBase()}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId, agent_id: agentId, files, file_infos: fileInfos, enable_thinking: mode === "think", enable_search: enableSearch || false }),
      signal: controller.signal,
    });
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof DOMException && err.name === "AbortError") {
      onError(new Error(abortSignal?.aborted ? "请求已取消" : "请求超时，请重试"));
    } else {
      onError(new Error("网络连接失败，请检查网络后重试"));
    }
    return;
  }

  clearTimeout(timeoutId);

  if (!res.ok) {
    const msg = await parseErrorResponse(res);
    onError(new Error(msg));
    return;
  }

  // 获取 ReadableStream reader 逐步读取响应
  const reader = res.body?.getReader();
  if (!reader) {
    onError(new Error("无法读取响应数据"));
    return;
  }

  const decoder = new TextDecoder();
  // 缓冲区：存储未完成的 SSE 行（可能一个 chunk 包含不完整的行）
  let buffer = "";

  let doneReceived = false;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // 将二进制数据解码为文本，追加到缓冲区
      buffer += decoder.decode(value, { stream: true });
      // 按换行符分割，最后一行可能不完整，保留在缓冲区
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      // 逐行处理 SSE 数据
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        // 去除 SSE "data:" 前缀
        let payload = trimmed;
        if (payload.startsWith("data:")) {
          payload = payload.slice(5).trim();
        }
        if (!payload) continue;
        try {
          const event: import("@/types").SSEEvent = JSON.parse(payload);
          onEvent(event);
          // 收到 done 事件表示 AI 回复主体结束，但继续读取后续事件（如异步生成的 title）
          if (event.type === "done") {
            doneReceived = true;
            onDone();
          }
          // 收到 title 事件（done 之后异步生成的标题），处理后结束流
          if (event.type === "title") {
            return;
          }
        } catch {}
      }
    }
    // 流正常结束（无 done 事件时才补调 onDone）
    if (!doneReceived) onDone();
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)));
  }
}
