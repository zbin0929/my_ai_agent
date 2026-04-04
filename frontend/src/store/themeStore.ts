/**
 * 主题状态管理 Store (Zustand + persist)
 *
 * 优化记录：
 * - [深色模式] 新增主题 store，支持 light/dark/system 三种模式
 * - [持久化] 使用 Zustand persist 中间件将主题偏好保存到 localStorage
 * - [系统跟随] system 模式下监听 prefers-color-scheme 媒体查询自动切换
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "light" | "dark" | "system";

interface ThemeState {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      mode: "system",
      setMode: (mode) => set({ mode }),
    }),
    { name: "theme-preference" }
  )
);

/** 根据当前 mode 计算实际应用的主题（light 或 dark） */
export function resolveTheme(mode: ThemeMode): "light" | "dark" {
  if (mode === "system") {
    if (typeof window !== "undefined") {
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    return "light";
  }
  return mode;
}
