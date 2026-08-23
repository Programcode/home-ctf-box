import type { InputHTMLAttributes } from 'react';

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> {
  /** Visible label rendered above the field. */
  label: string;
  /** Optional helper text shown below the field. */
  hint?: string;
  /** Validation message; switches the field into its error state. */
  error?: string;
  /** Must be provided so label/field wiring survives server rendering. */
  id: string;
}

/**
 * Labelled text input with hint and error wiring (`aria-describedby`,
 * `aria-invalid`). Server-component safe.
 */
export function Input({ label, hint, error, id, className, ...rest }: InputProps) {
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy =
    [error === undefined ? null : errorId, hint === undefined ? null : hintId]
      .filter((value): value is string => value !== null)
      .join(' ') || undefined;

  return (
    <div className={['or-field', className].filter(Boolean).join(' ')}>
      <label className="or-label" htmlFor={id}>
        {label}
      </label>
      <input
        id={id}
        className="or-input"
        aria-invalid={error === undefined ? undefined : true}
        aria-describedby={describedBy}
        {...rest}
      />
      {error === undefined ? null : (
        <p className="or-error" id={errorId} role="alert">
          {error}
        </p>
      )}
      {hint === undefined ? null : (
        <p className="or-hint" id={hintId}>
          {hint}
        </p>
      )}
    </div>
  );
}
