/**
 * 消息项组件
 *
 * 渲染单条聊天消息，区分用户消息和 AI 消息：
 * - 用户消息：右对齐，显示附件文件列表
 * - AI 消息：左对齐，使用 .ai-message 样式渲染 Markdown（含代码高亮）
 * - 支持推理模型的思考过程展示（折叠/展开）
 * - 悬停时显示复制按钮
 *
 * 优化记录：
 * - [React.memo] 使用 memo() 包裹组件，避免父组件状态变化导致不必要的重渲染
 * - [useMemo] Markdown 内容使用 useMemo 缓存，减少 ReactMarkdown 重复解析
 * - [useCallback] handleCopy 使用 useCallback 稳定引用
 */

"use client";

import { useState, useCallback, memo, useMemo, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useI18n } from "@/store/i18nStore";
import { FileIcon } from "./FileIcon";
import { FilePreviewModal, formatFileSize } from "./FilePreviewModal";
import type { Message, FileInfo } from "@/types";

interface MessageItemProps {
  message: Message;
  onRegenerate?: (userMessageContent: string) => void;
  onEditAndResend?: (messageId: string, newContent: string) => void;
  isLast?: boolean;
}

function FileAttachment({ file, onPreview }: { file: FileInfo; onPreview: () => void }) {
  if (file.type === "image") {
    return (
      <div className="mt-2 inline-block cursor-pointer group relative" onClick={onPreview}>
        <img
          src={file.url}
          alt={file.filename}
          className="max-w-[280px] max-h-[200px] rounded-xl border border-[var(--border)] group-hover:opacity-90 transition-opacity object-cover"
        />
        <div className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/10 rounded-xl transition-colors">
          <svg className="w-8 h-8 text-white opacity-0 group-hover:opacity-100 transition-opacity drop-shadow-lg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
            <line x1="11" y1="8" x2="11" y2="14" />
            <line x1="8" y1="11" x2="14" y2="11" />
          </svg>
        </div>
      </div>
    );
  }

  const typeColors: Record<string, string> = {
    video: "from-blue-50 to-blue-100 border-blue-200",
    audio: "from-green-50 to-green-100 border-green-200",
    document: "from-orange-50 to-orange-100 border-orange-200",
    spreadsheet: "from-emerald-50 to-emerald-100 border-emerald-200",
    text: "from-gray-50 to-gray-100 border-gray-200",
  };

  const colorClass = typeColors[file.type] || typeColors.text;

  return (
    <div
      onClick={onPreview}
      className={`mt-2 inline-flex items-center gap-2.5 px-3 py-2 rounded-xl bg-gradient-to-r ${colorClass} border text-sm cursor-pointer hover:shadow-sm transition-all`}
    >
      <div className="text-gray-500">
        <FileIcon type={file.type} className="w-5 h-5" />
      </div>
      <div className="flex flex-col">
        <span className="text-[var(--text)] font-medium text-[13px] max-w-[200px] truncate">{file.filename}</span>
        <span className="text-[var(--text-3)] text-[11px]">{formatFileSize(file.size)}</span>
      </div>
    </div>
  );
}

