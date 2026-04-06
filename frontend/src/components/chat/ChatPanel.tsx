/**
 * 聊天面板组件
 *
 * 聊天区域的主容器，包含：
 * - WelcomeScreen：无会话时显示的欢迎页
 * - PipelineInfoBar：技能触发和模型信息条
 * - MessageList：消息列表（含自动滚动）
 * - StreamingMessage：流式输出中的消息
 * - InputBar：底部输入栏（含文件上传、模式切换、发送按钮）
 */

"use client";

import { useChatStore } from "@/store/chatStore";
import { WelcomeScreen } from "./WelcomeScreen";
import { MessageList } from "./MessageList";
import { InputBar } from "./InputBar";

export function ChatPanel({ onMenuClick }: { onMenuClick?: () => void }) {
  const { currentSessionId, isStreaming, currentSkill, pipelineInfo } = useChatStore();

  if (!currentSessionId) {
    return (
      <div className="flex-1 flex flex-col h-full">
        <WelcomeScreen onMenuClick={onMenuClick} />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[var(--bg)]">
      {/* Mobile header with menu button */}
      <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-[var(--border)]">
        <button onClick={onMenuClick} className="p-2 rounded-lg hover:bg-[var(--bg-hover)]">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 12h18M3 6h18M3 18h18" />
          </svg>
        </button>
        <span className="text-sm font-medium truncate">{currentSessionId}</span>
      </div>
      <MessageList />

      {(isStreaming && (currentSkill || pipelineInfo)) && (
        <div className="px-6 pb-2 flex items-center gap-3 flex-wrap max-w-[768px] mx-auto w-full">
          {currentSkill && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-violet-50 text-violet-600 text-[11px] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
              {currentSkill}
            </span>
          )}
          {pipelineInfo && (
            <>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-600 text-[11px] font-medium">
                {pipelineInfo.agentName}
              </span>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-emerald-600 text-[11px] font-medium">
                {pipelineInfo.modelId}
              </span>
              {pipelineInfo.skillName && pipelineInfo.skillName !== currentSkill && (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-50 text-amber-600 text-[11px] font-medium">
                  {pipelineInfo.skillName}
                </span>
              )}
            </>
          )}
        </div>
      )}

      <InputBar />
    </div>
  );
}
