import { cn } from '@/lib/utils';

export function Button({ className, variant = 'default', size = 'default', ...props }) {
  const variants = {
    default: 'bg-primary text-primary-foreground hover:opacity-90',
    outline: 'border border-border bg-card hover:bg-muted',
    ghost: 'hover:bg-muted',
    destructive: 'bg-destructive text-destructive-foreground hover:opacity-90',
  };
  const sizes = {
    default: 'h-10 px-4 py-2',
    sm: 'h-8 px-3 text-xs',
    lg: 'h-11 px-6',
    icon: 'h-9 w-9',
  };
  return (
    <button
      className={cn('inline-flex items-center justify-center rounded-xl text-sm font-medium transition disabled:opacity-50 disabled:pointer-events-none', variants[variant], sizes[size], className)}
      {...props}
    />
  );
}
