/**
 * 主页面组件
 *
 * 应用的根页面，包含三部分布局：
 * - Sidebar：左侧会话列表
 * - ChatPanel：右侧聊天区域（默认）
 * - SettingsPage：设置页面（当 currentSessionId === "__settings__" 时显示）
 *
 * 页面加载时自动拉取会话列表。
 */

"use client";

import { useEffect, useState } from "react";
import { useChatStore } from "@/store/chatStore";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { SettingsPage } from "@/components/settings/SettingsPage";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { OfficeView } from "@/components/office/OfficeView";

export default function Home() {
  const { setSessions } = useChatStore();
  const showSettings = useChatStore((s) => s.currentSessionId === "__settings__");
  const viewMode = useChatStore((s) => s.viewMode);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    api.sessions.list().then((data) => {
      setSessions(data.sessions || []);
    }).catch(() => {});
  }, [setSessions]);

  const mainContent = showSettings
    ? <SettingsPage />
    : viewMode === "office"
      ? <OfficeView />
      : <ChatPanel onMenuClick={() => setSidebarOpen(true)} />;

  return (
    <ErrorBoundary>
      <div className="flex h-screen bg-[var(--bg)]">
        {/* Desktop sidebar */}
        <div className="hidden md:block">
          <Sidebar />
        </div>
        {/* Mobile drawer overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
        {/* Mobile drawer sidebar */}
        <div className={`fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 md:hidden ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}`}>
          <Sidebar onClose={() => setSidebarOpen(false)} />
        </div>
        <main className="flex-1 flex flex-col min-w-0">
          {mainContent}
        </main>
      </div>
    </ErrorBoundary>
  );
}
