import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XCircleIcon,
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';

type AlertVariant = 'info' | 'success' | 'warning' | 'error';

export interface AlertProps {
  variant?: AlertVariant;
  title?: string;
  children: React.ReactNode;
  className?: string;
  onDismiss?: () => void;
}

const variants: Record<AlertVariant, { bg: string; text: string; icon: React.ComponentType<{ className?: string }> }> = {
  info: {
    bg: 'bg-primary-50 dark:bg-primary-900/20',
    text: 'text-primary-700 dark:text-primary-400',
    icon: InformationCircleIcon,
  },
  success: {
    bg: 'bg-success-50 dark:bg-success-900/20',
    text: 'text-success-600 dark:text-success-400',
    icon: CheckCircleIcon,
  },
  warning: {
    bg: 'bg-warning-50 dark:bg-warning-900/20',
    text: 'text-warning-600 dark:text-warning-400',
    icon: ExclamationTriangleIcon,
  },
  error: {
    bg: 'bg-danger-50 dark:bg-danger-900/20',
    text: 'text-danger-600 dark:text-danger-400',
    icon: XCircleIcon,
  },
};

export default function Alert({ variant = 'info', title, children, className, onDismiss }: AlertProps) {
  const { bg, text, icon: Icon } = variants[variant];

  return (
    <div className={clsx('rounded-lg p-4', bg, className)}>
      <div className="flex">
        <div className="flex-shrink-0">
          <Icon className={clsx('h-5 w-5', text)} />
        </div>
        <div className="ml-3 flex-1">
          {title && <h3 className={clsx('text-sm font-medium', text)}>{title}</h3>}
          <div className={clsx('text-sm', text, title && 'mt-1')}>{children}</div>
        </div>
        {onDismiss && (
          <button
            type="button"
            onClick={onDismiss}
            className={clsx('ml-3 flex-shrink-0 rounded-md p-1.5 hover:bg-black/5 dark:hover:bg-white/5', text)}
          >
            <span className="sr-only">Dismiss</span>
            <XCircleIcon className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  );
}
