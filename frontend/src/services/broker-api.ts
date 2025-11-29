import apiClient from '@/lib/api-client';
import type { BrokerAccount, BrokerStatus, BrokerOAuthResponse } from '@/types';

export const brokerApi = {
  getAccounts: async (): Promise<{ total: number; accounts: BrokerAccount[] }> => {
    const response = await apiClient.get('/user/broker');
    return response.data;
  },

  getAccount: async (brokerType: string): Promise<BrokerAccount> => {
    const response = await apiClient.get<BrokerAccount>(`/user/broker/${brokerType}`);
    return response.data;
  },

  getStatus: async (brokerType: string): Promise<BrokerStatus> => {
    const response = await apiClient.get<BrokerStatus>(`/user/broker/${brokerType}/status`);
    return response.data;
  },

  connect: async (data: {
    broker_type: string;
    api_key: string;
    api_secret: string;
  }): Promise<BrokerOAuthResponse> => {
    const response = await apiClient.post<BrokerOAuthResponse>('/user/broker', data);
    return response.data;
  },

  reconnect: async (brokerType: string): Promise<BrokerOAuthResponse> => {
    const response = await apiClient.post<BrokerOAuthResponse>(
      `/user/broker/${brokerType}/reconnect`
    );
    return response.data;
  },

  disconnect: async (brokerType: string): Promise<void> => {
    await apiClient.delete(`/user/broker/${brokerType}`);
  },
};
