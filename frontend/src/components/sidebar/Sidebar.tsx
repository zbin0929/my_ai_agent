/**
 * 侧边栏组件
 *
 * 左侧面板，包含：
 * - 新建对话按钮
 * - 按时间分组的会话列表（置顶/今天/昨天/更早）
 * - 每个会话支持：重命名、置顶/取消置顶、删除
 * - 底部设置入口（点击后切换到设置页面）
 * - 中英文双语支持
 */

"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useChatStore } from "@/store/chatStore";
import { useI18n } from "@/store/i18nStore";
import { api } from "@/lib/api";
import { ThemeToggle } from "@/components/ThemeToggle";
import type { Session } from "@/types";

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const {
    sessions,
    currentSessionId,
    setCurrentSession,
    setSessions,
    addSession,
    removeSession,
    setMessages,
    isStreaming,
    resetStreaming,
    setIsStreaming,
  } = useChatStore();

  const { t, lang, setLang } = useI18n();
  const [menuOpen, setMenuOpen] = useState<string | null>(null);
  const [renameModal, setRenameModal] = useState<{ id: string; title: string } | null>(null);
  const [clearModal, setClearModal] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(null);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  const handleNewChat = async () => {
    setCurrentSession(null);
    setMessages([]);
  };

  const handleDelete = async (id: string) => {
    try {
      await api.sessions.delete(id);
      removeSession(id);
      setMenuOpen(null);
    } catch (e) {
      console.error(e);
    }
  };

  const handleRename = async () => {
    if (!renameModal) return;
    const title = renameModal.title.trim();
    if (!title) return;
    try {
      await api.sessions.update(renameModal.id, { title });
      const data = await api.sessions.list();
      setSessions(data.sessions || []);
    } catch (e) {
      console.error(e);
    }
    setRenameModal(null);
    setMenuOpen(null);
  };

  const handlePin = async (id: string, pinned: boolean) => {
    try {
      await api.sessions.update(id, { pinned: !pinned });
      const data = await api.sessions.list();
      setSessions(data.sessions || []);
      setMenuOpen(null);
    } catch (e) {
      console.error(e);
    }
  };

  const handleExport = async (id: string) => {
    try {
      const blob = await api.sessions.exportMarkdown(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `chat_${id}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setMenuOpen(null);
    } catch (e) {
      console.error("Export failed:", e);
    }
  };

  const handleClearAll = async () => {
    try {
      await api.sessions.clearAll();
      setSessions([]);
      setCurrentSession(null);
      setMessages([]);
      setClearModal(false);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSelectSession = async (id: string) => {
    if (isStreaming) {
      resetStreaming();
      setIsStreaming(false);
    }
    setCurrentSession(id);
    setMessages([]);
    onClose?.();  // Close mobile drawer when session selected
    try {
      const data = await api.sessions.getMessages(id);
      setMessages(
        (data.messages || []).map((m: any, i: number) => ({
          id: `${id}-${i}`,
          role: m.role,
          content: m.content || "",
          timestamp: m.timestamp,
          thinking: m.thinking || undefined,
          skill_name: m.skill_name || undefined,
          files: m.files || undefined,
        }))
      );
    } catch (e) {
      setMessages([]);
    }
  };

  const grouped = groupSessions(sessions);

  return (
    <aside className="w-[280px] min-w-[280px] bg-[var(--bg-sidebar)] border-r border-[var(--border)] flex flex-col h-full">
      {/* Mobile close button */}
      {onClose && (
        <div className="md:hidden flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
          <span className="font-medium text-sm">{t("sessions")}</span>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[var(--bg-hover)]">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
      <div className="p-4 pb-2">
        <button
          onClick={handleNewChat}
          className="w-full py-2.5 px-4 rounded-xl border-2 border-dashed border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--accent-bg)] text-[var(--text-2)] hover:text-[var(--accent)] transition-all text-sm font-medium flex items-center justify-center gap-2"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          {t("newChat")}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2">
        {grouped.pinned.length > 0 && (
          <div className="mb-5">
            <div className="px-2 py-1.5 text-[11px] font-semibold text-[var(--text-3)] uppercase tracking-widest">
              {t("pinned")}
            </div>
            {grouped.pinned.map((s) => (
              <SessionItem
                key={s.id}
                session={s}
                active={currentSessionId === s.id}
                menuOpen={menuOpen === s.id}
                menuRef={menuOpen === s.id ? menuRef : null}
                t={t}
                onSelect={() => handleSelectSession(s.id)}
                onMenuToggle={() => setMenuOpen(menuOpen === s.id ? null : s.id)}
                onRename={() => {
                  setRenameModal({ id: s.id, title: s.title || "" });
                  setMenuOpen(null);
                }}
                onDelete={() => handleDelete(s.id)}
                onPin={() => handlePin(s.id, s.pinned)}
                onExport={() => handleExport(s.id)}
              />
            ))}
          </div>
        )}

        {grouped.today.length > 0 && (
          <div className="mb-5">
            <div className="px-2 py-1.5 text-[11px] font-semibold text-[var(--text-3)] uppercase tracking-widest">
              {t("today")}
            </div>
            {grouped.today.map((s) => (
              <SessionItem
                key={s.id}
                session={s}
                active={currentSessionId === s.id}
                menuOpen={menuOpen === s.id}
                menuRef={menuOpen === s.id ? menuRef : null}
                t={t}
                onSelect={() => handleSelectSession(s.id)}
                onMenuToggle={() => setMenuOpen(menuOpen === s.id ? null : s.id)}
                onRename={() => {
                  setRenameModal({ id: s.id, title: s.title || "" });
                  setMenuOpen(null);
                }}
                onDelete={() => handleDelete(s.id)}
                onPin={() => handlePin(s.id, s.pinned)}
                onExport={() => handleExport(s.id)}
              />
            ))}
          </div>
        )}

        {grouped.yesterday.length > 0 && (
          <div className="mb-5">
            <div className="px-2 py-1.5 text-[11px] font-semibold text-[var(--text-3)] uppercase tracking-widest">
              {t("yesterday")}
            </div>
            {grouped.yesterday.map((s) => (
              <SessionItem
                key={s.id}
                session={s}
                active={currentSessionId === s.id}
                menuOpen={menuOpen === s.id}
                menuRef={menuOpen === s.id ? menuRef : null}
                t={t}
                onSelect={() => handleSelectSession(s.id)}
                onMenuToggle={() => setMenuOpen(menuOpen === s.id ? null : s.id)}
                onRename={() => {
                  setRenameModal({ id: s.id, title: s.title || "" });
                  setMenuOpen(null);
                }}
                onDelete={() => handleDelete(s.id)}
                onPin={() => handlePin(s.id, s.pinned)}
                onExport={() => handleExport(s.id)}
              />
            ))}
          </div>
        )}

        {grouped.older.length > 0 && (
          <div className="mb-5">
            <div className="px-2 py-1.5 text-[11px] font-semibold text-[var(--text-3)] uppercase tracking-widest">
              {t("older")}
            </div>
            {grouped.older.map((s) => (
              <SessionItem
                key={s.id}
                session={s}
                active={currentSessionId === s.id}
                menuOpen={menuOpen === s.id}
                menuRef={menuOpen === s.id ? menuRef : null}
                t={t}
                onSelect={() => handleSelectSession(s.id)}
                onMenuToggle={() => setMenuOpen(menuOpen === s.id ? null : s.id)}
                onRename={() => {
                  setRenameModal({ id: s.id, title: s.title || "" });
                  setMenuOpen(null);
                }}
                onDelete={() => handleDelete(s.id)}
                onPin={() => handlePin(s.id, s.pinned)}
                onExport={() => handleExport(s.id)}
              />
            ))}
          </div>
        )}

        {sessions.length === 0 && (
          <div className="px-4 py-12 text-center text-sm text-[var(--text-3)]">
            <div className="text-3xl mb-3">💬</div>
            {t("noSessions")}
          </div>
        )}
      </div>

      {/* 底部：办公室 + 设置 + 清理 + 语言切换 */}
      <div className="p-3 border-t border-[var(--border)] flex flex-col gap-1">
        <ThemeToggle />
        <ViewToggle />
        <div className="flex items-center gap-2">
          <button
            onClick={() => setCurrentSession("__settings__")}
            className="flex-1 py-2.5 px-4 rounded-xl hover:bg-[var(--bg-hover)] text-[var(--text-2)] hover:text-[var(--text)] transition-all text-sm flex items-center gap-2.5"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
            {t("settings")}
          </button>
          {sessions.length > 0 && (
            <button
              onClick={() => setClearModal(true)}
              className="px-3 py-2.5 rounded-xl hover:bg-red-50 text-[var(--text-3)] hover:text-[var(--red)] transition-all text-xs"
              title={t("clearAll")}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          )}
          <button
            onClick={() => setLang(lang === "zh" ? "en" : "zh")}
            className="px-3 py-2.5 rounded-xl hover:bg-[var(--bg-hover)] text-[var(--text-2)] hover:text-[var(--text)] transition-all text-xs font-bold"
            title={lang === "zh" ? "Switch to English" : "切换到中文"}
          >
            {lang === "zh" ? "EN" : "中"}
          </button>
        </div>
      </div>

      {renameModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setRenameModal(null)}>
          <div
            className="bg-[var(--bg)] rounded-2xl shadow-2xl p-6 w-[360px] animate-fade-in-up"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-[var(--text)] mb-4">{t("renameTitle")}</h3>
            <input
              autoFocus
              value={renameModal.title}
              onChange={(e) => setRenameModal({ ...renameModal, title: e.target.value })}
              onKeyDown={(e) => { if (e.key === "Enter") handleRename(); }}
              placeholder={t("renamePlaceholder")}
              className="w-full px-4 py-3 rounded-xl border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-bg)] text-sm transition-all"
            />
            <div className="flex justify-end gap-3 mt-5">
              <button
                onClick={() => setRenameModal(null)}
                className="px-5 py-2 rounded-xl text-sm text-[var(--text-2)] hover:bg-[var(--bg-hover)] transition-all"
              >
                {t("cancel")}
              </button>
              <button
                onClick={handleRename}
                className="px-5 py-2 rounded-xl text-sm bg-[var(--accent)] text-white hover:opacity-90 transition-all shadow-sm"
              >
                {t("confirm")}
              </button>
            </div>
          </div>
        </div>
      )}

      {clearModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setClearModal(false)}>
          <div
            className="bg-[var(--bg)] rounded-2xl shadow-2xl p-6 w-[360px] animate-fade-in-up"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">{t("clearAllTitle")}</h3>
            <p className="text-sm text-[var(--text-2)] mb-5">{t("clearAllDesc")}</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setClearModal(false)}
                className="px-5 py-2 rounded-xl text-sm text-[var(--text-2)] hover:bg-[var(--bg-hover)] transition-all"
              >
                {t("cancel")}
              </button>
              <button
                onClick={handleClearAll}
                className="px-5 py-2 rounded-xl text-sm bg-[var(--red)] text-white hover:opacity-90 transition-all shadow-sm"
              >
                {t("confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}

function SessionItem({
  session,
  active,
  menuOpen,
  menuRef,
  t,
  onSelect,
  onMenuToggle,
  onRename,
  onDelete,
  onPin,
  onExport,
}: {
  session: Session;
  active: boolean;
  menuOpen: boolean;
  menuRef: React.RefObject<HTMLDivElement | null> | null;
  t: (key: string) => string;
  onSelect: () => void;
  onMenuToggle: () => void;
  onRename: () => void;
  onDelete: () => void;
  onPin: () => void;
  onExport: () => void;
}) {
  return (
    <div
      className={"group relative flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all mb-1 " +
        (active
          ? "bg-[var(--accent-bg)] text-[var(--accent)] font-medium"
          : "hover:bg-[var(--bg-hover)] text-[var(--text)]")
      }
      onClick={onSelect}
    >
      <span className="flex-1 text-sm truncate">{session.pinned && "📌 "}{session.title || t("newChat")}</span>
      <button
        onClick={(e) => { e.stopPropagation(); onMenuToggle(); }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-[var(--bg-hover)] transition-all"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="5" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="12" cy="19" r="2" />
        </svg>
      </button>

      {menuOpen && (
        <div
          ref={menuRef}
          className="absolute right-0 top-full z-50 bg-[var(--bg)] border border-[var(--border)] rounded-xl shadow-lg py-1 min-w-[140px]"
          onClick={(e) => e.stopPropagation()}
        >
          <button onClick={onPin} className="w-full px-3 py-2.5 text-left text-sm hover:bg-[var(--bg-hover)] transition-colors">
            {session.pinned ? t("unpin") : t("pin")}
          </button>
          <button onClick={onRename} className="w-full px-3 py-2.5 text-left text-sm hover:bg-[var(--bg-hover)] transition-colors">
            {t("rename")}
          </button>
          <button className="w-full px-3 py-2.5 text-left text-sm hover:bg-[var(--bg-hover)] text-[var(--text-2)] transition-colors">
            {t("share")}
          </button>
          <button onClick={onExport} className="w-full px-3 py-2.5 text-left text-sm hover:bg-[var(--bg-hover)] transition-colors">
            {t("export")}
          </button>
          <div className="border-t border-[var(--border)] my-1" />
          <button onClick={onDelete} className="w-full px-3 py-2.5 text-left text-sm hover:bg-red-50 text-[var(--red)] transition-colors">
            {t("delete")}
          </button>
        </div>
      )}
    </div>
  );
}

function ViewToggle() {
  const viewMode = useChatStore((s) => s.viewMode);
  const setViewMode = useChatStore((s) => s.setViewMode);

  return (
    <div className="flex rounded-xl bg-[var(--bg-hover)] p-0.5">
      <button
        onClick={() => setViewMode("chat")}
        className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
          viewMode === "chat"
            ? "bg-[var(--bg)] text-[var(--text)] shadow-sm"
            : "text-[var(--text-3)] hover:text-[var(--text-2)]"
        }`}
      >
        💬 聊天
      </button>
      <button
        onClick={() => setViewMode("office")}
        className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1.5 ${
          viewMode === "office"
            ? "bg-[var(--bg)] text-[var(--text)] shadow-sm"
            : "text-[var(--text-3)] hover:text-[var(--text-2)]"
        }`}
      >
        🏢 办公室
      </button>
    </div>
  );
}

function groupSessions(sessions: Session[]) {
  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = `${yesterday.getFullYear()}-${String(yesterday.getMonth() + 1).padStart(2, "0")}-${String(yesterday.getDate()).padStart(2, "0")}`;

  const pinned = sessions.filter((s) => s.pinned);
  const todaySessions = sessions.filter((s) => !s.pinned && s.created_at?.slice(0, 10) === today);
  const yesterdaySessions = sessions.filter((s) => !s.pinned && s.created_at?.slice(0, 10) === yesterdayStr);
  const older = sessions.filter((s) => !s.pinned && s.created_at?.slice(0, 10) !== today && s.created_at?.slice(0, 10) !== yesterdayStr);
  return { pinned, today: todaySessions, yesterday: yesterdaySessions, older };
}
