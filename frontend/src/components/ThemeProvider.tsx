/**
 * 主题提供者组件
 *
 * 优化记录：
 * - [深色模式] 监听 themeStore 并将 data-theme 属性应用到 <html> 元素
 * - [系统跟随] system 模式下监听 prefers-color-scheme 变化实时切换
 * - [无闪烁] useLayoutEffect 确保在首次渲染前应用主题
 */

"use client";

import { useEffect, useLayoutEffect } from "react";
import { useThemeStore, resolveTheme } from "@/store/themeStore";

const useIsomorphicLayoutEffect =
  typeof window !== "undefined" ? useLayoutEffect : useEffect;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const mode = useThemeStore((s) => s.mode);

  useIsomorphicLayoutEffect(() => {
    const resolved = resolveTheme(mode);
    document.documentElement.setAttribute("data-theme", resolved);
  }, [mode]);

  // system 模式下监听系统主题切换
  useEffect(() => {
    if (mode !== "system") return;

    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      document.documentElement.setAttribute(
        "data-theme",
        e.matches ? "dark" : "light"
      );
    };
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [mode]);

  return <>{children}</>;
}
