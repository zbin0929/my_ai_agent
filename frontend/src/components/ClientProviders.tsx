/**
 * 客户端 Provider 包装器
 *
 * 将所有需要 "use client" 的 Provider 集中在此处，
 * 避免在 Server Component 的 layout.tsx 中使用客户端代码。
 */

"use client";

import { ThemeProvider } from "@/components/ThemeProvider";
import { ToastProvider } from "@/components/ui/Toast";

export function ClientProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <ToastProvider>{children}</ToastProvider>
    </ThemeProvider>
  );
}
