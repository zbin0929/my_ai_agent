"use client";

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from "react";

export type ToastType = "success" | "error" | "info";

export interface ToastMessage {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

interface ToastContextType {
  showToast: (type: ToastType, message: string, duration?: number) => void;
  success: (message: string, duration?: number) => void;
  error: (message: string, duration?: number) => void;
  info: (message: string, duration?: number) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((type: ToastType, message: string, duration = 3000) => {
    const id = Math.random().toString(36).substr(2, 9);
    const toast: ToastMessage = { id, type, message, duration };
    setToasts((prev) => [...prev, toast]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
  }, []);

  const success = useCallback((message: string, duration?: number) => showToast("success", message, duration), [showToast]);
  const error = useCallback((message: string, duration?: number) => showToast("error", message, duration), [showToast]);
  const info = useCallback((message: string, duration?: number) => showToast("info", message, duration), [showToast]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast, success, error, info }}>
      {children}
      <div className="fixed top-4 right-4 z-[9999] space-y-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`
              flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg border min-w-[280px] max-w-[400px]
              animate-slide-in-right cursor-pointer hover:opacity-90 transition-opacity
              ${
                toast.type === "success"
                  ? "bg-green-50 border-green-200 text-green-800 dark:bg-green-900/30 dark:border-green-800 dark:text-green-400"
                  : toast.type === "error"
                  ? "bg-red-50 border-red-200 text-red-800 dark:bg-red-900/30 dark:border-red-800 dark:text-red-400"
                  : "bg-blue-50 border-blue-200 text-blue-800 dark:bg-blue-900/30 dark:border-blue-800 dark:text-blue-400"
              }
            `}
            onClick={() => removeToast(toast.id)}
          >
            <span className="text-lg">
              {toast.type === "success" ? "✅" : toast.type === "error" ? "❌" : "ℹ️"}
            </span>
            <span className="text-sm flex-1">{toast.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return context;
}
