import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Disclosure, Menu, Transition } from '@headlessui/react';
import {
  Bars3Icon,
  XMarkIcon,
  ChartBarIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  UserCircleIcon,
  SunIcon,
  MoonIcon,
  BoltIcon,
  DocumentTextIcon,
  ClipboardDocumentListIcon,
  CurrencyDollarIcon,
} from '@heroicons/react/24/outline';
import { clsx } from 'clsx';
import { useAuthStore, useThemeStore } from '@/stores';
import { APP_NAME, ROUTES } from '@/config';
import Badge from '../ui/Badge';
import type { EngineStatus } from '@/types';

interface NavbarProps {
  engineStatus?: EngineStatus;
}

const navigation = [
  { name: 'Dashboard', href: ROUTES.DASHBOARD, icon: ChartBarIcon },
  { name: 'Positions', href: ROUTES.POSITIONS, icon: CurrencyDollarIcon },
  { name: 'Rules', href: ROUTES.RULES, icon: DocumentTextIcon },
  { name: 'Trades', href: ROUTES.TRADES, icon: ClipboardDocumentListIcon },
];

export default function Navbar({ engineStatus }: NavbarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();

  const handleLogout = () => {
    logout();
    navigate(ROUTES.LOGIN);
  };

  return (
    <Disclosure as="nav" className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      {({ open }) => (
        <>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                {/* Logo */}
                <Link to={ROUTES.DASHBOARD} className="flex-shrink-0 flex items-center">
                  <BoltIcon className="h-8 w-8 text-primary-600" />
                  <span className="ml-2 text-xl font-bold text-gray-900 dark:text-white">
                    {APP_NAME}
                  </span>
                </Link>

                {/* Desktop Navigation */}
                <div className="hidden sm:ml-8 sm:flex sm:space-x-4">
                  {navigation.map((item) => {
                    const isActive = location.pathname.startsWith(item.href);
                    return (
                      <Link
                        key={item.name}
                        to={item.href}
                        className={clsx(
                          'inline-flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                          isActive
                            ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                            : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                        )}
                      >
                        <item.icon className="h-5 w-5 mr-2" />
                        {item.name}
                      </Link>
                    );
                  })}
                </div>
              </div>

              <div className="flex items-center space-x-4">
                {/* Engine Status */}
                {engineStatus && (
                  <div className="hidden md:flex items-center">
                    <Badge
                      variant={engineStatus.running ? 'success' : 'gray'}
                      dot
                    >
                      Engine: {engineStatus.running ? 'Running' : 'Stopped'}
                    </Badge>
                    {engineStatus.running && (
                      <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
                        {engineStatus.active_trades} trades
                      </span>
                    )}
                  </div>
                )}

                {/* Theme Toggle */}
                <button
                  onClick={toggleTheme}
                  className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                >
                  {theme === 'dark' ? (
                    <SunIcon className="h-5 w-5" />
                  ) : (
                    <MoonIcon className="h-5 w-5" />
                  )}
                </button>

                {/* User Menu */}
                <Menu as="div" className="relative">
                  <Menu.Button className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                    <UserCircleIcon className="h-6 w-6 text-gray-500" />
                    <span className="hidden md:block text-sm font-medium text-gray-700 dark:text-gray-200">
                      {user?.name}
                    </span>
                  </Menu.Button>

                  <Transition
                    enter="transition ease-out duration-100"
                    enterFrom="transform opacity-0 scale-95"
                    enterTo="transform opacity-100 scale-100"
                    leave="transition ease-in duration-75"
                    leaveFrom="transform opacity-100 scale-100"
                    leaveTo="transform opacity-0 scale-95"
                  >
                    <Menu.Items className="absolute right-0 mt-2 w-48 origin-top-right rounded-lg bg-white dark:bg-gray-800 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none border border-gray-200 dark:border-gray-700">
                      <div className="py-1">
                        <Menu.Item>
                          {({ active }) => (
                            <Link
                              to={ROUTES.SETTINGS}
                              className={clsx(
                                'flex items-center px-4 py-2 text-sm',
                                active
                                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                                  : 'text-gray-700 dark:text-gray-200'
                              )}
                            >
                              <Cog6ToothIcon className="h-5 w-5 mr-2" />
                              Settings
                            </Link>
                          )}
                        </Menu.Item>
                        <Menu.Item>
                          {({ active }) => (
                            <button
                              onClick={handleLogout}
                              className={clsx(
                                'flex w-full items-center px-4 py-2 text-sm',
                                active
                                  ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
                                  : 'text-gray-700 dark:text-gray-200'
                              )}
                            >
                              <ArrowRightOnRectangleIcon className="h-5 w-5 mr-2" />
                              Sign out
                            </button>
                          )}
                        </Menu.Item>
                      </div>
                    </Menu.Items>
                  </Transition>
                </Menu>

                {/* Mobile menu button */}
                <div className="flex items-center sm:hidden">
                  <Disclosure.Button className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700">
                    {open ? (
                      <XMarkIcon className="h-6 w-6" />
                    ) : (
                      <Bars3Icon className="h-6 w-6" />
                    )}
                  </Disclosure.Button>
                </div>
              </div>
            </div>
          </div>

          {/* Mobile Navigation */}
          <Disclosure.Panel className="sm:hidden">
            <div className="px-2 pt-2 pb-3 space-y-1">
              {navigation.map((item) => {
                const isActive = location.pathname.startsWith(item.href);
                return (
                  <Disclosure.Button
                    key={item.name}
                    as={Link}
                    to={item.href}
                    className={clsx(
                      'flex items-center px-3 py-2 rounded-lg text-base font-medium',
                      isActive
                        ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                        : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    )}
                  >
                    <item.icon className="h-5 w-5 mr-3" />
                    {item.name}
                  </Disclosure.Button>
                );
              })}
            </div>
          </Disclosure.Panel>
        </>
      )}
    </Disclosure>
  );
}
