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
import { ChatInputToolbar } from "./ChatInputToolbar";

const SUGGESTIONS = [
  { icon: "💡", key: "s1" },
  { icon: "📊", key: "s2" },
  { icon: "🎨", key: "s3" },
  { icon: "🔍", key: "s4" },
];

export function WelcomeScreen({ onMenuClick }: { onMenuClick?: () => void }) {
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
      {/* Mobile menu button */}
      <div className="md:hidden absolute top-4 left-4">
        <button onClick={onMenuClick} className="p-2 rounded-lg hover:bg-[var(--bg-hover)]">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
      </div>
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
          <ChatInputToolbar
            hasInput={hasInput}
            onAttachClick={() => fileInputRef.current?.click()}
            onSend={() => startChat(input)}
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
