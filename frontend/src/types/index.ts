/**
 * TypeScript 类型定义
 *
 * 定义前端所有核心数据结构，与后端 API 的 JSON 结构一一对应。
 * 包括：消息、会话、Agent、模型、技能、文件信息、SSE 事件、通知配置。
 *
 * 优化记录：
 * - [强类型] 新增 ModelCreate/ModelUpdate/SkillCreate/SkillUpdate 接口，
 *   替代 api.ts 中的 any 类型，提升类型安全性
 */

/** 参与的 Agent 信息 */
export interface AgentInfo {
  name: string;                  // Agent 名称
  model_id: string;              // 使用的模型 ID
  role: "manager" | "worker";    // 角色：主管或员工
}

/** 聊天消息 */
export interface Message {
  id: string;                    // 消息唯一 ID
  role: "user" | "assistant";    // 角色：用户 或 AI 助手
  content: string;               // 消息内容（Markdown 格式）
  thinking?: string;             // 推理模型的思考过程（仅 supports_thinking 模型）
  timestamp: string;             // 发送时间（ISO 格式字符串）
  files?: FileInfo[];            // 附件文件列表
  skill_used?: string;           // 触发的技能 ID
  skill_name?: string;           // 触发的技能名称
  agents?: AgentInfo[];          // 参与的 Agent 列表
  isError?: boolean;             // 是否为错误消息（用于分级展示）
}

/** 会话 */
export interface Session {
  id: string;                    // 会话唯一 ID
  title: string;                 // 会话标题
  created_at: string;            // 创建时间
  updated_at: string;            // 最后更新时间
  pinned: boolean;               // 是否置顶
  pinned_at?: string;            // 置顶时间
  message_count?: number;        // 消息数量
}

/** AI Agent（员工）配置 */
export interface Agent {
  id: string;                    // Agent 唯一 ID（默认为 "default"）
  name: string;                  // 显示名称
  avatar: string;                // 头像（文字或 emoji）
  description: string;           // Agent 描述
  role: string;                  // 角色描述（如"图片生成分"、"数据分析师"）
  model_provider: string;        // 默认模型提供商（zhipu/deepseek/openai 等）
  model_id: string;              // 默认模型 ID
  temperature: number;           // 温度参数（0~1，越高越随机）
  enable_thinking: boolean;       // 是否启用深度思考
  custom_api_key?: string;       // 自定义 API Key（覆盖全局配置）
  custom_base_url?: string;      // 自定义 API Base URL
  is_default: boolean;           // 是否为默认 Agent（不可删除）
  capabilities?: string[];       // 模型能力标签（从后端动态获取）
  skills?: string[];             // 绑定的技能 ID 列表（如 ["image_gen", "tts"]）
}

/** LLM 模型配置 */
export interface Model {
  id: string;                    // 模型唯一 ID
  name: string;                  // 显示名称
  provider: string;              // 提供商（zhipu/deepseek/dashscope/openai/moonshot）
  model_id: string;              // 模型标识（如 glm-4-flash-250414、deepseek-chat）
  base_url: string;              // API Base URL
  description: string;           // 模型描述
  supports_thinking: boolean;    // 是否支持思考/推理输出
  builtin: boolean;              // 是否为系统内置模型
  api_key?: string;              // 自定义 API Key（仅自定义模型）
  capabilities?: string[];       // 能力标签（text/vision/ocr 等）
}

/** 技能配置项选项（select 类型） */
export interface SkillConfigOption {
  value: string;
  label: string;
}

/** 技能配置项定义 */
export interface SkillConfigSchemaItem {
  key: string;
  label: string;
  description: string;
  type: "text" | "password" | "select" | "number" | "boolean";
  required: boolean;
  env_hint?: string;
  default?: string;
  options?: SkillConfigOption[];
}

/** 技能配置 */
export interface Skill {
  id: string;
  name: string;
  description: string;
  icon: string;
  triggers: string[];
  examples: string[];
  builtin: boolean;
  enabled: boolean;
  config_schema?: SkillConfigSchemaItem[];
  config?: Record<string, string>;
}

/** 上传文件信息 */
export interface FileInfo {
  file_id: string;               // 文件唯一 ID（UUID 前 12 位 + 扩展名）
  filename: string;              // 原始文件名
  size: number;                  // 文件大小（字节）
  type: string;                  // 文件类型（image/document/spreadsheet/text/audio/video）
  url: string;                   // 文件访问 URL（/uploads/xxx）
}

/** SSE 事件 — 流式聊天的每个数据块 */
export interface SSEEvent {
  type: "thinking" | "content" | "skill" | "done" | "error" | "worker" | "tool_start" | "user_message" | "title";  // 事件类型
  content?: string;              // 内容片段（type=content 时）
  skill_used?: string;           // 触发的技能 ID（type=skill 时）
  skill_name?: string;           // 触发的技能名称（type=skill 时）
  agent_name?: string;           // Agent 名称（type=done 时）
  model_id?: string;             // 使用的模型 ID（type=done 时）
  title?: string;                // 会话标题（type=done 时，用于自动命名）
  worker_name?: string;          // 员工名称（type=worker 时）
  worker_model?: string;         // 员工使用的模型（type=worker 时）
  tool_name?: string;            // 工具名称（type=tool_start 时）
  agents?: AgentInfo[];          // 参与的 Agent 列表（type=done 时）
}

/** 创建自定义模型的请求参数 */
export interface ModelCreate {
  name: string;
  provider: string;
  model_id: string;
  base_url: string;
  api_key?: string;
  description?: string;
  supports_thinking?: boolean;
  capabilities?: string[];
}

/** 更新自定义模型的请求参数 */
export interface ModelUpdate {
  name?: string;
  provider?: string;
  model_id?: string;
  base_url?: string;
  api_key?: string;
  supports_thinking?: boolean;
  description?: string;
  capabilities?: string[];
}

/** 创建自定义技能的请求参数 */
export interface SkillCreate {
  name: string;
  description: string;
  icon?: string;
  triggers: string[];
  examples?: string[];
  handler_code?: string;
}

/** 更新自定义技能的请求参数 */
export interface SkillUpdate {
  name?: string;
  description?: string;
  icon?: string;
  triggers?: string[];
  examples?: string[];
  handler_code?: string;
}
