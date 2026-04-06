"use client";

import { useState, useEffect, useCallback } from "react";
import { FileIcon } from "./FileIcon";
import type { FileInfo } from "@/types";

export function formatFileSize(bytes: number): string {
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

export function FilePreviewModal({ file, onClose }: { file: FileInfo; onClose: () => void }) {
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
