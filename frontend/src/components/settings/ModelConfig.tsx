/**
 * 模型配置组件
 *
 * 设置页面的模型配置 Tab，功能包括：
 * - 显示内置模型列表（按提供商分组，标注思考模型）
 * - 添加自定义模型（弹窗表单：名称、提供商、API Key、Base URL 等）
 * - 测试模型连接（自动检测 FC 支持并更新 capabilities）
 */

"use client";

import { useState, useEffect } from "react";
import { useSettingsStore } from "@/store/settingsStore";
import { useI18n } from "@/store/i18nStore";
import { useToast } from "@/components/ui/Toast";
import { api, configApi } from "@/lib/api";
import type { Model } from "@/types";

const CAPABILITY_I18N_KEYS: Record<string, string> = {
  tool_use: "capToolUse",
};

const CAPABILITY_COLORS: Record<string, string> = {
  tool_use: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

function CapabilityBadge({ cap }: { cap: string }) {
  const { t } = useI18n();
  const i18nKey = CAPABILITY_I18N_KEYS[cap];
  if (!i18nKey) return null;
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${CAPABILITY_COLORS[cap] || "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"}`}>
      🔧 {t(i18nKey)}
    </span>
  );
}

export function ModelConfig() {
  const { t } = useI18n();
  const { models, setModels } = useSettingsStore();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    provider: "openai",
    model_id: "",
    base_url: "",
    api_key: "",
    description: "",
    supports_thinking: false,
    capabilities: [] as string[],
  });
  const [testing, setTesting] = useState<string | null>(null);
  const [searchConfig, setSearchConfig] = useState<{ provider: string; api_key_configured: boolean; api_key_masked: string } | null>(null);
  const [editingSearch, setEditingSearch] = useState(false);
  const [searchForm, setSearchForm] = useState({ provider: "", api_key: "" });
  const [savingSearch, setSavingSearch] = useState(false);

  const reloadSearchConfig = () => {
    configApi.search.get().then(setSearchConfig).catch(() => {});
  };

  useEffect(() => {
    reloadSearchConfig();
  }, []);

  const builtin = models.filter((m) => m.builtin);
  const custom = models.filter((m) => !m.builtin);

  const handleCreate = async () => {
    try {
      await api.models.create(form as any);
      const data = await api.models.list();
      setModels(data.models || []);
      closeForm();
      toast.success(t("createSuccess"));
    } catch (e) {
      toast.error(t("createFailed") + ": " + (e as Error).message);
    }
  };

  const handleEdit = (model: Model) => {
    setEditingId(model.id);
    setForm({
      name: model.name,
      provider: model.provider,
      model_id: model.model_id,
      base_url: model.base_url,
      api_key: model.api_key || "",
      description: model.description || "",
      supports_thinking: model.supports_thinking || false,
      capabilities: model.capabilities || [],
    });
    setShowForm(true);
  };

  const handleUpdate = async () => {
    if (!editingId) return;
    try {
      await api.models.update(editingId, form as any);
      const data = await api.models.list();
      setModels(data.models || []);
      closeForm();
      toast.success(t("updateSuccess"));
    } catch (e) {
      toast.error(t("updateFailed") + ": " + (e as Error).message);
    }
  };

  const closeForm = () => {
    setShowForm(false);
    setEditingId(null);
    setForm({
      name: "",
      provider: "openai",
      model_id: "",
      base_url: "",
      api_key: "",
      description: "",
      supports_thinking: false,
      capabilities: [],
    });
  };

  const handleDelete = async (id: string) => {
    try {
      await api.models.delete(id);
      const data = await api.models.list();
      setModels(data.models || []);
      toast.success(t("deleteSuccess"));
    } catch (e) {
      toast.error(t("deleteFailed"));
    } finally {
      setDeleteConfirm(null);
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const result = await api.models.test(id);
      if (result.success) {
        const data = await api.models.list();
        setModels(data.models || []);
        const fcInfo = result.capabilities?.includes("tool_use")
          ? ` | ✅ FC` : "";
        toast.success(t("testSuccess") + fcInfo);
      } else {
        toast.error(t("testFailed") + ": " + result.message);
      }
    } catch (e) {
      toast.error(t("testFailed") + ": " + (e as Error).message);
    } finally {
      setTesting(null);
    }
  };

  return (
    <div>
      <div className="mb-6 border border-[var(--border)] rounded-xl p-4 space-y-4">
        <h2 className="text-lg font-medium">{t("systemConfig")}</h2>

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-medium">{t("searchService")}</div>
              <div className="text-xs text-[var(--text-3)] mt-0.5">{t("searchServiceDesc")}</div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setSearchForm({ provider: searchConfig?.provider || "zhipu_search", api_key: "" });
                  setEditingSearch(true);
                }}
                className="text-xs px-2.5 py-1 rounded-lg border border-[var(--border)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors"
              >
                {t("edit")}
              </button>
              <span className={`text-xs px-2 py-0.5 rounded-full ${searchConfig?.api_key_configured ? "bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400" : "bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400"}`}>
                {searchConfig?.api_key_configured ? `✅ ${t("configured")}` : `❌ ${t("notConfigured")}`}
              </span>
            </div>
          </div>
          {searchConfig && (
            <div className="text-xs text-[var(--text-3)] bg-[var(--bg-hover)] rounded-lg px-3 py-2">
              {searchConfig.provider} {searchConfig.api_key_configured ? "✅" : "❌"}
            </div>
          )}
        </div>
      </div>

      <div className="mb-6">
        <h2 className="text-lg font-medium mb-4">{t("builtinModels")}</h2>
        <div className="space-y-3">
          {builtin.map((model) => (
            <div key={model.id} className="border border-[var(--border)] rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium flex items-center gap-2 flex-wrap">
                    {model.name}
                    {model.supports_thinking && (
                      <span className="text-xs bg-[var(--accent-bg)] text-[var(--accent)] px-2 py-0.5 rounded-full">{t("supportsThinking")}</span>
                    )}
                    {(model.capabilities || []).map((cap) => (
                      <CapabilityBadge key={cap} cap={cap} />
                    ))}
                  </div>
                  <div className="text-sm text-[var(--text-2)] mt-0.5">{model.description}</div>
                </div>
                <span className="text-xs text-[var(--text-3)]">{model.provider}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium">{t("customModels")}</h2>
          <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-[var(--accent)] text-white rounded-lg text-sm hover:bg-[var(--accent-light)]">
            {t("addModel")}
          </button>
        </div>
        {custom.length === 0 ? (
          <div className="text-center py-8 text-[var(--text-3)] text-sm border border-dashed border-[var(--border)] rounded-xl">
            {t("noCustomModels")}
          </div>
        ) : (
          <div className="space-y-3">
            {custom.map((model) => (
              <div key={model.id} className="border border-[var(--border)] rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium flex items-center gap-2 flex-wrap">
                      {model.name}
                      {model.supports_thinking && <span className="text-xs bg-[var(--accent-bg)] text-[var(--accent)] px-2 py-0.5 rounded-full">{t("supportsThinking")}</span>}
                      {(model.capabilities || []).map((cap) => (
                        <CapabilityBadge key={cap} cap={cap} />
                      ))}
                    </div>
                    <div className="text-sm text-[var(--text-2)] mt-0.5">{model.model_id} · {model.base_url}</div>
                    {model.description && (
                      <div className="text-xs text-[var(--text-3)] mt-0.5">{model.description}</div>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleEdit(model)} className="px-3 py-1.5 text-sm border border-[var(--border)] rounded-lg hover:bg-[var(--bg-hover)]">{t("edit")}</button>
                    <button onClick={() => handleTest(model.id)} disabled={testing === model.id} className="px-3 py-1.5 text-sm border border-[var(--border)] rounded-lg hover:bg-[var(--bg-hover)] disabled:opacity-50">
                      {testing === model.id ? t("testing") : t("test")}
                    </button>
                    <button onClick={() => setDeleteConfirm(model.id)} className="px-3 py-1.5 text-sm border border-[var(--red)]/30 text-[var(--red)] rounded-lg hover:bg-red-50">{t("delete")}</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={closeForm}>
          <div className="bg-[var(--bg)] rounded-2xl p-6 w-[520px] max-w-[90vw] max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-medium mb-4">{editingId ? t("editModel") : t("addCustomModel")}</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("modelName")}</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="DeepSeek R1" className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("provider")}</label>
                <select value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]">
                  <option value="openai">OpenAI</option>
                  <option value="deepseek">DeepSeek</option>
                  <option value="zhipu">智谱 AI</option>
                  <option value="dashscope">阿里云百炼</option>
                  <option value="moonshot">Moonshot AI</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("apiBaseUrl")}</label>
                <input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} placeholder="https://api.openai.com/v1/" className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("apiKey")}</label>
                <input type="password" value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })} placeholder="sk-..." className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("modelId")}</label>
                <input value={form.model_id} onChange={(e) => setForm({ ...form, model_id: e.target.value })} placeholder="gpt-4, deepseek-reasoner" className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" />
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("modelDescription")}</label>
                <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder={t("modelDescPlaceholder")} className="w-full px-3 py-2 border border-[var(--border)] rounded-lg text-sm focus:outline-none focus:border-[var(--accent)]" />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="thinking" checked={form.supports_thinking} onChange={(e) => setForm({ ...form, supports_thinking: e.target.checked })} />
                <label htmlFor="thinking" className="text-sm text-[var(--text-2)]">{t("supportsThinkingOutput")}</label>
              </div>
              <div className="text-xs text-[var(--text-3)] bg-[var(--bg-hover)] rounded-lg px-3 py-2">
                {t("capabilitiesAutoDetect")}
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={closeForm} className="flex-1 px-4 py-2 border border-[var(--border)] rounded-lg text-sm hover:bg-[var(--bg-hover)]">{t("cancel")}</button>
              <button onClick={editingId ? handleUpdate : handleCreate} className="flex-1 px-4 py-2 bg-[var(--accent)] text-white rounded-lg text-sm hover:bg-[var(--accent-light)]">{t("save")}</button>
            </div>
          </div>
        </div>
      )}

      {editingSearch && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setEditingSearch(false)}>
          <div className="bg-[var(--bg)] rounded-2xl p-6 w-[480px] max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-medium mb-4">{t("searchService")}</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("searchProvider")}</label>
                <select
                  value={searchForm.provider}
                  onChange={(e) => setSearchForm({ ...searchForm, provider: e.target.value })}
                  className="w-full px-3 py-2 text-sm border border-[var(--border)] rounded-lg bg-[var(--bg)] focus:outline-none focus:border-[var(--accent)]"
                >
                  <option value="zhipu_search">智谱 Search API</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-[var(--text-2)] mb-1">{t("searchApiKey")}</label>
                <input
                  value={searchForm.api_key}
                  onChange={(e) => setSearchForm({ ...searchForm, api_key: e.target.value })}
                  placeholder={searchConfig?.api_key_configured ? t("searchKeyPlaceholder") : "sk-xxx"}
                  className="w-full px-3 py-2 text-sm border border-[var(--border)] rounded-lg bg-[var(--bg)] focus:outline-none focus:border-[var(--accent)] font-mono"
                />
                <div className="text-xs text-[var(--text-3)] mt-1">{t("searchKeyHint")}</div>
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setEditingSearch(false)} className="flex-1 px-4 py-2 border border-[var(--border)] rounded-lg text-sm hover:bg-[var(--bg-hover)]">{t("cancel")}</button>
              <button
                onClick={async () => {
                  setSavingSearch(true);
                  try {
                    await configApi.search.update(searchForm);
                    setEditingSearch(false);
                    reloadSearchConfig();
                    toast.success(t("updateSuccess"));
                  } catch (e) {
                    toast.error(t("updateFailed") + ": " + (e as Error).message);
                  } finally {
                    setSavingSearch(false);
                  }
                }}
                disabled={savingSearch}
                className="flex-1 px-4 py-2 bg-[var(--accent)] text-white rounded-lg text-sm hover:bg-[var(--accent-light)] disabled:opacity-50"
              >
                {savingSearch ? t("saving") : t("save")}
              </button>
            </div>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setDeleteConfirm(null)}>
          <div className="bg-[var(--bg)] rounded-2xl shadow-2xl p-6 w-[360px] animate-fade-in-up" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-[var(--text)] mb-2">{t("deleteModelTitle")}</h3>
            <p className="text-sm text-[var(--text-2)] mb-5">{t("deleteModelDesc")}</p>
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
