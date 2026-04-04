"use client";

import { useState, useEffect } from "react";
import { useI18n } from "@/store/i18nStore";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import type { Skill, SkillConfigSchemaItem } from "@/types";

const ICON_MAP: Record<string, string> = {
  image: "🖼️",
  audio: "🔊",
  web: "🌐",
  "🔧": "🔧",
};

export function SkillManager() {
  const { t } = useI18n();
  const toast = useToast();
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [configForm, setConfigForm] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const reloadSkills = async () => {
    try {
      const data = await api.skills.list();
      setSkills(data.skills || []);
    } catch {
      toast.error(t("loadFailed"));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    reloadSkills();
  }, []);

  const startEdit = (skill: Skill) => {
    setEditingSkill(skill);
    const form: Record<string, string> = {};
    (skill.config_schema || []).forEach((item) => {
      form[item.key] = (skill.config || {})[item.key] ?? item.default ?? "";
    });
    setConfigForm(form);
  };

  const handleSave = async () => {
    if (!editingSkill) return;
    setSaving(true);
    try {
      await api.skills.saveConfig(editingSkill.id, configForm);
      setEditingSkill(null);
      reloadSkills();
      toast.success(t("updateSuccess"));
    } catch (e) {
      toast.error(t("updateFailed") + ": " + (e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const getConfigStatus = (skill: Skill): "ok" | "missing" | "none" => {
    const schema = skill.config_schema || [];
    if (schema.length === 0) return "none";
    const hasRequired = schema.some((s) => s.required);
    if (!hasRequired) return "none";
    const config = skill.config || {};
    const allConfigured = schema
      .filter((s) => s.required)
      .every((s) => config[s.key]);
    return allConfigured ? "ok" : "missing";
  };

  const renderConfigInput = (item: SkillConfigSchemaItem) => {
    const value = configForm[item.key] || "";

    if (item.type === "select") {
      return (
        <select
          value={value}
          onChange={(e) => setConfigForm({ ...configForm, [item.key]: e.target.value })}
          className="w-full px-3 py-2 text-sm border border-[var(--border)] rounded-lg bg-[var(--bg)] focus:outline-none focus:border-[var(--accent)]"
        >
          {(item.options || []).map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      );
    }

    if (item.type === "boolean") {
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={value === "true"}
            onChange={(e) => setConfigForm({ ...configForm, [item.key]: e.target.checked ? "true" : "false" })}
            className="w-4 h-4 rounded border-[var(--border)] text-[var(--accent)]"
          />
          <span className="text-sm text-[var(--text-2)]">{item.label}</span>
        </label>
      );
    }

    return (
      <input
        type={item.type === "password" ? "password" : item.type === "number" ? "number" : "text"}
        value={value}
        onChange={(e) => setConfigForm({ ...configForm, [item.key]: e.target.value })}
        placeholder={item.type === "password" ? t("enterApiKey") : (item.env_hint ? `${t("envVarHint")}: ${item.env_hint}` : "")}
        className="w-full px-3 py-2 text-sm border border-[var(--border)] rounded-lg bg-[var(--bg)] focus:outline-none focus:border-[var(--accent)] font-mono"
      />
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-[var(--text-3)]">
        {t("loading")}
      </div>
    );
  }

  const builtinSkills = skills.filter((s) => s.builtin);
  const customSkills = skills.filter((s) => !s.builtin);

  return (
    <div>
      <div className="mb-6">
        <h2 className="text-lg font-medium mb-1">{t("skillManagement")}</h2>
        <p className="text-sm text-[var(--text-3)]">{t("skillManagementDesc")}</p>
      </div>

      <div className="space-y-3">
        {builtinSkills.map((skill) => {
          const status = getConfigStatus(skill);
          return (
            <div
              key={skill.id}
              className="border border-[var(--border)] rounded-xl p-4 hover:border-[var(--accent)]/30 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg">{ICON_MAP[skill.icon] || "🔧"}</span>
                    <span className="font-medium">{skill.name}</span>
                    {skill.builtin && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-[var(--accent)]/10 text-[var(--accent)]">
                        {t("builtin")}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-[var(--text-2)] mb-2">{skill.description}</p>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {skill.triggers.slice(0, 5).map((trigger) => (
                      <span
                        key={trigger}
                        className="text-xs px-2 py-0.5 rounded-full bg-[var(--bg-sidebar)] text-[var(--text-3)]"
                      >
                        {trigger}
                      </span>
                    ))}
                    {skill.triggers.length > 5 && (
                      <span className="text-xs text-[var(--text-3)]">
                        +{skill.triggers.length - 5}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-[var(--text-3)]">{t("apiConfig")}:</span>
                    {status === "none" && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400">
                        {t("noConfigNeeded")}
                      </span>
                    )}
                    {status === "ok" && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-400">
                        ✅ {t("configured")}
                      </span>
                    )}
                    {status === "missing" && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400">
                        ❌ {t("notConfigured")}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => startEdit(skill)}
                  className="ml-4 px-3 py-1.5 text-sm border border-[var(--border)] rounded-lg hover:border-[var(--accent)] hover:text-[var(--accent)] transition-colors shrink-0"
                >
                  {t("edit")}
                </button>
              </div>
            </div>
          );
        })}

        {customSkills.length > 0 && (
          <>
            <div className="flex items-center gap-2 pt-4 pb-1">
              <div className="h-px flex-1 bg-[var(--border)]" />
              <span className="text-xs text-[var(--text-3)]">{t("customSkills")}</span>
              <div className="h-px flex-1 bg-[var(--border)]" />
            </div>
            {customSkills.map((skill) => (
              <div
                key={skill.id}
                className="border border-[var(--border)] rounded-xl p-4 hover:border-[var(--accent)]/30 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span>{ICON_MAP[skill.icon] || "🔧"}</span>
                      <span className="font-medium">{skill.name}</span>
                    </div>
                    <p className="text-sm text-[var(--text-2)]">{skill.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>

      {editingSkill && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={() => setEditingSkill(null)}>
          <div className="bg-[var(--bg)] rounded-2xl p-6 w-[520px] max-w-[90vw] max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">{editingSkill.name}</h3>
              <button onClick={() => setEditingSkill(null)} className="p-1 hover:bg-[var(--bg-hover)] rounded-lg">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12" /></svg>
              </button>
            </div>

            <div className="space-y-4">
              {(editingSkill.config_schema || []).map((item) => (
                <div key={item.key}>
                  {item.type !== "boolean" && (
                    <label className="block text-sm font-medium text-[var(--text-2)] mb-1.5">{item.label}</label>
                  )}
                  {renderConfigInput(item)}
                  <p className="text-xs text-[var(--text-3)] mt-1">{item.description}</p>
                </div>
              ))}

              {(!editingSkill.config_schema || editingSkill.config_schema.length === 0) && (
                <div className="text-center py-8 text-[var(--text-3)]">
                  {t("noConfigNeeded")}
                </div>
              )}
            </div>

            {editingSkill.config_schema && editingSkill.config_schema.length > 0 && (
              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => setEditingSkill(null)}
                  className="flex-1 px-4 py-2.5 border border-[var(--border)] rounded-xl text-sm hover:bg-[var(--bg-hover)] transition-colors"
                >
                  {t("cancel")}
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex-1 px-4 py-2.5 bg-[var(--accent)] text-white rounded-xl text-sm hover:bg-[var(--accent-light)] disabled:opacity-50 transition-colors"
                >
                  {saving ? t("saving") : t("save")}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
