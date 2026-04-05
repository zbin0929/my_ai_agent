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

import { useState, useEffect, useCallback, memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useI18n } from "@/store/i18nStore";
import type { Message, FileInfo } from "@/types";

interface MessageItemProps {
  message: Message;
}

function FileIcon({ type, className = "w-5 h-5" }: { type: string; className?: string }) {
  const cls = className;
  switch (type) {
    case "image":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <path d="M21 15l-5-5L5 21" />
        </svg>
      );
    case "video":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <polygon points="10,8 16,12 10,16" fill="currentColor" opacity="0.3" />
          <polygon points="10,8 16,12 10,16" />
        </svg>
      );
    case "audio":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 18V5l12-2v13" />
          <circle cx="6" cy="18" r="3" />
          <circle cx="18" cy="16" r="3" />
        </svg>
      );
    case "document":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14,2 14,8 20,8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10,9 9,9 8,9" />
        </svg>
      );
    case "spreadsheet":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <line x1="3" y1="9" x2="21" y2="9" />
          <line x1="3" y1="15" x2="21" y2="15" />
          <line x1="9" y1="3" x2="9" y2="21" />
          <line x1="15" y1="3" x2="15" y2="21" />
        </svg>
      );
    default:
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14,2 14,8 20,8" />
        </svg>
      );
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function getLanguageHint(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() || "";
  const map: Record<string, string> = {
    py: "python", js: "javascript", ts: "typescript", json: "json",
    html: "html", css: "css", xml: "xml", yaml: "yaml", yml: "yaml",
    md: "markdown", sh: "bash", bash: "bash", zsh: "bash",
    go: "go", rs: "rust", java: "java", c: "c", cpp: "cpp",
    h: "c", hpp: "cpp", rb: "ruby", php: "php", sql: "sql",
    r: "r", m: "objectivec", swift: "swift", kt: "kotlin",
    dart: "dart", toml: "toml", ini: "ini", cfg: "ini",
    conf: "conf", log: "log", env: "env",
  };
  return map[ext] || "text";
}

