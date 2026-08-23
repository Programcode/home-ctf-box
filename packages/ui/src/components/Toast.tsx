'use client';

import { createContext, useCallback, useContext, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';

export type ToastVariant = 'info' | 'success' | 'error' | 'warning';

export interface Toast {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  push: (toast: { title: string; description?: string; variant?: ToastVariant }) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const AUTO_DISMISS_MS = 6000;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const push = useCallback<ToastContextValue['push']>(({ title, description, variant }) => {
    const id = nextId.current;
    nextId.current += 1;
    const toast: Toast = { id, title, description, variant: variant ?? 'info' };
    setToasts((current) => [...current, toast]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((candidate) => candidate.id !== id));
    }, AUTO_DISMISS_MS);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite">
        <ul className="or-toasts">
          {toasts.map((toast) => (
            <li key={toast.id} className={`or-toast or-toast--${toast.variant}`}>
              <div>
                <strong>{toast.title}</strong>
                {toast.description === undefined ? null : <div>{toast.description}</div>}
              </div>
              <button
                type="button"
                className="or-dialog__close"
                aria-label={`Dismiss notification: ${toast.title}`}
                onClick={() => dismiss(toast.id)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const value = useContext(ToastContext);
  if (value === undefined) {
    throw new Error('useToast must be used inside ToastProvider');
  }
  return value;
}
