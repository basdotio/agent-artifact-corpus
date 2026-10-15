'use client';
import * as React from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantToClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-[color:var(--color-primary)] text-white hover:brightness-95 focus-visible:ring-[color:var(--color-primary)]',
  secondary:
    'bg-[color:var(--color-accent)] text-white hover:brightness-95 focus-visible:ring-[color:var(--color-accent)]',
  ghost:
    'bg-transparent text-[color:var(--color-foreground)] hover:bg-[color:var(--color-muted)] focus-visible:ring-[color:var(--color-foreground)]',
};

const sizeToClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs rounded-[var(--radius-sm)]',
  md: 'h-10 px-4 text-sm rounded-[var(--radius-md)]',
  lg: 'h-12 px-5 text-base rounded-[var(--radius-lg)]',
};

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  ...props
}: ButtonProps) {
  const base =
    'inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
  const classes = `${base} ${variantToClasses[variant]} ${sizeToClasses[size]} ${className}`;
  return <button className={classes} {...props} />;
}