function FilePreviewModal({ file, onClose }: { file: FileInfo; onClose: () => void }) {
  const [content, setContent] = useState<string | null>(null);
  const [contentType, setContentType] = useState<string>("text");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  }, [onClose]);

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [handleKeyDown]);

  useEffect(() => {
    if (file.type === "image" || file.type === "video" || file.type === "audio") {
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetch(`/api/files/content/${file.file_id}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load file");
        return res.json();
      })
      .then((data) => {
        if (data.type === "binary" || data.content === null) {
          setError("preview_not_supported");
        } else {
          setContent(data.content);
          setContentType(data.type);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError("Failed to load file content");
        setLoading(false);
      });
    return () => controller.abort();
  }, [file]);

  const isDownloadOnly = file.type === "document";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div
        className="bg-[var(--bg)] rounded-2xl shadow-2xl max-w-[85vw] max-h-[85vh] w-[900px] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--border)] shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="text-violet-500">
              <FileIcon type={file.type} className="w-5 h-5" />
            </div>
            <span className="font-medium text-[14px] text-[var(--text)]">{file.filename}</span>
            <span className="text-[12px] text-[var(--text-3)]">{formatFileSize(file.size)}</span>
          </div>
          <div className="flex items-center gap-1">
            <a
              href={file.url}
              download={file.filename}
              className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-[var(--bg-hover)] text-[var(--text-3)] hover:text-[var(--text-2)]"
              title="Download"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7,10 12,15 17,10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
            </a>
            <button
              onClick={onClose}
              className="w-7 h-7 rounded-full flex items-center justify-center hover:bg-[var(--bg-hover)] text-[var(--text-3)] hover:text-[var(--text-2)]"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto p-5 min-h-0">
          {loading && (
            <div className="flex items-center justify-center py-16 text-[var(--text-3)]">
              <div className="w-6 h-6 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin mr-3" />
              Loading...
            </div>
          )}

          {!loading && file.type === "image" && (
            <div className="flex items-center justify-center">
              <img src={file.url} alt={file.filename} className="max-w-full max-h-[70vh] rounded-lg object-contain" />
            </div>
          )}

          {!loading && file.type === "video" && (
            <div className="flex items-center justify-center">
              <video src={file.url} controls className="max-w-full max-h-[70vh] rounded-lg" />
            </div>
          )}

          {!loading && file.type === "audio" && (
            <div className="flex items-center justify-center py-12">
              <div className="w-full max-w-lg flex flex-col items-center gap-4">
                <div className="w-20 h-20 rounded-full bg-gradient-to-br from-violet-100 to-purple-100 flex items-center justify-center">
                  <FileIcon type="audio" className="w-10 h-10 text-violet-500" />
                </div>
                <span className="text-sm text-gray-500">{file.filename}</span>
                <audio src={file.url} controls className="w-full" />
              </div>
            </div>
          )}

          {!loading && isDownloadOnly && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-violet-100 to-purple-100 flex items-center justify-center">
                <FileIcon type="document" className="w-10 h-10 text-violet-500" />
              </div>
              <div className="text-center">
                <p className="text-gray-700 font-medium mb-1">{file.filename}</p>
                <p className="text-gray-400 text-sm mb-4">{formatFileSize(file.size)}</p>
                <a
                  href={file.url}
                  download={file.filename}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-500 text-white rounded-xl text-sm font-medium hover:bg-violet-600 transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7,10 12,15 17,10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Download
                </a>
              </div>
            </div>
          )}

          {!loading && error === "preview_not_supported" && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
                <FileIcon type={file.type} className="w-10 h-10 text-gray-400" />
              </div>
              <div className="text-center">
                <p className="text-gray-700 font-medium mb-1">{file.filename}</p>
                <p className="text-gray-400 text-sm mb-4">This file type does not support inline preview</p>
                <a
                  href={file.url}
                  download={file.filename}
                  className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-500 text-white rounded-xl text-sm font-medium hover:bg-violet-600 transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="7,10 12,15 17,10" />
                    <line x1="12" y1="15" x2="12" y2="3" />
                  </svg>
                  Download
                </a>
              </div>
            </div>
          )}

          {!loading && contentType === "csv" && content && (
            <div className="overflow-auto max-h-[65vh]">
              <table className="w-full text-sm border-collapse">
                <tbody>
                  {content.split("\n").filter(Boolean).map((row, i) => (
                    <tr key={i} className={i === 0 ? "bg-violet-50 font-medium" : "hover:bg-gray-50"}>
                      {row.split(/[\t,]/).map((cell, j) => (
                        <td key={j} className={`px-4 py-2.5 border border-gray-100 whitespace-nowrap ${i === 0 ? "text-violet-700" : "text-gray-700"}`}>
                          {cell.trim()}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!loading && contentType === "text" && content && (
            <div className="relative">
              <div className="absolute top-2 right-2 text-[11px] text-gray-300 font-mono bg-gray-50 px-2 py-0.5 rounded">
                {getLanguageHint(file.filename)}
              </div>
              <pre className="text-[13px] leading-relaxed text-gray-800 whitespace-pre-wrap font-mono bg-gray-50 rounded-xl p-4 overflow-auto max-h-[65vh] border border-gray-100">
                <code>{content}</code>
              </pre>
            </div>
          )}

          {!loading && error && error !== "preview_not_supported" && (
            <div className="flex items-center justify-center py-16 text-red-400">
              <p>Failed to load file content</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
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

export const MessageItem = memo(function MessageItem({ message }: MessageItemProps) {
  const { t } = useI18n();
  const isUser = message.role === "user";
  const [previewFile, setPreviewFile] = useState<FileInfo | null>(null);
  const [copied, setCopied] = useState(false);

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
          {message.content && isUser && (
            <div className="inline-block rounded-2xl px-4 py-3 text-[14px] leading-relaxed bg-[var(--accent)] text-white rounded-tr-md">
              <span>{message.content}</span>
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
          {message.content && !isUser && (
            <div className="ai-message">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdownContent}</ReactMarkdown>
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
          {message.content && (
            <div className={`mt-1 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 ${isUser ? "justify-end" : "justify-start"}`}>
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
            </div>
          )}
        </div>
      </div>
    </>
  );
});
