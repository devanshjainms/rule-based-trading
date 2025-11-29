import apiClient from '@/lib/api-client';
import type {
  Position,
  Trade,
  Order,
  EngineStatus,
} from '@/types';

export const tradingApi = {
  // Positions
  getPositions: async (): Promise<Position[]> => {
    const response = await apiClient.get<Position[]>('/trading/positions');
    return response.data;
  },

  closePosition: async (symbol: string): Promise<void> => {
    await apiClient.post(`/trading/positions/${symbol}/close`);
  },

  // Orders
  getOrders: async (): Promise<Order[]> => {
    const response = await apiClient.get<Order[]>('/trading/orders');
    return response.data;
  },

  placeOrder: async (data: {
    symbol: string;
    exchange: string;
    transaction_type: 'BUY' | 'SELL';
    quantity: number;
    order_type: string;
    price?: number;
    product?: string;
  }): Promise<{ order_id: string }> => {
    const response = await apiClient.post('/trading/orders', data);
    return response.data;
  },

  cancelOrder: async (orderId: string): Promise<void> => {
    await apiClient.delete(`/trading/orders/${orderId}`);
  },

  // Trades
  getTrades: async (params?: {
    symbol?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<Trade[]> => {
    const response = await apiClient.get<Trade[]>('/trading/trades', { params });
    return response.data;
  },

  // Engine
  getEngineStatus: async (): Promise<EngineStatus> => {
    const response = await apiClient.get<EngineStatus>('/trading/engine/status');
    return response.data;
  },

  startEngine: async (): Promise<EngineStatus> => {
    const response = await apiClient.post<EngineStatus>('/trading/engine/start');
    return response.data;
  },

  stopEngine: async (): Promise<EngineStatus> => {
    const response = await apiClient.post<EngineStatus>('/trading/engine/stop');
    return response.data;
  },
};
