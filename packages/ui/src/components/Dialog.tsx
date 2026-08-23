'use client';

import { useEffect, useId, useRef } from 'react';
import type { ReactNode } from 'react';

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
}

/**
 * Modal dialog built on the native `<dialog>` element, so focus trapping,
 * Escape handling and inert background content come from the platform.
 * Client component (controls open state).
 */
export function Dialog({ open, onClose, title, children }: DialogProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog === null) {
      return;
    }
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className="or-dialog"
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClose={() => {
        if (open) {
          onClose();
        }
      }}
    >
      <div className="or-dialog__header">
        <h2 className="or-dialog__title" id={titleId}>
          {title}
        </h2>
        <button type="button" className="or-dialog__close" aria-label="Close" onClick={onClose}>
          ×
        </button>
      </div>
      <div className="or-dialog__body">{children}</div>
    </dialog>
  );
}
