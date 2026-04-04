"use client";

import { useEffect } from "react";
import { useChatStore } from "@/store/chatStore";
import { useSettingsStore } from "@/store/settingsStore";
import { useI18n } from "@/store/i18nStore";
import { api } from "@/lib/api";
import { AgentManager } from "./AgentManager";
import { ModelConfig } from "./ModelConfig";
import { SkillManager } from "./SkillManager";

type TabKey = "agents" | "models" | "skills";

export function SettingsPage() {
  const { t } = useI18n();
  const { setCurrentSession } = useChatStore();
  const { activeTab, setActiveTab, setAgents, setModels } = useSettingsStore();

  const TABS: { key: TabKey; labelKey: string; icon: string }[] = [
    { key: "agents", labelKey: "tabAgents", icon: "🤖" },
    { key: "skills", labelKey: "tabSkills", icon: "⚡" },
    { key: "models", labelKey: "tabModels", icon: "🔑" },
  ];

  useEffect(() => {
    api.agents.list().then((d) => setAgents(d.agents || [])).catch(() => {});
    api.models.list().then((d) => setModels(d.models || [])).catch(() => {});
  }, [setAgents, setModels]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[900px] mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setCurrentSession(null)}
              className="p-2 hover:bg-[var(--bg-hover)] rounded-lg transition-colors"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <h1 className="text-xl font-semibold">{t("settingsTitle")}</h1>
          </div>
        </div>

        <div className="flex gap-1 mb-6 bg-[var(--bg-sidebar)] p-1 rounded-xl">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-[var(--bg)] text-[var(--accent)] shadow-sm"
                  : "text-[var(--text-2)] hover:text-[var(--text)]"
              }`}
            >
              {tab.icon} {t(tab.labelKey)}
            </button>
          ))}
        </div>

        <div>
          {activeTab === "agents" && <AgentManager />}
          {activeTab === "skills" && <SkillManager />}
          {activeTab === "models" && <ModelConfig />}
        </div>
      </div>
    </div>
  );
}
