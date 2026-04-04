/**
 * 主题切换按钮组件
 *
 * 优化记录：
 * - [深色模式] 提供 light/dark/system 三种模式的循环切换
 * - [图标反馈] 根据当前模式显示对应的太阳/月亮/系统图标
 */

"use client";

import React from "react";
import { useThemeStore, type ThemeMode } from "@/store/themeStore";

const icons: Record<ThemeMode, React.ReactNode> = {
  light: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  ),
  dark: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  ),
  system: (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
      <line x1="8" y1="21" x2="16" y2="21" />
      <line x1="12" y1="17" x2="12" y2="21" />
    </svg>
  ),
};

const labels: Record<ThemeMode, string> = {
  light: "浅色",
  dark: "深色",
  system: "跟随系统",
};

const cycle: ThemeMode[] = ["light", "dark", "system"];

export function ThemeToggle() {
  const mode = useThemeStore((s) => s.mode);
  const setMode = useThemeStore((s) => s.setMode);

  const next = () => {
    const idx = cycle.indexOf(mode);
    setMode(cycle[(idx + 1) % cycle.length]);
  };

  return (
    <button
      onClick={next}
      className="flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] text-[var(--text-2)] hover:bg-[var(--bg-hover)] transition-colors w-full"
      title={labels[mode]}
    >
      <span className="text-[var(--text-3)]">{icons[mode]}</span>
      <span>{labels[mode]}</span>
    </button>
  );
}
