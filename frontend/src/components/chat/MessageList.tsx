/**
 * 消息列表组件
 *
 * 渲染当前会话的所有消息，包含：
 * - 历史消息（MessageItem 组件）
 * - 流式输出中的消息（StreamingMessage 组件）
 * - 自动滚动到底部（新消息时、流式输出时）
 */

"use client";

import { useEffect, useRef, useCallback } from "react";
import { useChatStore } from "@/store/chatStore";
import { useI18n } from "@/store/i18nStore";
import { api, streamChat } from "@/lib/api";
import { createSSEHandlers } from "@/hooks/useSSEHandlers";
import { MessageItem } from "./MessageItem";
import { StreamingMessage } from "./StreamingMessage";

let _regenIdCounter = 0;
function _regenId() {
  _regenIdCounter += 1;
  return `${Date.now()}-regen-${_regenIdCounter}-${Math.random().toString(36).slice(2, 8)}`;
}

export function MessageList() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { messages, isStreaming, streamingContent, streamingThinking, currentSkill, currentSessionId } = useChatStore();
  const { t } = useI18n();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [currentSessionId, messages, isStreaming]);

  const triggerResend = useCallback((text: string) => {
    const state = useChatStore.getState();
    const sessionId = state.currentSessionId;
    if (!sessionId || !text.trim()) return;

    state.setIsStreaming(true);
    state.setStreamingSessionId(sessionId);
    state.resetStreaming();

    const { onEvent, onError, onDone } = createSSEHandlers({
      sessionId,
      shouldAutoTitle: false,
      userText: text,
      errorFallback: t("errorDefault"),
    });

    streamChat(
      text, sessionId, "default",
      onEvent, onError, onDone,
      undefined, undefined,
      state.chatMode, undefined, state.enableSearch,
    );
  }, [t]);

  const handleRegenerate = useCallback(() => {
    const state = useChatStore.getState();
    const msgs = state.messages;
    if (msgs.length < 2) return;

    const lastAssistantIdx = msgs.length - 1;
    const lastUserMsg = [...msgs].reverse().find((m) => m.role === "user");
    if (!lastUserMsg) return;

    const newMessages = msgs.slice(0, lastAssistantIdx);
    state.setMessages(newMessages);

    triggerResend(lastUserMsg.content);
  }, [triggerResend]);

  const handleEditAndResend = useCallback((messageId: string, newContent: string) => {
    const state = useChatStore.getState();
    const msgs = state.messages;
    const idx = msgs.findIndex((m) => m.id === messageId);
    if (idx === -1) return;

    const updatedMsg = { ...msgs[idx], content: newContent };
    const newMessages = [...msgs.slice(0, idx), updatedMsg];
    state.setMessages(newMessages);

    triggerResend(newContent);
  }, [triggerResend]);

  const lastAssistantIdx = messages.length > 0 && messages[messages.length - 1].role === "assistant"
    ? messages.length - 1
    : -1;

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-[768px] mx-auto">
        {messages.map((msg, idx) => (
          <MessageItem
            key={msg.id}
            message={msg}
            isLast={idx === lastAssistantIdx}
            onRegenerate={!isStreaming ? handleRegenerate : undefined}
            onEditAndResend={!isStreaming ? handleEditAndResend : undefined}
          />
        ))}
        {isStreaming && (
          <StreamingMessage
            content={streamingContent}
            thinking={streamingThinking}
            skill={currentSkill}
          />
        )}
      </div>
    </div>
  );
}
