"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { useChatStore } from "@/store/chatStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useI18n } from "@/store/i18nStore";
import { api, streamChat } from "@/lib/api";
import { createSSEHandlers } from "@/hooks/useSSEHandlers";
import { FileIcon } from "./FileIcon";
import { ChatInputToolbar } from "./ChatInputToolbar";
import type { FileInfo } from "@/types";

let messageIdCounter = 0;
function generateUniqueId() {
  messageIdCounter += 1;
  return `${Date.now()}-${messageIdCounter}-${Math.random().toString(36).slice(2, 8)}`;
}

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20MB
const ALLOWED_EXTENSIONS = new Set([
  "png","jpg","jpeg","gif","webp","bmp","svg",
  "pdf","doc","docx","ppt","pptx","txt","md","csv","tsv",
  "xls","xlsx","json","xml","html","py","js","ts","java","c","cpp",
  "mp3","wav","mp4","webm","ogg",
]);

function validateFile(file: File, t: (key: string) => string): string | null {
  if (file.size > MAX_FILE_SIZE) {
    return t("fileTooLarge").replace("{size}", "20MB");
  }
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  if (ext && !ALLOWED_EXTENSIONS.has(ext)) {
    return t("fileTypeNotAllowed");
  }
  return null;
}

export function InputBar() {
  const [input, setInput] = useState("");
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [isFocused, setIsFocused] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
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
    isStreaming,
    setIsStreaming,
    setStreamingSessionId,
    resetStreaming,
    updateSessionTitle,
    chatMode,
    setChatMode,
    enableSearch,
    setEnableSearch,
    pendingMessage,
    setPendingMessage,
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
      const { onEvent, onError, onDone } = createSSEHandlers({
        sessionId: currentSessionId,
        shouldAutoTitle,
        userText: text,
        errorFallback: t("errorDefault"),
      });
      await streamChat(
        text,
        currentSessionId,
        "default",
        onEvent,
        onError,
        onDone,
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
  }, [input, files, currentSessionId, messages.length, addMessage, setIsStreaming, setStreamingSessionId, resetStreaming, updateSessionTitle, chatMode, enableSearch, t]);

  useEffect(() => {
    if (!pendingMessage || !currentSessionId) return;
    if (pendingMessageSentRef.current) {
      setPendingMessage(null);
      return;
    }
    pendingMessageSentRef.current = true;
    const text = pendingMessage;
    const state = useChatStore.getState();
    const pendingFileInfos = state.pendingFiles;
    const pendingFileIds = pendingFileInfos?.map((f) => f.file_id);
    setPendingMessage(null);

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
      files: pendingFileInfos || undefined,
    });

    state.setIsStreaming(true);
    state.setStreamingSessionId(currentSessionId);
    state.resetStreaming();
    const ac = new AbortController();

    const { onEvent, onError, onDone: onDoneBase } = createSSEHandlers({
      sessionId: currentSessionId,
      shouldAutoTitle,
      userText: text,
      errorFallback: t("errorDefault"),
    });
    streamChat(
      text,
      currentSessionId,
      "default",
      onEvent,
      onError,
      () => {
        onDoneBase();
        pendingMessageSentRef.current = false;
      },
      pendingFileIds,
      pendingFileInfos || undefined,
      state.chatMode,
      ac.signal,
      state.enableSearch
    );
  }, [pendingMessage, currentSessionId, t]);

  const handleFileUpload = async (fileList: FileList | null) => {
    if (!fileList) return;
    setUploadError(null);
    for (let i = 0; i < fileList.length; i++) {
      const validationError = validateFile(fileList[i], t);
      if (validationError) {
        setUploadError(validationError);
        setTimeout(() => setUploadError(null), 5000);
        continue;
      }
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

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) {
      handleFileUpload(e.dataTransfer.files);
    }
  }, [handleFileUpload]);

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

  const handleStop = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
    resetStreaming();
  }, [setIsStreaming, resetStreaming]);

  const hasInput = input.trim().length > 0;

  return (
    <div
      className="w-full max-w-[720px] mx-auto px-4 pb-6 relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="absolute inset-0 z-50 flex items-center justify-center rounded-[24px] border-2 border-dashed border-[var(--accent)] bg-[var(--accent-bg)] backdrop-blur-sm">
          <div className="flex flex-col items-center gap-2 text-[var(--accent)]">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <span className="text-sm font-medium">{t("dragDropHint")}</span>
          </div>
        </div>
      )}
      <input ref={fileInputRef} type="file" className="hidden" multiple onChange={(e) => handleFileUpload(e.target.files)} />
      {uploadError && (
        <div className="mb-2 px-4 py-2 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 text-red-600 dark:text-red-400 text-[13px] flex items-center gap-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {uploadError}
        </div>
      )}
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

        <ChatInputToolbar
          hasInput={hasInput}
          isStreaming={isStreaming}
          onAttachClick={() => fileInputRef.current?.click()}
          onSend={handleSend}
          onStop={handleStop}
          onVoiceResult={(text) => handleInputChange(input ? input + " " + text : text)}
        />
      </div>

      <div className="text-center mt-2">
        <span className="text-[11px] text-[var(--text-3)]">{workers.length > 0 ? `@ ${t("assignWorker")} · ` : ""}{t("disclaimer")}</span>
      </div>
    </div>
  );
}
