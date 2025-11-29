import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  UserCircleIcon, 
  LinkIcon, 
  BellIcon,
  MoonIcon,
  SunIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { brokerApi } from '@/services';
import { useAuthStore } from '@/stores/auth-store';
import { useThemeStore } from '@/stores/theme-store';
import { Card, Button, Badge, Spinner, Input, Alert, Switch } from '@/components/ui';

export function SettingsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const isDarkMode = theme === 'dark';
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Notification settings state
  const [notifications, setNotifications] = useState({
    tradeAlerts: true,
    ruleTriggers: true,
    engineStatus: false,
  });

  // Broker status query
  const { data: brokerStatus, isLoading: brokerLoading } = useQuery({
    queryKey: ['broker-status'],
    queryFn: () => brokerApi.getStatus('kite'),
  });

  // Broker account query
  const { data: brokerAccountsData } = useQuery({
    queryKey: ['broker-accounts'],
    queryFn: brokerApi.getAccounts,
  });

  const brokerAccounts = brokerAccountsData?.accounts ?? [];

  // Connect broker mutation
  const connectMutation = useMutation({
    mutationFn: (data: { broker_type: string; api_key: string; api_secret: string }) => 
      brokerApi.connect(data),
    onSuccess: (data) => {
      // Redirect to OAuth URL
      window.location.href = data.auth_url;
    },
    onError: (err: Error) => setError(err.message),
  });

  // Disconnect broker mutation
  const disconnectMutation = useMutation({
    mutationFn: (brokerType: string) => brokerApi.disconnect(brokerType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['broker-status'] });
      queryClient.invalidateQueries({ queryKey: ['broker-accounts'] });
      setSuccess('Broker disconnected successfully');
    },
    onError: (err: Error) => setError(err.message),
  });

  // Profile update
  const [profileForm, setProfileForm] = useState({
    name: user?.name ?? '',
    email: user?.email ?? '',
  });

  // Broker connection form
  const [apiKeyForm, setApiKeyForm] = useState({
    apiKey: '',
    apiSecret: '',
  });

  const handleConnectBroker = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKeyForm.apiKey || !apiKeyForm.apiSecret) {
      setError('API Key and Secret are required');
      return;
    }
    connectMutation.mutate({
      broker_type: 'kite',
      api_key: apiKeyForm.apiKey,
      api_secret: apiKeyForm.apiSecret,
    });
  };

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage your account and broker connections
        </p>
      </div>

      {error && (
        <Alert variant="error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert variant="success" onDismiss={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Profile Section */}
      <Card>
        <div className="flex items-center gap-4 pb-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30">
            <UserCircleIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Profile
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Your personal information
            </p>
          </div>
        </div>

        <div className="pt-6 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Input
              label="Name"
              value={profileForm.name}
              onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
              placeholder="Your name"
            />
            <Input
              label="Email"
              type="email"
              value={profileForm.email}
              onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
              placeholder="you@example.com"
              disabled
            />
          </div>

          <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button disabled>Update Profile</Button>
          </div>
        </div>
      </Card>

      {/* Broker Connection Section */}
      <Card>
        <div className="flex items-center gap-4 pb-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30">
            <LinkIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Broker Connection
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Connect your Zerodha Kite account
            </p>
          </div>
          {brokerStatus && (
            <Badge 
              variant={brokerStatus.connected ? 'success' : 'danger'}
              dot
            >
              {brokerStatus.connected ? 'Connected' : 'Disconnected'}
            </Badge>
          )}
        </div>

        <div className="pt-6">
          {brokerLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : brokerStatus?.connected ? (
          <div className="space-y-6">
            {/* Connected account info */}
            {brokerAccounts.length > 0 && (
              <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Broker</span>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {brokerAccounts[0].broker_type}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">API Key</span>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {brokerAccounts[0].api_key_masked}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Status</span>
                    <p className="font-medium text-success-600 dark:text-success-400">
                      Active
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Token Expires</span>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {brokerAccounts[0].token_expires_at 
                        ? new Date(brokerAccounts[0].token_expires_at).toLocaleString()
                        : 'N/A'
                      }
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex gap-3">
              <Button
                variant="secondary"
                onClick={() => queryClient.invalidateQueries({ queryKey: ['broker-status'] })}
                leftIcon={<ArrowPathIcon className="h-5 w-5" />}
              >
                Refresh Status
              </Button>
              <Button
                variant="danger"
                onClick={() => disconnectMutation.mutate('kite')}
                isLoading={disconnectMutation.isPending}
              >
                Disconnect Broker
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleConnectBroker} className="space-y-6">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              To connect your Zerodha Kite account, enter your API credentials below. 
              You can get these from the{' '}
              <a 
                href="https://developers.kite.trade/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-primary-600 hover:underline font-medium"
              >
                Kite Connect Developer Console
              </a>.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Input
                label="API Key"
                value={apiKeyForm.apiKey}
                onChange={(e) => setApiKeyForm({ ...apiKeyForm, apiKey: e.target.value })}
                placeholder="Your Kite API Key"
                required
              />
              <Input
                label="API Secret"
                type="password"
                value={apiKeyForm.apiSecret}
                onChange={(e) => setApiKeyForm({ ...apiKeyForm, apiSecret: e.target.value })}
                placeholder="Your Kite API Secret"
                required
              />
            </div>

            <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
              <Button
                type="submit"
                isLoading={connectMutation.isPending}
                leftIcon={<LinkIcon className="h-5 w-5" />}
              >
                Connect to Zerodha
              </Button>
            </div>
          </form>
        )}
        </div>
      </Card>

      {/* Appearance Section */}
      <Card>
        <div className="flex items-center gap-4 pb-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30">
            {isDarkMode ? (
              <MoonIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
            ) : (
              <SunIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
            )}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Appearance
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Customize how the app looks
            </p>
          </div>
        </div>

        <div className="pt-6">
          <div className="flex items-center justify-between py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Dark Mode</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Use dark theme for the interface
              </p>
            </div>
            <Switch
              checked={isDarkMode}
              onChange={toggleTheme}
            />
          </div>
        </div>
      </Card>

      {/* Notifications Section */}
      <Card>
        <div className="flex items-center gap-4 pb-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary-100 dark:bg-primary-900/30">
            <BellIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Notifications
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Configure alert preferences
            </p>
          </div>
        </div>

        <div className="pt-6 space-y-3">
          <div className="flex items-center justify-between py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Trade Alerts</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Get notified when trades are executed
              </p>
            </div>
            <Switch 
              checked={notifications.tradeAlerts}
              onChange={(checked) => setNotifications({ ...notifications, tradeAlerts: checked })}
            />
          </div>

          <div className="flex items-center justify-between py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Rule Triggers</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Get notified when rules are triggered
              </p>
            </div>
            <Switch 
              checked={notifications.ruleTriggers}
              onChange={(checked) => setNotifications({ ...notifications, ruleTriggers: checked })}
            />
          </div>

          <div className="flex items-center justify-between py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900 dark:text-white">Engine Status</p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Get notified about engine start/stop
              </p>
            </div>
            <Switch 
              checked={notifications.engineStatus}
              onChange={(checked) => setNotifications({ ...notifications, engineStatus: checked })}
            />
          </div>
        </div>
      </Card>

      {/* Danger Zone */}
      <Card className="border-danger-300 dark:border-danger-800 bg-danger-50/50 dark:bg-danger-900/10">
        <div className="flex items-center gap-4 pb-6 border-b border-danger-200 dark:border-danger-800">
          <div className="flex items-center justify-center w-12 h-12 rounded-full bg-danger-100 dark:bg-danger-900/30">
            <svg className="h-6 w-6 text-danger-600 dark:text-danger-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-danger-700 dark:text-danger-400">
              Danger Zone
            </h2>
            <p className="text-sm text-danger-600/70 dark:text-danger-400/70">
              Irreversible actions
            </p>
          </div>
        </div>
        
        <div className="pt-6">
          <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
            Deleting your account will remove all your data including trading rules and history.
            This action cannot be undone.
          </p>
          <Button variant="danger" disabled>
            Delete Account
          </Button>
        </div>
      </Card>
    </div>
  );
}
