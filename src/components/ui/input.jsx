import { cn } from '@/lib/utils';

export function Input({ className, ...props }) {
  return <input className={cn('w-full h-10 rounded-xl border border-input bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring', className)} {...props} />;
}
