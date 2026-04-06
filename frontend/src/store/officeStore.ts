import { create } from "zustand";
import type { Appearance } from "@/components/office/PixelChar";

export type AgentAnim = "idle" | "walk" | "type" | "celebrate" | "error" | "sleep";

export interface OfficeAgent {
  id: string;
  name: string;
  color: string;
  x: number;
  y: number;
  targetX: number;
  targetY: number;
  anim: AgentAnim;
  flip: boolean;
  speech: string | null;
  speechType: "task" | "result" | "thinking" | "error" | null;
  frame: number;
  hat: boolean;
  appearance?: Appearance;
  facing?: "up" | "down";
}

export interface OfficeActivity {
  id: string;
  from: string;
  to?: string;
  type: "dispatch" | "working" | "result" | "error";
  content: string;
  time: number;
}

interface OfficeState {
  agents: Record<string, OfficeAgent>;
  managerId: string | null;
  activeWorkerId: string | null;
  activities: OfficeActivity[];
  tick: number;
}

interface OfficeActions {
  spawnAgent: (id: string, name: string, color: string, x: number, y: number, hat?: boolean, appearance?: Appearance, facing?: "up" | "down") => void;
  removeAgent: (id: string) => void;
  setAgentPosition: (id: string, x: number, y: number) => void;
  moveAgentTo: (id: string, x: number, y: number) => void;
  setAgentAnim: (id: string, anim: AgentAnim) => void;
  setAgentSpeech: (id: string, text: string | null, type?: "task" | "result" | "thinking" | "error") => void;
  setActiveWorker: (id: string | null) => void;
  addActivity: (act: Omit<OfficeActivity, "id" | "time">) => void;
  tickFrame: () => void;
  reset: () => void;
}

const DESK_POSITIONS: { x: number; y: number; facing: "up" | "down" }[] = [
  { x: 119, y: 282, facing: "down" },
  { x: 339, y: 282, facing: "down" },
  { x: 559, y: 282, facing: "down" },
  { x: 119, y: 342, facing: "up" },
  { x: 339, y: 342, facing: "up" },
  { x: 559, y: 342, facing: "up" },
];

const AGENT_COLORS = [
  "#4a9eff",
  "#4ade80",
  "#f59e0b",
  "#f472b6",
  "#a78bfa",
  "#fb923c",
];

let deskIndex = 0;

export function getNextDeskPosition() {
  const pos = DESK_POSITIONS[deskIndex % DESK_POSITIONS.length];
  deskIndex++;
  return pos;
}

export function getAgentColor(index: number) {
  return AGENT_COLORS[index % AGENT_COLORS.length];
}

export const useOfficeStore = create<OfficeState & OfficeActions>()((set, get) => ({
  agents: {},
  managerId: null,
  activeWorkerId: null,
  activities: [],
  tick: 0,

  spawnAgent: (id: string, name: string, color: string, x: number, y: number, hat?: boolean, appearance?: Appearance, facing?: "up" | "down") =>
    set((s) => {
      const isManager = id === "manager" || hat;
      const agent: OfficeAgent = {
        id,
        name,
        color,
        x,
        y,
        targetX: x,
        targetY: y,
        anim: "idle",
        flip: false,
        speech: null,
        speechType: null,
        frame: 0,
        hat: !!hat,
        appearance,
        facing: facing || "down",
      };
      return {
        agents: { ...s.agents, [id]: agent },
        ...(isManager ? { managerId: id } : {}),
      };
    }),

  removeAgent: (id) =>
    set((s) => {
      const { [id]: _, ...rest } = s.agents;
      return { agents: rest };
    }),

  setAgentPosition: (id, x, y) =>
    set((s) => {
      const agent = s.agents[id];
      if (!agent) return s;
      return { agents: { ...s.agents, [id]: { ...agent, x, y } } };
    }),

  moveAgentTo: (id, x, y) =>
    set((s) => {
      const agent = s.agents[id];
      if (!agent) return s;
      return {
        agents: {
          ...s.agents,
          [id]: { ...agent, targetX: x, targetY: y, anim: "walk" },
        },
      };
    }),

  setAgentAnim: (id, anim) =>
    set((s) => {
      const agent = s.agents[id];
      if (!agent) return s;
      return { agents: { ...s.agents, [id]: { ...agent, anim } } };
    }),

  setAgentSpeech: (id, text, type) =>
    set((s) => {
      const agent = s.agents[id];
      if (!agent) return s;
      return {
        agents: {
          ...s.agents,
          [id]: { ...agent, speech: text, speechType: type ?? null },
        },
      };
    }),

  setActiveWorker: (id) => set({ activeWorkerId: id }),

  addActivity: (act) =>
    set((s) => ({
      activities: [
        { ...act, id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`, time: Date.now() },
        ...s.activities,
      ].slice(0, 50),
    })),

  tickFrame: () => {
    const s = get();
    const nextAgents = { ...s.agents };
    let changed = false;

    for (const id of Object.keys(nextAgents)) {
      const a = nextAgents[id];
      let { x, y, targetX, targetY, anim, frame, flip } = a;
      const speed = 2;

      if (anim === "walk") {
        const dx = targetX - x;
        const dy = targetY - y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < speed + 1) {
          x = targetX;
          y = targetY;
          anim = "idle";
        } else {
          x += (dx / dist) * speed;
          y += (dy / dist) * speed;
          flip = dx < 0;
        }
        changed = true;
      }

      const newFrame = frame + 1;
      if (newFrame !== a.frame || changed) {
        nextAgents[id] = { ...a, x, y, anim, frame: newFrame, flip };
        changed = true;
      }
    }

    if (changed) {
      set({ agents: nextAgents, tick: s.tick + 1 });
    } else {
      set({ tick: s.tick + 1 });
    }
  },

  reset: () =>
    set({
      agents: {},
      managerId: null,
      activeWorkerId: null,
      activities: [],
      tick: 0,
    }),
}));
