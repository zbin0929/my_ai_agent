/**
 * 聊天状态管理 Store (Zustand)
 *
 * 使用 slice 模式按职责拆分为三个逻辑切片：
 * - SessionSlice：会话列表和当前会话管理
 * - MessageSlice：消息列表管理
 * - StreamSlice：SSE 流式输出状态、技能触发、聊天模式
 *
 * 优化记录：
 * - [Slice 模式] 从单一扁平 store 重构为三个独立 slice，提升可维护性
 * - [类型安全] 每个 slice 有独立的 TypeScript 接口，StateCreator 泛型保证类型正确
 */

import { create, type StateCreator } from "zustand";
import type { Message, Session } from "@/types";

// ==================== Session Slice ====================

interface SessionSlice {
  sessions: Session[];
  currentSessionId: string | null;
  pendingMessage: string | null;
  setSessions: (sessions: Session[]) => void;
  setCurrentSession: (id: string | null) => void;
  setPendingMessage: (msg: string | null) => void;
  updateSessionTitle: (id: string, title: string) => void;
  removeSession: (id: string) => void;
  addSession: (session: Session) => void;
  pinSession: (id: string, pinned: boolean) => void;
}

const createSessionSlice: StateCreator<ChatState, [], [], SessionSlice> = (set) => ({
  sessions: [],
  currentSessionId: null,
  pendingMessage: null,
  setSessions: (sessions) => set({ sessions }),
  setCurrentSession: (id) => set({ currentSessionId: id }),
  setPendingMessage: (msg) => set({ pendingMessage: msg }),
  updateSessionTitle: (id, title) =>
    set((state) => ({
      sessions: state.sessions.map((s) => (s.id === id ? { ...s, title } : s)),
    })),
  removeSession: (id) =>
    set((state) => ({
      sessions: state.sessions.filter((s) => s.id !== id),
      currentSessionId: state.currentSessionId === id ? null : state.currentSessionId,
      messages: state.currentSessionId === id ? [] : state.messages,
    })),
  addSession: (session) =>
    set((state) => ({ sessions: [session, ...state.sessions] })),
  pinSession: (id, pinned) =>
    set((state) => ({
      sessions: state.sessions.map((s) => (s.id === id ? { ...s, pinned } : s)),
    })),
});

// ==================== Message Slice ====================

interface MessageSlice {
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
}

const createMessageSlice: StateCreator<ChatState, [], [], MessageSlice> = (set) => ({
  messages: [],
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
});

// ==================== Stream Slice ====================

interface StreamSlice {
  isStreaming: boolean;
  streamingContent: string;
  streamingThinking: string;
  streamingSessionId: string | null;
  currentSkill: string | null;
  pipelineInfo: { agentName: string; modelId: string; skillName: string } | null;
  chatMode: "simple" | "think";
  enableSearch: boolean;
  setIsStreaming: (v: boolean) => void;
  setStreamingSessionId: (id: string | null) => void;
  appendContent: (chunk: string) => void;
  appendThinking: (chunk: string) => void;
  resetStreaming: () => void;
  setCurrentSkill: (skill: string | null) => void;
  setPipelineInfo: (info: { agentName: string; modelId: string; skillName: string } | null) => void;
  setChatMode: (mode: "simple" | "think") => void;
  setEnableSearch: (v: boolean) => void;
  finalizeStreamMessage: (metadata?: { skill_used?: string; skill_name?: string; agents?: any[] }) => void;
}

const createStreamSlice: StateCreator<ChatState, [], [], StreamSlice> = (set, get) => ({
  isStreaming: false,
  streamingContent: "",
  streamingThinking: "",
  streamingSessionId: null,
  currentSkill: null,
  pipelineInfo: null,
  chatMode: "think",
  enableSearch: false,
  setIsStreaming: (v) => set({ isStreaming: v }),
  setStreamingSessionId: (id) => set({ streamingSessionId: id }),
  appendContent: (chunk) =>
    set((state) => {
      if (state.streamingSessionId && state.streamingSessionId !== state.currentSessionId) return state;
      return { streamingContent: state.streamingContent + chunk };
    }),
  appendThinking: (chunk) =>
    set((state) => {
      if (state.streamingSessionId && state.streamingSessionId !== state.currentSessionId) return state;
      return { streamingThinking: state.streamingThinking + chunk };
    }),
  resetStreaming: () =>
    set({ streamingContent: "", streamingThinking: "", currentSkill: null, pipelineInfo: null }),
  setCurrentSkill: (skill) => set({ currentSkill: skill }),
  setPipelineInfo: (info) => set({ pipelineInfo: info }),
  setChatMode: (mode) => set({ chatMode: mode }),
  setEnableSearch: (v) => set({ enableSearch: v }),
  finalizeStreamMessage: (metadata) => {
    const state = get();
    if (state.streamingSessionId && state.streamingSessionId !== state.currentSessionId) {
      set({ isStreaming: false, streamingContent: "", streamingThinking: "", streamingSessionId: null, currentSkill: null, pipelineInfo: null });
      return;
    }
    if (state.streamingContent || state.streamingThinking) {
      const newMsg: Message = {
        id: `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        role: "assistant" as const,
        content: state.streamingContent,
        thinking: state.streamingThinking || undefined,
        timestamp: new Date().toISOString(),
        skill_used: metadata?.skill_used,
        skill_name: metadata?.skill_name,
        agents: metadata?.agents,
      };
      set({
        messages: [...state.messages, newMsg],
        isStreaming: false,
        streamingContent: "",
        streamingThinking: "",
        streamingSessionId: null,
        currentSkill: null,
        pipelineInfo: null,
      });
    } else {
      set({ isStreaming: false, streamingContent: "", streamingThinking: "", streamingSessionId: null, currentSkill: null, pipelineInfo: null });
    }
  },
});

// ==================== 合并 Store ====================

type ChatState = SessionSlice & MessageSlice & StreamSlice;

export const useChatStore = create<ChatState>((...a) => ({
  ...createSessionSlice(...a),
  ...createMessageSlice(...a),
  ...createStreamSlice(...a),
}));
