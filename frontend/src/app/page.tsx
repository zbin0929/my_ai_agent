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

import { useEffect } from "react";
import { useChatStore } from "@/store/chatStore";
import { api } from "@/lib/api";
import { Sidebar } from "@/components/sidebar/Sidebar";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { SettingsPage } from "@/components/settings/SettingsPage";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function Home() {
  const { setSessions, currentSessionId } = useChatStore();
  const showSettings = useChatStore((s) => s.currentSessionId === "__settings__");

  useEffect(() => {
    api.sessions.list().then((data) => {
      setSessions(data.sessions || []);
    }).catch(() => {});
  }, [setSessions]);

  return (
    <ErrorBoundary>
      <div className="flex h-screen bg-[var(--bg)]">
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0">
          {showSettings ? <SettingsPage /> : <ChatPanel />}
        </main>
      </div>
    </ErrorBoundary>
  );
}
