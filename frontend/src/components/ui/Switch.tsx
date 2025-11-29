import { forwardRef } from 'react';
import { Switch as HeadlessSwitch } from '@headlessui/react';
import { clsx } from 'clsx';

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

const Switch = forwardRef<HTMLButtonElement, SwitchProps>(
  ({ checked, onChange, label, description, disabled, size = 'md' }, ref) => {
    const sizes = {
      sm: {
        switch: 'h-5 w-9',
        dot: 'h-4 w-4',
        translate: 'translate-x-4',
      },
      md: {
        switch: 'h-6 w-11',
        dot: 'h-5 w-5',
        translate: 'translate-x-5',
      },
    };

    return (
      <HeadlessSwitch.Group as="div" className="flex items-center justify-between">
        {(label || description) && (
          <span className="flex flex-grow flex-col mr-4">
            {label && (
              <HeadlessSwitch.Label
                as="span"
                className="text-sm font-medium text-gray-900 dark:text-white"
                passive
              >
                {label}
              </HeadlessSwitch.Label>
            )}
            {description && (
              <HeadlessSwitch.Description
                as="span"
                className="text-sm text-gray-500 dark:text-gray-400"
              >
                {description}
              </HeadlessSwitch.Description>
            )}
          </span>
        )}
        <HeadlessSwitch
          ref={ref}
          checked={checked}
          onChange={onChange}
          disabled={disabled}
          className={clsx(
            checked ? 'bg-primary-600' : 'bg-gray-200 dark:bg-gray-700',
            'relative inline-flex flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
            disabled && 'opacity-50 cursor-not-allowed',
            sizes[size].switch
          )}
        >
          <span
            aria-hidden="true"
            className={clsx(
              checked ? sizes[size].translate : 'translate-x-0',
              'pointer-events-none inline-block transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
              sizes[size].dot
            )}
          />
        </HeadlessSwitch>
      </HeadlessSwitch.Group>
    );
  }
);

Switch.displayName = 'Switch';

export default Switch;
