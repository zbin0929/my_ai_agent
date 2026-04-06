/**
 * 共享输入工具栏组件
 *
 * 从 InputBar 和 WelcomeScreen 中提取的公共底部工具栏，包含：
 * - 附件按钮
 * - 联网搜索开关
 * - 简单/思考模式切换
 * - 发送/停止按钮
 */

"use client";

import { useChatStore } from "@/store/chatStore";
import { useI18n } from "@/store/i18nStore";

interface ChatInputToolbarProps {
  hasInput: boolean;
  isStreaming?: boolean;
  onAttachClick: () => void;
  onSend: () => void;
  onStop?: () => void;
}

export function ChatInputToolbar({
  hasInput,
  isStreaming = false,
  onAttachClick,
  onSend,
  onStop,
}: ChatInputToolbarProps) {
  const { chatMode, setChatMode, enableSearch, setEnableSearch } = useChatStore();
  const { t } = useI18n();

  return (
    <div className="flex items-center justify-between px-4 pb-3">
      <div className="flex items-center gap-1">
        <button
          onClick={onAttachClick}
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

      {isStreaming && onStop ? (
        <button
          onClick={onStop}
          className="w-8 h-8 rounded-full flex items-center justify-center transition-all bg-red-500 text-white shadow-[0_2px_8px_rgba(239,68,68,0.3)] hover:bg-red-600 hover:scale-105"
          title={t("stopGenerate")}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
            <rect x="4" y="4" width="16" height="16" rx="2" />
          </svg>
        </button>
      ) : (
        <button
          onClick={onSend}
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
      )}
    </div>
  );
}
