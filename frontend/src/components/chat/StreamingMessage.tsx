/**
 * 流式消息组件
 *
 * 在 AI 回复流式输出过程中实时渲染：
 * - 技能名称提示（如"正在使用技能：文件分析"）
 * - 推理模型的思考过程（可折叠）
 * - 逐步增长的回复内容（Markdown 渲染）
 */

"use client";

import { useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useI18n } from "@/store/i18nStore";

export function StreamingMessage({ content, thinking, skill }: { content: string; thinking: string; skill: string | null }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [content]);

  return (
    <div className="flex gap-3 mb-6">
      <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 bg-gradient-to-br from-violet-500 to-purple-600 text-white">
        GC
      </div>

      <div className="min-w-0 max-w-[80%]">
        {skill && (
          <div className="mb-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-violet-50 text-violet-600 text-[11px] font-medium">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
            <span>{skill}</span>
          </div>
        )}

        {thinking && (
          <div className="thinking-block">
            <details open>
              <summary>
                <svg className="think-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
                <span className="think-label">{t("thinkingProcess")}</span>
                <span className="think-badge">推理中</span>
              </summary>
              <div className="thinking-content">
                {thinking}
              </div>
            </details>
          </div>
        )}

        {content && (
          <>
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
                      onClick={() => typeof src === "string" && window.open(src, "_blank")}
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
              >{content}</ReactMarkdown>
            </div>
            <div className="mt-1 flex items-center gap-1">
              <button
                onClick={handleCopy}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-[var(--text-3)] hover:bg-[var(--bg-2)] hover:text-[var(--text-2)] transition-colors"
                title="Copy Markdown"
              >
                {copied ? (
                  <>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <span>Copied</span>
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
          </>
        )}

        {!content && !thinking && !skill && (
          <div className="flex items-center gap-2 text-[var(--text-3)] py-3 px-4">
            <span className="inline-block w-2 h-2 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="inline-block w-2 h-2 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="inline-block w-2 h-2 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        )}
      </div>
    </div>
  );
}
