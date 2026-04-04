import { create } from "zustand";
import type { Agent, Model } from "@/types";

interface SettingsState {
  agents: Agent[];
  models: Model[];
  activeTab: "agents" | "models" | "skills";

  setAgents: (agents: Agent[]) => void;
  setModels: (models: Model[]) => void;
  setActiveTab: (tab: "agents" | "models" | "skills") => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  agents: [],
  models: [],
  activeTab: "agents",

  setAgents: (agents) => set({ agents }),
  setModels: (models) => set({ models }),
  setActiveTab: (activeTab) => set({ activeTab }),
}));
