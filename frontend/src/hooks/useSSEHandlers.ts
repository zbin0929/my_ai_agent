import { useChatStore } from "@/store/chatStore";
import { useOfficeStore, getNextDeskPosition, getAgentColor } from "@/store/officeStore";
import { api } from "@/lib/api";

let _msgIdCounter = 0;
function _genId() {
  _msgIdCounter += 1;
  return `${Date.now()}-${_msgIdCounter}-${Math.random().toString(36).slice(2, 8)}`;
}

let _workerIndex = 0;

interface SSEHandlerOptions {
  sessionId: string;
  shouldAutoTitle: boolean;
  userText: string;
  errorFallback: string;
}

function applyTitle(sessionId: string, title: string) {
  useChatStore.getState().updateSessionTitle(sessionId, title);
  api.sessions.update(sessionId, { title }).then(() => {
    api.sessions.list().then((data) => {
      useChatStore.getState().setSessions(data.sessions || []);
    }).catch(() => {});
  }).catch(() => {});
}

function ensureWorkerAgent(workerName: string): string | null {
  const o = useOfficeStore.getState();
  const existing = Object.values(o.agents).find((a) => a.name === workerName);
  if (existing) return existing.id;

  const pos = getNextDeskPosition();
  const color = getAgentColor(_workerIndex);
  const id = `worker-${_workerIndex}`;
  _workerIndex++;

  o.spawnAgent(id, workerName, color, pos.x, pos.y);
  return id;
}

export function createSSEHandlers(opts: SSEHandlerOptions) {
  const { sessionId, shouldAutoTitle, userText, errorFallback } = opts;

  let _currentWorkerId: string | null = null;

  const onEvent = (event: any) => {
    const s = useChatStore.getState();
    const o = useOfficeStore.getState();

    switch (event.type) {
      case "thinking":
        s.appendThinking(event.content || "");
        if (_currentWorkerId) {
          o.setAgentSpeech(_currentWorkerId, (event.content || "").slice(0, 60) + "...", "thinking");
        }
        break;
      case "content":
        s.appendContent(event.content || "");
        break;
      case "skill":
        s.setCurrentSkill(event.content || null);
        break;
      case "worker": {
        s.setPipelineInfo({
          agentName: event.worker_name || "",
          modelId: event.worker_model || "",
          skillName: "",
        });
        const workerName = event.worker_name || "";
        const workerId = ensureWorkerAgent(workerName);
        if (workerId) {
          _currentWorkerId = workerId;
          o.setActiveWorker(workerId);
          o.setAgentAnim(workerId, "type");

          if (o.managerId) {
            o.setAgentSpeech(o.managerId, `派发 → ${workerName}`, "task");
          }

          setTimeout(() => {
            const latest = useOfficeStore.getState();
            if (latest.managerId) {
              latest.setAgentAnim(latest.managerId, "idle");
              latest.setAgentSpeech(latest.managerId, null);
            }
          }, 1200);
        }
        break;
      }
      case "tool_start":
        s.setCurrentSkill(event.tool_name || null);
        if (_currentWorkerId) {
          o.setAgentAnim(_currentWorkerId, "type");
          o.setAgentSpeech(_currentWorkerId, event.tool_name || "工作中...", "thinking");
        }
        break;
      case "done": {
        const st = useChatStore.getState();
        st.finalizeStreamMessage({
          skill_used: event.skill_used,
          skill_name: event.skill_name,
          agents: event.agents,
        });
        if (event.agent_name || event.model_id) {
          st.setPipelineInfo({
            agentName: event.agent_name || "",
            modelId: event.model_id || "",
            skillName: event.skill_name || "",
          });
        }
        if (shouldAutoTitle && sessionId) {
          if (event.title) {
            applyTitle(sessionId, event.title);
          } else {
            const snippetTitle = userText.slice(0, 30) + (userText.length > 30 ? "..." : "");
            st.updateSessionTitle(sessionId, snippetTitle);
          }
        }
        if (_currentWorkerId) {
          o.setAgentAnim(_currentWorkerId, "celebrate");
          o.setAgentSpeech(_currentWorkerId, "完成!", "result");
          setTimeout(() => {
            const latest = useOfficeStore.getState();
            if (latest.agents[_currentWorkerId!]?.anim === "celebrate") {
              latest.setAgentAnim(_currentWorkerId!, "idle");
              latest.setAgentSpeech(_currentWorkerId!, null);
            }
          }, 3000);
        }
        o.setActiveWorker(null);
        _currentWorkerId = null;
        break;
      }
      case "title":
        if (shouldAutoTitle && sessionId && event.title) {
          applyTitle(sessionId, event.title);
        }
        break;
      case "error": {
        const st = useChatStore.getState();
        st.addMessage({
          id: _genId(),
          role: "assistant",
          content: event.content || errorFallback,
          timestamp: new Date().toISOString(),
          isError: true,
        });
        st.setIsStreaming(false);
        st.resetStreaming();
        if (_currentWorkerId) {
          o.setAgentAnim(_currentWorkerId, "error");
          o.setAgentSpeech(_currentWorkerId, event.content || "出错了", "error");
          setTimeout(() => {
            const latest = useOfficeStore.getState();
            if (latest.agents[_currentWorkerId!]?.anim === "error") {
              latest.setAgentAnim(_currentWorkerId!, "idle");
              latest.setAgentSpeech(_currentWorkerId!, null);
            }
          }, 5000);
        }
        o.setActiveWorker(null);
        _currentWorkerId = null;
        break;
      }
    }
  };

  const onError = (err: Error) => {
    const st = useChatStore.getState();
    st.addMessage({
      id: _genId(),
      role: "assistant",
      content: err.message || errorFallback,
      timestamp: new Date().toISOString(),
      isError: true,
    });
    st.setIsStreaming(false);
    st.resetStreaming();
  };

  const onDone = () => {
    const st = useChatStore.getState();
    if (st.isStreaming) st.finalizeStreamMessage();
  };

  return { onEvent, onError, onDone };
}
