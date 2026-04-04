/**
 * Next.js 根布局
 *
 * 定义 HTML 文档结构（lang、metadata）和全局 CSS 引入。
 * 所有页面共享此布局。
 *
 * 优化记录：
 * - [深色模式] 集成 ClientProviders（ThemeProvider）实现主题切换
 */

import type { Metadata } from "next";
import "./globals.css";
import { ClientProviders } from "@/components/ClientProviders";

export const metadata: Metadata = {
  title: "GymClaw",
  description: "GymClaw - Powered by LLM",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh" suppressHydrationWarning>
      <body>
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
