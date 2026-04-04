/**
 * Agent（员工）管理组件
 *
 * 设置页面的 Agent 管理 Tab，功能包括：
 * - 显示 Agent 列表（含默认标记、能力标签）
 * - 新建 Agent（弹窗表单：名称、角色、模型、温度等）
 * - 编辑 Agent 配置
 * - 删除 Agent（默认 Agent 不可删除）
 */

"use client";
import { useState, useRef, useEffect } from "react";
import { useSettingsStore } from "@/store/settingsStore";
import { useI18n } from "@/store/i18nStore";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import type { Agent } from "@/types";

const CAPABILITY_I18N_KEYS: Record<string, string> = {
  tool_use: "capToolUse",
};

const CAPABILITY_COLORS: Record<string, string> = {
  tool_use: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

const ROLE_PRESETS = [
  { labelKey: "roleImageGen", roleKey: "roleImageGenDesc", model_hint: "cogview" },
  { labelKey: "roleDataAnalyst", roleKey: "roleDataAnalystDesc", model_hint: "deepseek" },
  { labelKey: "roleResearcher", roleKey: "roleResearcherDesc", model_hint: "" },
  { labelKey: "roleGeneral", roleKey: "roleGeneralDesc", model_hint: "" },
];

const defaultForm = {
  name: "",
  avatar: "🤖",
  role: "",
  description: "",
  model_id: "",
  model_provider: "zhipu",
  temperature: 0.7,
  enable_thinking: false,
  custom_api_key: "",
  custom_base_url: "",
  skills: [] as string[],
};

interface AvailableSkill {
  id: string;
  name: string;
  description: string;
  icon: string;
  config_status: "ok" | "missing" | "none";
}

export function AgentManager() {
  const { t } = useI18n();
  const { agents, setAgents, models } = useSettingsStore();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);
  const [editAgent, setEditAgent] = useState<Agent | null>(null);
  const [form, setForm] = useState(defaultForm);
  const [modelSearch, setModelSearch] = useState("");
  const [showModelDropdown, setShowModelDropdown] = useState(false);
  const [availableSkills, setAvailableSkills] = useState<AvailableSkill[]>([]);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.agents.availableSkills().then((data) => {
      setAvailableSkills((data.skills || []).map((s: Record<string, unknown>) => ({
        id: s.id as string,
        name: s.name as string,
        description: s.description as string,
        icon: s.icon as string,
        config_status: (s.config_status as "ok" | "missing" | "none") || "none",
      })));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (modelDropdownRef.current && !modelDropdownRef.current.contains(e.target as Node)) {
        setShowModelDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const filteredModels = models.filter((m) => {
    const q = modelSearch.toLowerCase();
    return m.name.toLowerCase().includes(q) || m.model_id.toLowerCase().includes(q) || m.provider.toLowerCase().includes(q);
  });

  const selectedModel = models.find((m) => m.model_id === form.model_id);

  const getAgentType = () => {
    const hasSkills = form.skills && form.skills.length > 0;
    const hasModel = !!form.model_id;
    if (hasSkills && !hasModel) return "runner";
    if (hasSkills && hasModel) return "smart";
    return "agent";
  };

  const agentType = getAgentType();

  const selectModel = (model: typeof models[0]) => {
    setForm((prev) => ({ ...prev, model_id: model.model_id, model_provider: model.provider }));
    setModelSearch("");
    setShowModelDropdown(false);
  };

  const applyPreset = (preset: typeof ROLE_PRESETS[0]) => {
    const { t } = useI18n.getState();
    const updates: Partial<typeof form> = { role: t(preset.roleKey) };
    const label = t(preset.labelKey);
    if (label && !form.name) {
      updates.name = label;
    }
    if (preset.model_hint) {
      const hint = models.find((m) => m.model_id.toLowerCase().includes(preset.model_hint));
      if (hint) {
        updates.model_id = hint.model_id;
        updates.model_provider = hint.provider;
      }
    }
    setForm((prev) => ({ ...prev, ...updates }));
  };

  const handleCreate = async () => {
    try {
      const payload = { ...form, model_id: form.model_id || undefined };
      await api.agents.create(payload);
      const data = await api.agents.list();
      setAgents(data.agents || []);
      setShowForm(false);
      setForm(defaultForm);
      toast.success(t("createSuccess"));
    } catch (e) {
      toast.error(t("createFailed"));
    }
  };

  const handleUpdate = async () => {
    if (!editAgent) return;
    try {
      await api.agents.update(editAgent.id, form);
      const data = await api.agents.list();
      setAgents(data.agents || []);
      setEditAgent(null);
      toast.success(t("updateSuccess"));
    } catch (e) {
      toast.error(t("updateFailed") + ": " + (e as Error).message);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.agents.delete(id);
      const data = await api.agents.list();
      setAgents(data.agents || []);
      toast.success(t("deleteSuccess"));
    } catch (e) {
      toast.error(t("deleteFailed") + ": " + (e as Error).message);
    } finally {
      setDeleteConfirm(null);
    }
  };

  const startEdit = (agent: Agent) => {
    setEditAgent(agent);
    setForm({
      name: agent.name,
      avatar: agent.avatar,
      role: agent.role || "",
      description: agent.description || "",
      model_id: agent.model_id,
      model_provider: agent.model_provider,
      temperature: agent.temperature,
      enable_thinking: agent.enable_thinking || false,
      custom_api_key: agent.custom_api_key || "",
      custom_base_url: agent.custom_base_url || "",
      skills: agent.skills || [],
    });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium">{t("agentList")}</h2>
        <button
          onClick={() => { setForm(defaultForm); setShowForm(true); setEditAgent(null); }}
          className="px-3 py-1.5 text-sm bg-[var(--accent)] text-white rounded-lg hover:bg-[var(--accent-light)] transition-colors"
        >
          {t("newAgent")}
        </button>
      </div>

      <div className="space-y-3">
        {agents.map((agent) => (
          <div key={agent.id} className="border border-[var(--border)] rounded-xl p-4 hover:border-[var(--accent)]/30 transition-colors">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl">{agent.avatar}</span>
                  <span className="font-medium">{agent.name}</span>
                  {agent.is_default && (
                    <span className="text-xs bg-[var(--accent-bg)] text-[var(--accent)] px-2 py-0.5 rounded-full">
                      {t("defaultAgent")}
                    </span>
                  )}
                </div>
                <div className="text-sm text-[var(--text-2)] mt-0.5">
                  {agent.role && <span className="mr-2">{agent.role}</span>}
                  <span className="text-[var(--text-3)]">{agent.model_id}</span>
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => startEdit(agent)} className="px-3 py-1.5 text-sm border border-[var(--border)] rounded-lg hover:bg-[var(--bg-hover)] transition-colors">{t("edit")}</button>
                {!agent.is_default && (
                  <button onClick={() => setDeleteConfirm(agent.id)} className="px-3 py-1.5 text-sm border border-[var(--red)]/30 text-[var(--red)] rounded-lg hover:bg-red-50 transition-colors">{t("delete")}</button>
                )}
              </div>
            </div>
            {agent.capabilities && agent.capabilities.length > 0 && (
              <div className="flex gap-1.5 mt-2 ml-11">
                {agent.capabilities.map((cap) => (
                  <span
                    key={cap}
                    className={`text-xs px-2 py-0.5 rounded-full ${CAPABILITY_COLORS[cap] || "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"}`}
                  >
                    {CAPABILITY_I18N_KEYS[cap] ? t(CAPABILITY_I18N_KEYS[cap]) : cap}
                  </span>
                ))}
              </div>
            )}
            {agent.skills && agent.skills.length > 0 && (
              <div className="flex gap-1.5 mt-1 ml-11">
                {agent.skills.map((sid) => {
                  const skillInfo = availableSkills.find((s) => s.id === sid);
                  return (
                    <span
                      key={sid}
                      className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                    >
                      {skillInfo ? `${skillInfo.icon} ${skillInfo.name}` : sid}
                    </span>
                  );
                })}
              </div>
            )}
            {agent.enable_thinking && (
              <div className="flex gap-1.5 mt-1 ml-11">
                <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
                  🧠 {t("deepThinking")}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {(showForm || editAgent) && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => { setShowForm(false); setEditAgent(null); }}>
          <div className="bg-[var(--bg)] rounded-2xl p-6 w-[520px] max-w-[90vw] max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-medium mb-4">{editAgent ? t("editAgent") : t("createAgent")}</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("name")}</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" placeholder={t("agentNamePlaceholder")} />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("avatar")}</label>
                <input value={form.avatar} onChange={(e) => setForm({ ...form, avatar: e.target.value })} className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("roleDescription")}</label>
                <input value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" placeholder={t("rolePlaceholder")} />
                {!editAgent && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {ROLE_PRESETS.map((preset) => (
                      <button
                        key={preset.labelKey}
                        type="button"
                        onClick={() => applyPreset(preset)}
                        className="text-xs px-2.5 py-1 rounded-full border border-[var(--border)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors"
                      >
                        {t(preset.labelKey)}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("description")}</label>
                <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("modelSelect")}</label>
                <div className="relative" ref={modelDropdownRef}>
                  <div
                    className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm cursor-pointer flex items-center justify-between hover:border-[var(--accent)]"
                    onClick={() => setShowModelDropdown(!showModelDropdown)}
                  >
                    <span>
                      {selectedModel ? `${selectedModel.name} (${selectedModel.model_id})` : t("modelOptional")}
                    </span>
                    <span className="text-[var(--text-3)]">▼</span>
                  </div>
                  {showModelDropdown && (
                    <div className="mt-1 border border-[var(--border)] rounded-lg bg-[var(--bg)] shadow-lg max-h-56 overflow-hidden">
                      <div className="p-2 border-b border-[var(--border)]">
                        <input
                          value={modelSearch}
                          onChange={(e) => setModelSearch(e.target.value)}
                          placeholder={t("searchModel")}
                          className="w-full px-2 py-1.5 text-sm border border-[var(--border)] rounded-md focus:outline-none focus:border-[var(--accent)]"
                          autoFocus
                        />
                      </div>
                      <div className="overflow-y-auto max-h-52">
                        <div
                          className={`px-3 py-2 text-sm cursor-pointer hover:bg-[var(--bg-hover)] ${!form.model_id ? "bg-[var(--accent-bg)] text-[var(--accent)]" : "text-[var(--text-3)]"}`}
                          onClick={() => { setForm((prev) => ({ ...prev, model_id: "", model_provider: "zhipu" })); setShowModelDropdown(false); }}
                        >
                          {t("noModel")}
                        </div>
                        {filteredModels.length === 0 ? (
                          <div className="px-3 py-2 text-sm text-[var(--text-3)]">{t("noModelsFound")}</div>
                        ) : (
                          filteredModels.map((model) => (
                            <div
                              key={model.id}
                              className={`px-3 py-2 text-sm cursor-pointer hover:bg-[var(--bg-hover)] ${model.model_id === form.model_id ? "bg-[var(--accent-bg)] text-[var(--accent)]" : ""}`}
                              onClick={() => selectModel(model)}
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">{model.name}</span>
                                  {model.capabilities && model.capabilities.length > 0 && (
                                    <div className="flex gap-1">
                                      {model.capabilities.filter((c) => c !== "text").map((cap) => (
                                        <span key={cap} className={`text-[10px] px-1.5 py-0 rounded-full ${CAPABILITY_COLORS[cap] || "bg-gray-100 text-gray-500"}`}>
                                          {CAPABILITY_I18N_KEYS[cap] ? t(CAPABILITY_I18N_KEYS[cap]) : cap}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                  {model.supports_thinking && (
                                    <span className="text-[10px] px-1.5 py-0 rounded-full bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">🧠</span>
                                  )}
                                </div>
                                <span className="text-xs text-[var(--text-3)] shrink-0 ml-2">{model.provider}</span>
                              </div>
                              {model.description && (
                                <div className="text-xs text-[var(--text-3)] mt-0.5 truncate">{model.description}</div>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>
                {selectedModel && (
                  <button
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, model_id: "", model_provider: "zhipu" }))}
                    className="text-xs text-[var(--text-3)] hover:text-[var(--red)] transition-colors ml-2"
                  >
                    ✕ {t("clearModel")}
                  </button>
                )}
                {selectedModel && selectedModel.description && (
                  <div className="text-xs text-[var(--text-3)] ml-2 mt-0.5">{selectedModel.description}</div>
                )}
                {selectedModel && selectedModel.capabilities && (
                  <div className="flex gap-1.5">
                    <span className="text-xs text-[var(--text-3)]">{t("modelCapabilities")}</span>
                    {selectedModel.capabilities.map((cap) => (
                      <span key={cap} className={`text-xs px-2 py-0.5 rounded-full ${CAPABILITY_COLORS[cap] || "bg-gray-100 text-gray-500"}`}>
                        {CAPABILITY_I18N_KEYS[cap] ? t(CAPABILITY_I18N_KEYS[cap]) : cap}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("temperature")} ({form.temperature})</label>
                <input type="range" min="0" max="1" step="0.1" value={form.temperature} onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })} className="w-full" />
              </div>
              <div className="flex gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.enable_thinking}
                    onChange={(e) => setForm({ ...form, enable_thinking: e.target.checked })}
                    className="w-4 h-4 rounded border-[var(--border)] accent-[var(--accent)]"
                  />
                  <span className="text-sm">{t("deepThinking")}</span>
                </label>
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("bindSkills")}</label>
                {availableSkills.length === 0 ? (
                  <div className="text-xs text-[var(--text-3)] py-2">{t("noSkillsAvailable")}</div>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {availableSkills.map((skill) => {
                      const bound = (form.skills || []).includes(skill.id);
                      const cfgStatus = skill.config_status;
                      return (
                        <button
                          key={skill.id}
                          type="button"
                          onClick={() => {
                            const current = form.skills || [];
                            const next = bound
                              ? current.filter((s) => s !== skill.id)
                              : [...current, skill.id];
                            setForm({ ...form, skills: next });
                          }}
                          className={`text-xs px-2.5 py-1.5 rounded-full border transition-colors flex items-center gap-1 ${
                            bound
                              ? "bg-[var(--accent-bg)] border-[var(--accent)] text-[var(--accent)]"
                              : "border-[var(--border)] hover:border-[var(--accent)] hover:text-[var(--accent)]"
                          }`}
                          title={skill.description}
                        >
                          {skill.icon} {skill.name}
                          {bound && ` ✓`}
                          {cfgStatus === "missing" && (
                            <span className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" title={t("notConfigured")} />
                          )}
                          {cfgStatus === "ok" && (
                            <span className="w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" title={t("configured")} />
                          )}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
              <div className={`rounded-lg p-3 text-sm ${
                agentType === "runner" ? "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-400" :
                agentType === "smart" ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400" :
                "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium">
                    {agentType === "runner" ? `⚡ ${t("typeRunner")}` :
                     agentType === "smart" ? `🧠 ${t("typeSmart")}` :
                     `💬 ${t("typeAgent")}`}
                  </span>
                </div>
                <div className="text-xs opacity-80">
                  {agentType === "runner" ? t("typeRunnerDesc") :
                   agentType === "smart" ? t("typeSmartDesc") :
                   t("typeAgentDesc")}
                </div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => { setShowForm(false); setEditAgent(null); }} className="flex-1 px-4 py-2 border border-[var(--border)] rounded-lg text-sm hover:bg-[var(--bg-hover)]">{t("cancel")}</button>
              <button onClick={editAgent ? handleUpdate : handleCreate} className="flex-1 px-4 py-2 bg-[var(--accent)] text-white rounded-lg text-sm hover:bg-[var(--accent-light)]">
                {editAgent ? t("save") : t("create")}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setDeleteConfirm(null)}>
          <div className="bg-[var(--bg)] rounded-2xl shadow-2xl p-6 w-[360px] animate-fade-in-up" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">{t("deleteAgentTitle")}</h3>
            <p className="text-sm text-[var(--text-2)] mb-5">{t("deleteAgentDesc")}</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="px-5 py-2 rounded-xl text-sm text-[var(--text-2)] hover:bg-[var(--bg-hover)] transition-all">
                {t("cancel")}
              </button>
              <button onClick={() => handleDelete(deleteConfirm)} className="px-5 py-2 rounded-xl text-sm bg-[var(--red)] text-white hover:opacity-90 transition-all shadow-sm">
                {t("confirm")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
