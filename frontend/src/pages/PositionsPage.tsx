import { useQuery } from '@tanstack/react-query';
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/react/24/outline';
import { tradingApi } from '@/services';
import type { Position } from '@/types';
import { Card, Badge, Spinner, Table } from '@/components/ui';

export function PositionsPage() {
  const { data: positions, isLoading, error } = useQuery({
    queryKey: ['positions'],
    queryFn: tradingApi.getPositions,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const totalPnL = positions?.reduce((sum, p) => sum + p.pnl, 0) ?? 0;
  const openPositions = positions?.length ?? 0;

  const columns = [
    {
      key: 'symbol',
      header: 'Symbol',
      render: (position: Position) => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-white">
            {position.symbol}
          </span>
          {position.quantity > 0 ? (
            <ArrowTrendingUpIcon className="h-4 w-4 text-success-500" />
          ) : (
            <ArrowTrendingDownIcon className="h-4 w-4 text-danger-500" />
          )}
        </div>
      ),
    },
    {
      key: 'quantity',
      header: 'Quantity',
      render: (position: Position) => (
        <span className={position.quantity > 0 ? 'text-success-600' : 'text-danger-600'}>
          {position.quantity > 0 ? '+' : ''}{position.quantity}
        </span>
      ),
    },
    {
      key: 'average_price',
      header: 'Avg Price',
      render: (position: Position) => formatCurrency(position.average_price),
    },
    {
      key: 'current_price',
      header: 'Current Price',
      render: (position: Position) => formatCurrency(position.current_price),
    },
    {
      key: 'pnl',
      header: 'P&L',
      render: (position: Position) => (
        <div className="text-right">
          <div className={position.pnl >= 0 ? 'text-success-600 font-medium' : 'text-danger-600 font-medium'}>
            {formatCurrency(position.pnl)}
          </div>
          <div className={`text-xs ${position.pnl_percent >= 0 ? 'text-success-500' : 'text-danger-500'}`}>
            {formatPercent(position.pnl_percent)}
          </div>
        </div>
      ),
    },
    {
      key: 'product',
      header: 'Product',
      render: (position: Position) => (
        <Badge variant={position.product === 'MIS' ? 'primary' : 'gray'}>
          {position.product}
        </Badge>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">
          Unable to fetch positions. Make sure your broker is connected.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Open Positions
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Real-time view of your active positions
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="bg-gradient-to-br from-primary-50 to-primary-100 dark:from-primary-900/20 dark:to-primary-800/20">
          <div className="text-sm text-primary-600 dark:text-primary-400 mb-1">
            Open Positions
          </div>
          <div className="text-2xl font-bold text-primary-700 dark:text-primary-300">
            {openPositions}
          </div>
        </Card>

        <Card className={`bg-gradient-to-br ${totalPnL >= 0 
          ? 'from-success-50 to-success-100 dark:from-success-900/20 dark:to-success-800/20'
          : 'from-danger-50 to-danger-100 dark:from-danger-900/20 dark:to-danger-800/20'
        }`}>
          <div className={`text-sm mb-1 ${totalPnL >= 0 
            ? 'text-success-600 dark:text-success-400' 
            : 'text-danger-600 dark:text-danger-400'
          }`}>
            Total P&L
          </div>
          <div className={`text-2xl font-bold ${totalPnL >= 0 
            ? 'text-success-700 dark:text-success-300' 
            : 'text-danger-700 dark:text-danger-300'
          }`}>
            {formatCurrency(totalPnL)}
          </div>
        </Card>

        <Card className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800/50 dark:to-gray-700/50">
          <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
            Market Status
          </div>
          <div className="text-2xl font-bold text-gray-700 dark:text-gray-300">
            <Badge variant="success" dot>
              Open
            </Badge>
          </div>
        </Card>
      </div>

      {/* Positions Table */}
      {positions && positions.length > 0 ? (
        <Card className="overflow-hidden">
          <Table
            data={positions}
            columns={columns}
            keyExtractor={(position) => position.symbol}
          />
        </Card>
      ) : (
        <Card className="text-center py-12">
          <ArrowTrendingUpIcon className="h-12 w-12 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500 dark:text-gray-400">
            No open positions at the moment.
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">
            Positions will appear here when your trading rules execute.
          </p>
        </Card>
      )}
    </div>
  );
}
