"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useChatStore } from "@/store/chatStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useI18n } from "@/store/i18nStore";
import { api, streamChat } from "@/lib/api";
import type { FileInfo } from "@/types";

let messageIdCounter = 0;
function generateUniqueId() {
  messageIdCounter += 1;
  return `${Date.now()}-${messageIdCounter}-${Math.random().toString(36).slice(2, 8)}`;
}

function FileIcon({ type, className = "w-3.5 h-3.5" }: { type: string; className?: string }) {
  const cls = className;
  switch (type) {
    case "image":
      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><path d="M21 15l-5-5L5 21" /></svg>;
    case "document":
      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14,2 14,8 20,8" /></svg>;
    case "spreadsheet":
      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="3" y1="15" x2="21" y2="15" /><line x1="9" y1="3" x2="9" y2="21" /><line x1="15" y1="3" x2="15" y2="21" /></svg>;
    case "audio":
      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" /></svg>;
    case "video":
      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="2" y="4" width="20" height="16" rx="2" /><polygon points="10,8 16,12 10,16" /></svg>;
    default:
      return <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" /></svg>;
  }
}

export function InputBar() {
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [isFocused, setIsFocused] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionIndex, setMentionIndex] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const pendingMessageSentRef = useRef(false);
  const { t } = useI18n();
  const { agents } = useSettingsStore();

  const workers = agents.filter((a) => !a.is_default);

  const filteredWorkers = mentionQuery !== null
    ? workers.filter((a) => a.name.toLowerCase().includes(mentionQuery.toLowerCase()))
    : [];

  const {
    currentSessionId,
    messages,
    addMessage,
    setIsStreaming,
    setStreamingSessionId,
    appendContent,
    appendThinking,
    resetStreaming,
    setCurrentSkill,
    updateSessionTitle,
    setPipelineInfo,
    chatMode,
    setChatMode,
    enableSearch,
    setEnableSearch,
    pendingMessage,
    setPendingMessage,
    finalizeStreamMessage,
  } = useChatStore();

  const handleInputChange = useCallback((value: string) => {
    setInput(value);
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 300) + "px";
    }

    const cursorPos = textareaRef.current?.selectionStart ?? 0;
    const textBeforeCursor = value.slice(0, cursorPos);
    const atMatch = textBeforeCursor.match(/@(\S*)$/);
    if (atMatch) {
      setMentionQuery(atMatch[1]);
      setMentionIndex(0);
    } else {
      setMentionQuery(null);
    }
  }, []);

  const insertMention = useCallback((agentName: string) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = input.slice(0, cursorPos);
    const textAfterCursor = input.slice(cursorPos);
    const newBefore = textBeforeCursor.replace(/@\S*$/, `@${agentName} `);
    const newValue = newBefore + textAfterCursor;
    setInput(newValue);
    setMentionQuery(null);
    setTimeout(() => {
      const newPos = newBefore.length;
      textarea.setSelectionRange(newPos, newPos);
      textarea.focus();
    }, 0);
  }, [input]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || !currentSessionId) return;

    const fileIds = files.length > 0 ? files.map((f) => f.file_id) : undefined;
    const fileInfos = files.length > 0 ? files : undefined;

    const shouldAutoTitle = messages.length === 0;
    const userMsgId = generateUniqueId();

    setInput("");
    setFiles([]);
    setMentionQuery(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (textareaRef.current) textareaRef.current.style.height = "";

    if (shouldAutoTitle && currentSessionId) {
      const snippetTitle = text.length > 30 ? text.slice(0, 30) + "..." : text;
      updateSessionTitle(currentSessionId, snippetTitle);
    }

    addMessage({
      id: userMsgId,
      role: "user" as const,
      content: text,
      timestamp: new Date().toISOString(),
      files: fileInfos,
    });

    setIsStreaming(true);
    setStreamingSessionId(currentSessionId);
    resetStreaming();
    abortControllerRef.current = new AbortController();

    try {
      await streamChat(
        text,
        currentSessionId,
        "default",
        (event) => {
          if (event.type === "thinking") appendThinking(event.content || "");
          else if (event.type === "content") appendContent(event.content || "");
          else if (event.type === "skill") setCurrentSkill(event.content || null);
          else if (event.type === "worker") {
            setPipelineInfo({ agentName: event.worker_name || "", modelId: event.worker_model || "", skillName: "" });
          }
          else if (event.type === "tool_start") {
            setCurrentSkill(event.tool_name || null);
          }
          else if (event.type === "done") {
            finalizeStreamMessage({
              skill_used: event.skill_used,
              skill_name: event.skill_name,
              agents: event.agents,
            });
            if (event.agent_name || event.model_id) {
              setPipelineInfo({ agentName: event.agent_name || "", modelId: event.model_id || "", skillName: event.skill_name || "" });
            }
            if (shouldAutoTitle && currentSessionId) {
              const finalTitle = event.title || text.slice(0, 30) + (text.length > 30 ? "..." : "");
              updateSessionTitle(currentSessionId, finalTitle);
              api.sessions.update(currentSessionId, { title: finalTitle }).then(() => {
                api.sessions.list().then((data) => {
                  useChatStore.getState().setSessions(data.sessions || []);
                }).catch(() => {});
              }).catch(() => {});
            }
          } else if (event.type === "error") {
            useChatStore.getState().addMessage({
              id: generateUniqueId(),
              role: "assistant",
              content: event.content || t("errorDefault"),
              timestamp: new Date().toISOString(),
            });
            setIsStreaming(false);
            resetStreaming();
          }
        },
        (err) => {
          useChatStore.getState().addMessage({
            id: generateUniqueId(),
            role: "assistant",
            content: err.message || t("errorDefault"),
            timestamp: new Date().toISOString(),
          });
          setIsStreaming(false);
          resetStreaming();
        },
        () => {
          const s = useChatStore.getState();
          if (s.isStreaming) s.finalizeStreamMessage();
        },
        fileIds,
        fileInfos,
        chatMode,
        abortControllerRef.current?.signal,
        enableSearch
      );
    } catch (e: any) {
      useChatStore.getState().addMessage({
        id: generateUniqueId(),
        role: "assistant",
        content: e?.message || t("errorDefault"),
        timestamp: new Date().toISOString(),
      });
      setIsStreaming(false);
      resetStreaming();
    } finally {
      abortControllerRef.current = null;
    }
  }, [input, files, currentSessionId, messages.length, addMessage, setIsStreaming, setStreamingSessionId, appendContent, appendThinking, resetStreaming, setCurrentSkill, updateSessionTitle, setPipelineInfo, finalizeStreamMessage, chatMode, enableSearch, t]);

  useEffect(() => {
    if (!pendingMessage || !currentSessionId) return;
    if (pendingMessageSentRef.current) {
      setPendingMessage(null);
      return;
    }
    pendingMessageSentRef.current = true;
    const text = pendingMessage;
    setPendingMessage(null);

    const state = useChatStore.getState();
    const shouldAutoTitle = state.messages.length === 0;
    const userMsgId = generateUniqueId();

    if (shouldAutoTitle && currentSessionId) {
      const snippetTitle = text.length > 30 ? text.slice(0, 30) + "..." : text;
      state.updateSessionTitle(currentSessionId, snippetTitle);
    }

    state.addMessage({
      id: userMsgId,
      role: "user" as const,
      content: text,
      timestamp: new Date().toISOString(),
    });

    state.setIsStreaming(true);
    state.setStreamingSessionId(currentSessionId);
    state.resetStreaming();
    const ac = new AbortController();

    streamChat(
      text,
      currentSessionId,
      "default",
      (event) => {
        const s = useChatStore.getState();
        if (event.type === "thinking") s.appendThinking(event.content || "");
        else if (event.type === "content") s.appendContent(event.content || "");
        else if (event.type === "skill") s.setCurrentSkill(event.content || null);
        else if (event.type === "worker") {
          s.setPipelineInfo({ agentName: event.worker_name || "", modelId: event.worker_model || "", skillName: "" });
        }
        else if (event.type === "tool_start") {
          s.setCurrentSkill(event.tool_name || null);
        }
        else if (event.type === "done") {
          const st = useChatStore.getState();
          st.finalizeStreamMessage({
            skill_used: event.skill_used,
            skill_name: event.skill_name,
            agents: event.agents,
          });
          if (event.agent_name || event.model_id) {
            setPipelineInfo({ agentName: event.agent_name || "", modelId: event.model_id || "", skillName: event.skill_name || "" });
          }
          if (shouldAutoTitle && currentSessionId) {
            const finalTitle = event.title || text.slice(0, 30) + (text.length > 30 ? "..." : "");
            st.updateSessionTitle(currentSessionId, finalTitle);
            api.sessions.update(currentSessionId, { title: finalTitle }).then(() => {
              api.sessions.list().then((data) => {
                useChatStore.getState().setSessions(data.sessions || []);
              }).catch(() => {});
            }).catch(() => {});
          }
        } else if (event.type === "error") {
          const st = useChatStore.getState();
          st.addMessage({
            id: generateUniqueId(),
            role: "assistant",
            content: event.content || t("errorDefault"),
            timestamp: new Date().toISOString(),
          });
          st.setIsStreaming(false);
          st.resetStreaming();
        }
      },
      (err) => {
        const st = useChatStore.getState();
        st.addMessage({
          id: generateUniqueId(),
          role: "assistant",
          content: err.message || t("errorDefault"),
          timestamp: new Date().toISOString(),
        });
        st.setIsStreaming(false);
        st.resetStreaming();
      },
      () => {
        const st = useChatStore.getState();
        if (st.isStreaming) st.finalizeStreamMessage();
        pendingMessageSentRef.current = false;
      },
      undefined,
      undefined,
      state.chatMode,
      ac.signal,
      state.enableSearch
    );
  }, [pendingMessage, currentSessionId, t]);

  const handleFileUpload = async (fileList: FileList | null) => {
    if (!fileList) return;
    setUploadError(null);
    for (let i = 0; i < fileList.length; i++) {
      try {
        const result = await api.upload(fileList[i]);
        setFiles((prev) => [...prev, result]);
      } catch (e: any) {
        console.error("Upload failed:", e);
        setUploadError(e?.message || t("uploadFailed"));
        setTimeout(() => setUploadError(null), 5000);
      }
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (mentionQuery !== null && filteredWorkers.length > 0) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setMentionIndex((prev) => (prev + 1) % filteredWorkers.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setMentionIndex((prev) => (prev - 1 + filteredWorkers.length) % filteredWorkers.length);
        return;
      }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        insertMention(filteredWorkers[mentionIndex].name);
        return;
      }
      if (e.key === "Escape") {
        setMentionQuery(null);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasInput = input.trim().length > 0;

  return (
    <div className="w-full max-w-[720px] mx-auto px-4 pb-6">
      <input ref={fileInputRef} type="file" className="hidden" multiple onChange={(e) => handleFileUpload(e.target.files)} />
      <div
        className={
          "bg-[var(--bg)] rounded-[24px] border transition-all duration-200 " +
          (isFocused
            ? "border-[var(--accent)] shadow-[0_0_0_3px_rgba(79,70,229,0.1),0_4px_20px_rgba(0,0,0,0.08)]"
            : "border-[var(--border)] shadow-[0_2px_8px_rgba(0,0,0,0.04)]")
        }
      >
        {files.length > 0 && (
          <div className="flex gap-2 px-5 pt-3 pb-1 flex-wrap">
            {files.map((f) => (
              <div key={f.file_id} className="file-chip-v2">
                <span className="text-gray-400"><FileIcon type={f.type} /></span>
                <span className="max-w-[120px] truncate text-[13px]">{f.filename}</span>
                <button
                  onClick={() => setFiles(files.filter((x) => x.file_id !== f.file_id))}
                  className="text-[var(--text-3)] hover:text-[var(--red)] transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="px-5 py-3 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={t("placeholder")}
            rows={3}
            className="w-full resize-none text-[15px] text-[var(--text)] focus:outline-none min-h-[72px] max-h-[300px] bg-transparent placeholder:text-[var(--text-3)]"
            style={{ lineHeight: "1.6" }}
          />

          {mentionQuery !== null && filteredWorkers.length > 0 && (
            <div className="absolute left-5 bottom-full mb-1 w-64 bg-[var(--bg)] border border-[var(--border)] rounded-xl shadow-lg z-50 overflow-hidden">
              <div className="px-3 py-1.5 text-xs text-[var(--text-3)] border-b border-[var(--border)]">
                {t("selectWorker")}
              </div>
              {filteredWorkers.map((agent, idx) => (
                <div
                  key={agent.id}
                  className={`px-3 py-2 text-sm cursor-pointer flex items-center gap-2 ${
                    idx === mentionIndex ? "bg-[var(--accent-bg)] text-[var(--accent)]" : "hover:bg-[var(--bg-hover)]"
                  }`}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    insertMention(agent.name);
                  }}
                >
                  <span className="text-lg">{agent.avatar}</span>
                  <div>
                    <div className="font-medium text-[13px]">{agent.name}</div>
                    <div className="text-[11px] text-[var(--text-3)]">
                      {agent.role || agent.model_id}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between px-4 pb-3">
          <div className="flex items-center gap-1">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 px-2.5 py-1 text-[12px] text-[var(--text-2)] hover:text-[var(--accent)] hover:bg-[var(--accent-bg)] rounded-full transition-all"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
              </svg>
              {t("attachment")}
            </button>

            <div className="w-px h-4 bg-[var(--border)] mx-1" />

            <button
              onClick={() => setEnableSearch(!enableSearch)}
              className={
                "flex items-center gap-1.5 px-2.5 py-1 text-[12px] rounded-full transition-all " +
                (enableSearch
                  ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                  : "text-[var(--text-3)] hover:text-[var(--text-2)]")
              }
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
              {t("webSearch")}
            </button>

            <div className="w-px h-4 bg-[var(--border)] mx-1" />

            <div className="flex items-center bg-[var(--bg-hover)] rounded-full p-0.5">
              <button
                onClick={() => setChatMode("simple")}
                className={
                  "px-3 py-1 text-[12px] rounded-full transition-all " +
                  (chatMode === "simple"
                    ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm font-medium"
                    : "text-[var(--text-3)] hover:text-[var(--text-2)]")
                }
              >
                {t("modeSimple")}
              </button>
              <button
                onClick={() => setChatMode("think")}
                className={
                  "px-3 py-1 text-[12px] rounded-full transition-all flex items-center gap-1 " +
                  (chatMode === "think"
                    ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm font-medium"
                    : "text-[var(--text-3)] hover:text-[var(--text-2)]")
                }
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 6v6l4 2" />
                </svg>
                {t("modeThink")}
              </button>
            </div>
          </div>

          <button
            onClick={handleSend}
            disabled={!hasInput}
            className={
              "w-8 h-8 rounded-full flex items-center justify-center transition-all " +
              (hasInput
                ? "bg-[var(--accent)] text-white shadow-[0_2px_8px_rgba(79,70,229,0.3)] hover:opacity-90 hover:scale-105"
                : "bg-[var(--bg-hover)] text-[var(--text-3)] cursor-not-allowed")
            }
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>

      <div className="text-center mt-2">
        <span className="text-[11px] text-[var(--text-3)]">{workers.length > 0 ? `@ ${t("assignWorker")} · ` : ""}{t("disclaimer")}</span>
      </div>
    </div>
  );
}
