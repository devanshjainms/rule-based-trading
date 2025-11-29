import { clsx } from 'clsx';

type BadgeVariant = 'success' | 'danger' | 'warning' | 'primary' | 'gray';

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
  dot?: boolean;
}

const variants: Record<BadgeVariant, string> = {
  success: 'bg-success-50 text-success-600 dark:bg-success-500/20 dark:text-success-500',
  danger: 'bg-danger-50 text-danger-600 dark:bg-danger-500/20 dark:text-danger-500',
  warning: 'bg-warning-50 text-warning-600 dark:bg-warning-500/20 dark:text-warning-500',
  primary: 'bg-primary-50 text-primary-600 dark:bg-primary-500/20 dark:text-primary-500',
  gray: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
};

const dotColors: Record<BadgeVariant, string> = {
  success: 'bg-success-500',
  danger: 'bg-danger-500',
  warning: 'bg-warning-500',
  primary: 'bg-primary-500',
  gray: 'bg-gray-500',
};

export default function Badge({ children, variant = 'gray', className, dot }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
        variants[variant],
        className
      )}
    >
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full mr-1.5', dotColors[variant])} />}
      {children}
    </span>
  );
}
