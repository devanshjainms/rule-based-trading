import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDownTrayIcon, FunnelIcon } from '@heroicons/react/24/outline';
import { tradingApi } from '@/services';
import type { Trade } from '@/types';
import { Card, Badge, Spinner, Button, Input, Table } from '@/components/ui';

type FilterType = 'all' | 'BUY' | 'SELL';

export function TradesPage() {
  const [filter, setFilter] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const { data: trades, isLoading, error } = useQuery({
    queryKey: ['trades'],
    queryFn: () => tradingApi.getTrades(),
  });

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatDateTime = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredTrades = trades?.filter((trade) => {
    const matchesFilter = filter === 'all' || trade.side === filter;
    const matchesSearch = trade.symbol.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  }) ?? [];

  const totalBuys = trades?.filter(t => t.side === 'BUY').length ?? 0;
  const totalSells = trades?.filter(t => t.side === 'SELL').length ?? 0;
  const realizedPnL = trades?.reduce((sum, t) => sum + (t.pnl ?? 0), 0) ?? 0;

  const columns = [
    {
      key: 'executed_at',
      header: 'Date & Time',
      render: (trade: Trade) => (
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {formatDateTime(trade.executed_at)}
        </span>
      ),
    },
    {
      key: 'symbol',
      header: 'Symbol',
      render: (trade: Trade) => (
        <div>
          <span className="font-medium text-gray-900 dark:text-white">
            {trade.symbol}
          </span>
          <span className="ml-2 text-xs text-gray-500">{trade.exchange}</span>
        </div>
      ),
    },
    {
      key: 'side',
      header: 'Side',
      render: (trade: Trade) => (
        <Badge variant={trade.side === 'BUY' ? 'success' : 'danger'}>
          {trade.side}
        </Badge>
      ),
    },
    {
      key: 'quantity',
      header: 'Qty',
      render: (trade: Trade) => (
        <span className="font-medium text-gray-900 dark:text-white">
          {trade.quantity}
        </span>
      ),
    },
    {
      key: 'price',
      header: 'Price',
      render: (trade: Trade) => formatCurrency(trade.price),
    },
    {
      key: 'order_type',
      header: 'Type',
      render: (trade: Trade) => (
        <Badge variant="gray">{trade.order_type}</Badge>
      ),
    },
    {
      key: 'pnl',
      header: 'P&L',
      render: (trade: Trade) => (
        trade.pnl !== undefined ? (
          <span className={trade.pnl >= 0 ? 'text-success-600 font-medium' : 'text-danger-600 font-medium'}>
            {formatCurrency(trade.pnl)}
          </span>
        ) : (
          <span className="text-gray-400">-</span>
        )
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (trade: Trade) => (
        <Badge 
          variant={
            trade.status === 'COMPLETE' ? 'success' : 
            trade.status === 'REJECTED' ? 'danger' : 
            'warning'
          }
        >
          {trade.status}
        </Badge>
      ),
    },
  ];

  const exportToCsv = () => {
    if (!filteredTrades.length) return;
    
    const headers = ['Date', 'Symbol', 'Exchange', 'Side', 'Quantity', 'Price', 'Type', 'P&L', 'Status'];
    const rows = filteredTrades.map(t => [
      formatDateTime(t.executed_at),
      t.symbol,
      t.exchange,
      t.side,
      t.quantity,
      t.price,
      t.order_type,
      t.pnl ?? '',
      t.status,
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `trades-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

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
          Unable to fetch trade history. Please try again later.
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Trade History
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Complete record of all executed trades
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={exportToCsv}
          disabled={!filteredTrades.length}
          leftIcon={<ArrowDownTrayIcon className="h-5 w-5" />}
        >
          Export CSV
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <Card>
          <div className="text-sm text-gray-500 dark:text-gray-400 mb-1">Total Trades</div>
          <div className="text-2xl font-bold text-gray-900 dark:text-white">
            {trades?.length ?? 0}
          </div>
        </Card>
        <Card className="bg-success-50 dark:bg-success-900/20">
          <div className="text-sm text-success-600 dark:text-success-400 mb-1">Buy Orders</div>
          <div className="text-2xl font-bold text-success-700 dark:text-success-300">
            {totalBuys}
          </div>
        </Card>
        <Card className="bg-danger-50 dark:bg-danger-900/20">
          <div className="text-sm text-danger-600 dark:text-danger-400 mb-1">Sell Orders</div>
          <div className="text-2xl font-bold text-danger-700 dark:text-danger-300">
            {totalSells}
          </div>
        </Card>
        <Card className={realizedPnL >= 0 ? 'bg-success-50 dark:bg-success-900/20' : 'bg-danger-50 dark:bg-danger-900/20'}>
          <div className={`text-sm mb-1 ${realizedPnL >= 0 ? 'text-success-600 dark:text-success-400' : 'text-danger-600 dark:text-danger-400'}`}>
            Realized P&L
          </div>
          <div className={`text-2xl font-bold ${realizedPnL >= 0 ? 'text-success-700 dark:text-success-300' : 'text-danger-700 dark:text-danger-300'}`}>
            {formatCurrency(realizedPnL)}
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <Input
              placeholder="Search by symbol..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-5 w-5 text-gray-400" />
            <div className="flex gap-1">
              {(['all', 'BUY', 'SELL'] as FilterType[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                    filter === f
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                  }`}
                >
                  {f === 'all' ? 'All' : f}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Card>

      {/* Trades Table */}
      {filteredTrades.length > 0 ? (
        <Card className="overflow-hidden">
          <Table
            data={filteredTrades}
            columns={columns}
            keyExtractor={(trade) => trade.id}
          />
        </Card>
      ) : (
        <Card className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400">
            {trades?.length === 0 
              ? 'No trades executed yet.'
              : 'No trades match your filter criteria.'
            }
          </p>
        </Card>
      )}
    </div>
  );
}
