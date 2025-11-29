import { Outlet, Link } from 'react-router-dom';
import { BoltIcon } from '@heroicons/react/24/outline';
import { APP_NAME } from '@/config';

export default function AuthLayout() {
  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-gray-50 dark:bg-gray-900">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link to="/" className="flex justify-center items-center">
          <BoltIcon className="h-12 w-12 text-primary-600" />
          <span className="ml-3 text-3xl font-bold text-gray-900 dark:text-white">
            {APP_NAME}
          </span>
        </Link>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white dark:bg-gray-800 py-8 px-4 shadow-xl sm:rounded-xl sm:px-10 border border-gray-200 dark:border-gray-700">
          <Outlet />
        </div>
      </div>

      <p className="mt-8 text-center text-sm text-gray-500 dark:text-gray-400">
        Rule-based automated trading system
      </p>
    </div>
  );
}
