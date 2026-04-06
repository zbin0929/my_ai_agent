"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useI18n } from "@/store/i18nStore";

interface Stats {
  total_sessions: number;
  total_messages: number;
  today_messages: number;
  week_messages: number;
  month_messages: number;
  top_models: { model: string; count: number }[];
  top_skills: { skill: string; count: number }[];
}

export function StatsPanel() {
  const { t } = useI18n();
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.stats.get()
      .then(setStats)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center py-12 text-[var(--text-3)]">
        {t("statsLoadError")}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label={t("totalSessions")} value={stats.total_sessions} icon="💬" />
        <StatCard label={t("totalMessages")} value={stats.total_messages} icon="📝" />
        <StatCard label={t("todayMessages")} value={stats.today_messages} icon="📅" />
        <StatCard label={t("weekMessages")} value={stats.week_messages} icon="📊" />
      </div>

      {/* Top Models */}
      <div className="bg-[var(--bg)] rounded-xl border border-[var(--border)] p-4">
        <h3 className="text-sm font-medium text-[var(--text)] mb-3">{t("topModels")}</h3>
        {stats.top_models.length > 0 ? (
          <div className="space-y-2">
            {stats.top_models.map((m, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-2)] truncate flex-1">{m.model}</span>
                <span className="text-sm font-medium text-[var(--accent)] ml-2">{m.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--text-3)]">{t("noData")}</p>
        )}
      </div>

      {/* Top Skills */}
      <div className="bg-[var(--bg)] rounded-xl border border-[var(--border)] p-4">
        <h3 className="text-sm font-medium text-[var(--text)] mb-3">{t("topSkills")}</h3>
        {stats.top_skills.length > 0 ? (
          <div className="space-y-2">
            {stats.top_skills.map((s, i) => (
              <div key={i} className="flex items-center justify-between">
                <span className="text-sm text-[var(--text-2)] truncate flex-1">{s.skill}</span>
                <span className="text-sm font-medium text-[var(--accent)] ml-2">{s.count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[var(--text-3)]">{t("noData")}</p>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="bg-[var(--bg)] rounded-xl border border-[var(--border)] p-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{icon}</span>
        <span className="text-xs text-[var(--text-3)]">{label}</span>
      </div>
      <div className="text-2xl font-semibold text-[var(--text)]">{value.toLocaleString()}</div>
    </div>
  );
}
