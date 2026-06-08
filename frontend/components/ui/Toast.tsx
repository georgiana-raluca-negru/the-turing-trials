"use client";

import {
  createContext,
  useCallback,
  useContext,
  useState,
} from "react";

export type ToastType = "success" | "error" | "info" | "warning";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>({ showToast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

const STYLES: Record<ToastType, string> = {
  success: "border-emerald-500/60 text-emerald-300 bg-emerald-950/90",
  error:   "border-red-500/60 text-red-300 bg-red-950/90",
  info:    "border-cyan-500/60 text-cyan-300 bg-slate-950/95",
  warning: "border-yellow-500/60 text-yellow-300 bg-yellow-950/90",
};

const PREFIX: Record<ToastType, string> = {
  success: "OK",
  error:   "ERR",
  info:    "SYS",
  warning: "WARN",
};

let _id = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = ++_id;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const dismiss = (id: number) =>
    setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}

      {/* Toast portal — fixed to viewport bottom-right */}
      <div
        aria-live="polite"
        className="fixed bottom-6 right-4 sm:right-6 z-[9999] flex flex-col gap-2 w-[calc(100vw-2rem)] sm:w-96 pointer-events-none"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`flex items-start gap-3 p-3 rounded border backdrop-blur-md font-mono text-xs shadow-2xl pointer-events-auto toast-in ${STYLES[toast.type]}`}
          >
            <span className="font-black shrink-0 border border-current rounded px-1 py-0.5 text-[10px] tracking-widest">
              {PREFIX[toast.type]}
            </span>
            <span className="flex-1 leading-relaxed break-words">{toast.message}</span>
            <button
              onClick={() => dismiss(toast.id)}
              aria-label="Dismiss"
              className="shrink-0 opacity-40 hover:opacity-100 transition-opacity text-base leading-none -mt-0.5 cursor-pointer"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
