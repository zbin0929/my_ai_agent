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

import { useState, useRef } from "react";
import { useChatStore } from "@/store/chatStore";
import { useI18n } from "@/store/i18nStore";
import { api } from "@/lib/api";

const SUGGESTIONS = [
  { icon: "💡", key: "s1" },
  { icon: "📊", key: "s2" },
  { icon: "🎨", key: "s3" },
  { icon: "🔍", key: "s4" },
];

export function WelcomeScreen() {
  const { addSession, setCurrentSession, setMessages, setPendingMessage, chatMode, setChatMode, enableSearch, setEnableSearch } = useChatStore();
  const { t } = useI18n();
  const [input, setInput] = useState("");
  const [isFocused, setIsFocused] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const startChat = async (text: string) => {
    if (!text.trim()) return;
    try {
      const session = await api.sessions.create();
      addSession(session);
      setCurrentSession(session.id);
      setMessages([]);
      setPendingMessage(text.trim());
      setInput("");
    } catch (e) { console.error(e); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); startChat(input); }
  };

  const hasInput = input.trim().length > 0;

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-[720px]">
        <div className="mb-8">
          <h1 className="text-[32px] font-semibold text-[var(--text)] mb-2">{t("welcome")}</h1>
          <p className="text-[var(--text-2)] text-lg">{t("subtitle")}</p>
        </div>
        <input ref={fileInputRef} type="file" className="hidden" multiple onChange={() => {}} />
        <div className={"bg-[var(--bg)] rounded-[24px] border transition-all duration-200 " + (isFocused ? "border-[var(--accent)] shadow-[0_0_0_3px_rgba(79,70,229,0.1),0_4px_20px_rgba(0,0,0,0.08)]" : "border-[var(--border)] shadow-[0_2px_8px_rgba(0,0,0,0.04)]")}>
          <div className="px-5 pt-4">
            <textarea value={input} onChange={(e) => { setInput(e.target.value); e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 300) + "px"; }} onKeyDown={handleKeyDown} onFocus={() => setIsFocused(true)} onBlur={() => setIsFocused(false)} placeholder={t("placeholder")} rows={3} className="w-full resize-none text-[15px] text-[var(--text)] focus:outline-none min-h-[72px] max-h-[300px] bg-transparent placeholder:text-[var(--text-3)]" style={{ lineHeight: "1.6" }} />
          </div>
          <div className="flex items-center justify-between px-3 py-3">
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

            <button onClick={() => startChat(input)} disabled={!hasInput} className={"w-9 h-9 rounded-full flex items-center justify-center transition-all " + (hasInput ? "bg-[var(--accent)] text-white shadow-[0_2px_8px_rgba(79,70,229,0.3)] hover:opacity-90 hover:scale-105" : "bg-[var(--bg-hover)] text-[var(--text-3)] cursor-not-allowed")}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
            </button>
          </div>
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