export const MessageItem = memo(function MessageItem({ message, onRegenerate, onEditAndResend, isLast }: MessageItemProps) {
  const { t } = useI18n();
  const isUser = message.role === "user";
  const [previewFile, setPreviewFile] = useState<FileInfo | null>(null);
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const editRef = useRef<HTMLTextAreaElement>(null);

  // 处理Markdown中的图片点击预览
  const handleImagePreview = (src: string, alt: string) => {
    const filename = src.split("/").pop() || "image.png";
    setPreviewFile({
      file_id: filename,
      filename: alt || filename,
      url: src,
      size: 0,
      type: "image",
    });
  };

  useEffect(() => {
    if (isEditing && editRef.current) {
      editRef.current.focus();
      editRef.current.style.height = "auto";
      editRef.current.style.height = editRef.current.scrollHeight + "px";
    }
  }, [isEditing]);

  const handleEditSubmit = useCallback(() => {
    const trimmed = editContent.trim();
    if (!trimmed || trimmed === message.content) {
      setIsEditing(false);
      setEditContent(message.content);
      return;
    }
    onEditAndResend?.(message.id, trimmed);
    setIsEditing(false);
  }, [editContent, message.content, message.id, onEditAndResend]);

  const handleEditCancel = useCallback(() => {
    setIsEditing(false);
    setEditContent(message.content);
  }, [message.content]);

  const markdownContent = useMemo(() => message.content || "", [message.content]);

  const handleCopy = useCallback(() => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [message.content]);

  return (
    <>
      {previewFile && (
        <FilePreviewModal file={previewFile} onClose={() => setPreviewFile(null)} />
      )}
      <div className={`group flex gap-3 ${isUser ? "flex-row-reverse" : ""} mb-6`}>
        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${isUser ? "bg-[var(--accent)] text-white" : "bg-gradient-to-br from-violet-500 to-purple-600 text-white"}`}>
          {isUser ? "U" : "GC"}
        </div>
        <div className={`min-w-0 ${isUser ? "max-w-[75%]" : "max-w-[80%]"}`}>
          {message.files && message.files.length > 0 && (
            <div className={`flex flex-wrap gap-2 mb-2 ${isUser ? "justify-end" : ""}`}>
              {message.files.map((f) => (
                <FileAttachment key={f.file_id} file={f} onPreview={() => setPreviewFile(f)} />
              ))}
            </div>
          )}
          {message.content && isUser && !isEditing && (
            <div className="inline-block rounded-2xl px-4 py-3 text-[14px] leading-relaxed bg-[var(--accent)] text-white rounded-tr-md">
              <span>{message.content}</span>
            </div>
          )}
          {isUser && isEditing && (
            <div className="w-full max-w-[400px]">
              <textarea
                ref={editRef}
                value={editContent}
                onChange={(e) => {
                  setEditContent(e.target.value);
                  e.target.style.height = "auto";
                  e.target.style.height = e.target.scrollHeight + "px";
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleEditSubmit(); }
                  if (e.key === "Escape") handleEditCancel();
                }}
                className="w-full resize-none rounded-2xl px-4 py-3 text-[14px] leading-relaxed bg-[var(--bg)] border-2 border-[var(--accent)] text-[var(--text)] focus:outline-none"
                style={{ minHeight: "48px" }}
              />
              <div className="flex justify-end gap-2 mt-2">
                <button onClick={handleEditCancel} className="px-3 py-1 rounded-lg text-[12px] text-[var(--text-3)] hover:bg-[var(--bg-hover)] transition-colors">
                  {t("cancel")}
                </button>
                <button onClick={handleEditSubmit} className="px-3 py-1 rounded-lg text-[12px] bg-[var(--accent)] text-white hover:opacity-90 transition-colors">
                  {t("editAndResend")}
                </button>
              </div>
            </div>
          )}
          {message.thinking && !isUser && (
            <div className="thinking-block mb-2">
              <details open>
                <summary>
                  <svg className="think-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 6v6l4 2"/>
                  </svg>
                  <span className="think-label">思考过程</span>
                  <span className="think-badge">已完成</span>
                </summary>
                <div className="thinking-content">
                  {message.thinking}
                </div>
              </details>
            </div>
          )}
          {message.content && !isUser && message.isError && (
            <div className="rounded-2xl px-4 py-3 text-[14px] leading-relaxed bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/40 text-red-700 dark:text-red-300">
              <div className="flex items-start gap-2">
                <svg className="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>{message.content}</span>
              </div>
            </div>
          )}
          {message.content && !isUser && !message.isError && (
            <div className="ai-message">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ src, alt }) => (
                    <img
                      src={typeof src === "string" ? src : undefined}
                      alt={alt || "生成的图片"}
                      className="max-w-full rounded-xl border border-[var(--border)] cursor-pointer hover:opacity-90 transition-opacity"
                      style={{ maxHeight: "400px", objectFit: "contain" }}
                      onClick={() => typeof src === "string" && handleImagePreview(src, alt || "生成的图片")}
                      onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.style.display = "none";
                        const errorDiv = document.createElement("div");
                        errorDiv.className = "text-red-500 text-sm p-2 bg-red-50 dark:bg-red-900/20 rounded-lg";
                        errorDiv.textContent = "图片加载失败";
                        target.parentNode?.insertBefore(errorDiv, target);
                      }}
                    />
                  ),
                }}
              >{markdownContent}</ReactMarkdown>
            </div>
          )}
          {message.agents && message.agents.length > 0 && !isUser && (
            <div className="mt-2 flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px] text-[var(--text-3)]">{t("agentsInvolved")}</span>
              {message.agents.map((agent, idx) => (
                <span
                  key={idx}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${
                    agent.role === "manager"
                      ? "bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-400"
                      : "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                  }`}
                >
                  {agent.name}
                  <span className="text-[10px] opacity-60">{agent.model_id}</span>
                </span>
              ))}
            </div>
          )}
          {message.content && !isEditing && (
            <div className={`mt-1 flex items-center gap-1 ${message.isError ? "opacity-100" : "opacity-0 group-hover:opacity-100"} transition-opacity duration-200 ${isUser ? "justify-end" : "justify-start"}`}>
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-[var(--text-3)] hover:bg-[var(--bg-2)] hover:text-[var(--text-2)] transition-colors"
                title={isUser ? "Copy text" : "Copy Markdown"}
              >
                {copied ? (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <span>{copied ? "Copied" : "Copy"}</span>
                  </>
                ) : (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                    <span>Copy</span>
                  </>
                )}
              </button>
              {isUser && onEditAndResend && (
                <button
                  onClick={() => setIsEditing(true)}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-[var(--text-3)] hover:bg-[var(--bg-2)] hover:text-[var(--text-2)] transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                  <span>{t("editMessage")}</span>
                </button>
              )}
              {!isUser && isLast && onRegenerate && (
                <button
                  onClick={() => onRegenerate(message.content)}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-[var(--text-3)] hover:bg-[var(--bg-2)] hover:text-[var(--text-2)] transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="23 4 23 10 17 10" />
                    <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                  </svg>
                  <span>{t("regenerate")}</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
});
