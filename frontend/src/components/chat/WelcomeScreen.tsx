/**
 * 欢迎页组件
 *
 * 无会话选中时显示的欢迎页面，包含：
 * - 欢迎语和副标题
 * - 4 个快捷建议按钮（点击后直接发送对应消息）
 * - 联网搜索 + 简单/思考模式切换
 * - 创建新会话并触发 AI 回复的逻辑
 */

"use client";

import { useState, useRef, useCallback } from "react";
import { useChatStore } from "@/store/chatStore";
import { useI18n } from "@/store/i18nStore";
import { api } from "@/lib/api";
import { ChatInputToolbar } from "./ChatInputToolbar";
import { FileIcon } from "./FileIcon";
import type { FileInfo } from "@/types";

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

const SUGGESTIONS = [
  { icon: "💡", key: "s1" },
  { icon: "📊", key: "s2" },
  { icon: "🎨", key: "s3" },
  { icon: "🔍", key: "s4" },
];

export function WelcomeScreen({ onMenuClick }: { onMenuClick?: () => void }) {
  const { addSession, setCurrentSession, setMessages, setPendingMessage } = useChatStore();
  const { t } = useI18n();
  const [input, setInput] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const startChat = async (text: string) => {
    if (!text.trim() && files.length === 0) return;
    try {
      const session = await api.sessions.create();
      addSession(session);
      setCurrentSession(session.id);
      setMessages([]);
      setPendingMessage(text.trim() || "请分析这个文件", files.length > 0 ? files : null);
      setInput("");
      setFiles([]);
    } catch (e) { console.error(e); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); startChat(input); }
  };

  const handleFileUpload = useCallback(async (fileList: FileList | null) => {
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
  }, [t]);

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

  const hasInput = input.trim().length > 0 || files.length > 0;

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4">
      {/* Mobile menu button */}
      <div className="md:hidden absolute top-4 left-4">
        <button onClick={onMenuClick} className="p-2 rounded-lg hover:bg-[var(--bg-hover)]">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      </div>
      <div className="w-full max-w-[720px]" onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
        <div className="mb-8">
          <h1 className="text-[32px] font-semibold text-[var(--text)] mb-2">{t("welcome")}</h1>
          <p className="text-[var(--text-2)] text-lg">{t("subtitle")}</p>
        </div>
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
        <div className={"bg-[var(--bg)] rounded-[24px] border transition-all duration-200 " + (isFocused ? "border-[var(--accent)] shadow-[0_0_0_3px_rgba(79,70,229,0.1),0_4px_20px_rgba(0,0,0,0.08)]" : "border-[var(--border)] shadow-[0_2px_8px_rgba(0,0,0,0.04)]")}>
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
          <div className="px-5 pt-4">
            <textarea value={input} onChange={(e) => { setInput(e.target.value); e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 300) + "px"; }} onKeyDown={handleKeyDown} onFocus={() => setIsFocused(true)} onBlur={() => setIsFocused(false)} placeholder={t("placeholder")} rows={3} className="w-full resize-none text-[15px] text-[var(--text)] focus:outline-none min-h-[72px] max-h-[300px] bg-transparent placeholder:text-[var(--text-3)]" style={{ lineHeight: "1.6" }} />
          </div>
          <ChatInputToolbar
            hasInput={hasInput}
            onAttachClick={() => fileInputRef.current?.click()}
            onSend={() => startChat(input)}
            onVoiceResult={(text) => setInput(input ? input + " " + text : text)}
          />
        </div>
        <div className="flex flex-wrap gap-2 mt-6 justify-center">
          {SUGGESTIONS.map((s, i) => (
            <button key={i} onClick={() => startChat(t(s.key))} className="px-4 py-2 bg-[var(--bg)] border border-[var(--border)] rounded-full text-[14px] text-[var(--text-2)] hover:border-[var(--accent)] hover:text-[var(--accent)] hover:shadow-sm transition-all">
              {s.icon} {t(s.key)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
