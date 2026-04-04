/**
 * 消息列表组件
 *
 * 渲染当前会话的所有消息，包含：
 * - 历史消息（MessageItem 组件）
 * - 流式输出中的消息（StreamingMessage 组件）
 * - 自动滚动到底部（新消息时、流式输出时）
 */

"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/store/chatStore";
import { MessageItem } from "./MessageItem";
import { StreamingMessage } from "./StreamingMessage";

export function MessageList() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { messages, isStreaming, streamingContent, streamingThinking, currentSkill, currentSessionId } = useChatStore();

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [currentSessionId, messages, isStreaming]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6">
      <div className="max-w-[768px] mx-auto">
        {messages.map((msg) => (
          <MessageItem key={msg.id} message={msg} />
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
