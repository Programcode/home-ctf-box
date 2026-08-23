import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

function buttonClasses(variant: ButtonVariant, size: ButtonSize, extra?: string): string {
  const parts = ['or-btn', `or-btn--${variant}`, `or-btn--${size}`];
  if (extra !== undefined && extra.length > 0) {
    parts.push(extra);
  }
  return parts.join(' ');
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

/** Action button. Renders `<button>`; server-component safe. */
export function Button({
  variant = 'primary',
  size = 'md',
  className,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      className={buttonClasses(variant, size, className)}
      data-variant={variant}
      {...rest}
    />
  );
}

export interface ButtonLinkProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

/** Anchor styled as a button, for navigation CTAs. Server-component safe. */
export function ButtonLink({
  variant = 'primary',
  size = 'md',
  className,
  ...rest
}: ButtonLinkProps) {
  return <a className={buttonClasses(variant, size, className)} data-variant={variant} {...rest} />;
}
