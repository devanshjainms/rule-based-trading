import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  ChartBarIcon,
  CurrencyDollarIcon,
  DocumentTextIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  PlayIcon,
  StopIcon,
  LinkIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { Card, CardBody, CardHeader, Button, Badge, Alert } from '@/components/ui';
import { tradingApi, rulesApi, brokerApi } from '@/services';
import { ROUTES, POSITIONS_POLL_INTERVAL, ENGINE_STATUS_POLL_INTERVAL } from '@/config';
import { clsx } from 'clsx';
import type { Position, Rule } from '@/types';

export default function DashboardPage() {
  const queryClient = useQueryClient();

  // Fetch data
  const { data: engineStatus } = useQuery({
    queryKey: ['engineStatus'],
    queryFn: tradingApi.getEngineStatus,
    refetchInterval: ENGINE_STATUS_POLL_INTERVAL,
  });

  const { data: positions = [], isError: positionsError } = useQuery({
    queryKey: ['positions'],
    queryFn: tradingApi.getPositions,
    refetchInterval: POSITIONS_POLL_INTERVAL,
    retry: false,
  });

  const { data: rules = [] } = useQuery({
    queryKey: ['rules'],
    queryFn: rulesApi.getAll,
  });

  const { data: brokerData } = useQuery({
    queryKey: ['brokerAccounts'],
    queryFn: brokerApi.getAccounts,
  });

  const brokerConnected = brokerData?.accounts?.some((a) => a.is_connected) ?? false;

  // Engine controls
  const startEngine = useMutation({
    mutationFn: tradingApi.startEngine,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['engineStatus'] }),
  });

  const stopEngine = useMutation({
    mutationFn: tradingApi.stopEngine,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['engineStatus'] }),
  });

  // Calculate stats
  const totalPnL = positions.reduce((sum, p) => sum + (p.pnl || 0), 0);
  const activeRules = rules.filter((r) => r.is_active).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Overview of your trading activity
          </p>
        </div>

        <div className="flex items-center gap-3">
          {engineStatus?.running ? (
            <Button
              variant="danger"
              onClick={() => stopEngine.mutate()}
              isLoading={stopEngine.isPending}
              leftIcon={<StopIcon className="h-4 w-4" />}
            >
              Stop Engine
            </Button>
          ) : (
            <Button
              variant="success"
              onClick={() => startEngine.mutate()}
              isLoading={startEngine.isPending}
              disabled={!brokerConnected}
              leftIcon={<PlayIcon className="h-4 w-4" />}
            >
              Start Engine
            </Button>
          )}
        </div>
      </div>

      {/* Broker Warning */}
      {!brokerConnected && (
        <Alert variant="warning" title="Broker Not Connected">
          <p>Connect your broker to enable trading features.</p>
          <Link to={ROUTES.SETTINGS} className="mt-2 inline-flex items-center text-sm font-medium">
            <LinkIcon className="h-4 w-4 mr-1" />
            Connect Broker
          </Link>
        </Alert>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Engine Status"
          value={engineStatus?.running ? 'Running' : 'Stopped'}
          icon={ChartBarIcon}
          variant={engineStatus?.running ? 'success' : 'gray'}
          subtitle={
            engineStatus?.running
              ? `${engineStatus.active_trades} active trades`
              : 'Click Start to begin'
          }
        />
        <StatCard
          title="Open Positions"
          value={positions.length.toString()}
          icon={CurrencyDollarIcon}
          variant="primary"
          subtitle={positionsError ? 'Connect broker to view' : 'Active positions'}
        />
        <StatCard
          title="Total P&L"
          value={formatCurrency(totalPnL)}
          icon={totalPnL >= 0 ? ArrowTrendingUpIcon : ArrowTrendingDownIcon}
          variant={totalPnL >= 0 ? 'success' : 'danger'}
          subtitle="Unrealized profit/loss"
        />
        <StatCard
          title="Active Rules"
          value={`${activeRules}/${rules.length}`}
          icon={DocumentTextIcon}
          variant="primary"
          subtitle="Trading rules enabled"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Positions Card */}
        <Card>
          <CardHeader
            action={
              <Link to={ROUTES.POSITIONS}>
                <Button variant="ghost" size="sm">
                  View All
                </Button>
              </Link>
            }
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Open Positions
            </h3>
          </CardHeader>
          <CardBody className="p-0">
            {positionsError ? (
              <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                <ExclamationTriangleIcon className="h-8 w-8 mx-auto mb-2" />
                <p>Connect your broker to view positions</p>
              </div>
            ) : positions.length === 0 ? (
              <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                No open positions
              </div>
            ) : (
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {positions.slice(0, 5).map((position) => (
                  <PositionRow key={position.symbol} position={position} />
                ))}
              </div>
            )}
          </CardBody>
        </Card>

        {/* Rules Card */}
        <Card>
          <CardHeader
            action={
              <Link to={ROUTES.RULES}>
                <Button variant="ghost" size="sm">
                  View All
                </Button>
              </Link>
            }
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Trading Rules
            </h3>
          </CardHeader>
          <CardBody className="p-0">
            {rules.length === 0 ? (
              <div className="p-6 text-center text-gray-500 dark:text-gray-400">
                <DocumentTextIcon className="h-8 w-8 mx-auto mb-2" />
                <p>No rules configured</p>
                <Link to={ROUTES.RULES_CREATE}>
                  <Button variant="primary" size="sm" className="mt-3">
                    Create Rule
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {rules.slice(0, 5).map((rule) => (
                  <RuleRow key={rule.id} rule={rule} />
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

// Helper Components
interface StatCardProps {
  title: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  variant: 'success' | 'danger' | 'primary' | 'gray';
  subtitle: string;
}

function StatCard({ title, value, icon: Icon, variant, subtitle }: StatCardProps) {
  const colors = {
    success: 'text-success-600 bg-success-50 dark:bg-success-500/20',
    danger: 'text-danger-600 bg-danger-50 dark:bg-danger-500/20',
    primary: 'text-primary-600 bg-primary-50 dark:bg-primary-500/20',
    gray: 'text-gray-600 bg-gray-100 dark:bg-gray-700',
  };

  return (
    <Card>
      <CardBody>
        <div className="flex items-center">
          <div className={clsx('p-3 rounded-lg', colors[variant])}>
            <Icon className="h-6 w-6" />
          </div>
          <div className="ml-4">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{subtitle}</p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

function PositionRow({ position }: { position: Position }) {
  const isProfitable = position.pnl >= 0;

  return (
    <div className="px-6 py-4 flex items-center justify-between">
      <div>
        <p className="font-medium text-gray-900 dark:text-white">{position.symbol}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {position.quantity} @ {formatCurrency(position.average_price)}
        </p>
      </div>
      <div className="text-right">
        <p
          className={clsx(
            'font-medium',
            isProfitable ? 'text-success-600' : 'text-danger-600'
          )}
        >
          {isProfitable ? '+' : ''}
          {formatCurrency(position.pnl)}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {position.pnl_percent >= 0 ? '+' : ''}
          {position.pnl_percent.toFixed(2)}%
        </p>
      </div>
    </div>
  );
}

function RuleRow({ rule }: { rule: Rule }) {
  return (
    <div className="px-6 py-4 flex items-center justify-between">
      <div>
        <p className="font-medium text-gray-900 dark:text-white">{rule.name}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">{rule.symbol}</p>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant={rule.is_active ? 'success' : 'gray'}>
          {rule.is_active ? 'Active' : 'Disabled'}
        </Badge>
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {rule.trigger_count} triggers
        </span>
      </div>
    </div>
  );
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(value);
}
