import apiClient from '@/lib/api-client';
import type { Rule, CreateRuleRequest, UpdateRuleRequest } from '@/types';

export const rulesApi = {
  getAll: async (): Promise<Rule[]> => {
    const response = await apiClient.get<Rule[]>('/rules/');
    return response.data;
  },

  getById: async (id: string): Promise<Rule> => {
    const response = await apiClient.get<Rule>(`/rules/${id}`);
    return response.data;
  },

  create: async (data: CreateRuleRequest): Promise<Rule> => {
    const response = await apiClient.post<Rule>('/rules/', data);
    return response.data;
  },

  update: async (id: string, data: UpdateRuleRequest): Promise<Rule> => {
    const response = await apiClient.put<Rule>(`/rules/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/rules/${id}`);
  },

  toggle: async (id: string): Promise<Rule> => {
    const response = await apiClient.post<Rule>(`/rules/${id}/toggle`);
    return response.data;
  },

  enable: async (id: string): Promise<Rule> => {
    const response = await apiClient.post<Rule>(`/rules/${id}/enable`);
    return response.data;
  },

  disable: async (id: string): Promise<Rule> => {
    const response = await apiClient.post<Rule>(`/rules/${id}/disable`);
    return response.data;
  },

  validate: async (data: { conditions: Rule['conditions']; actions: Rule['actions'] }): Promise<{
    is_valid: boolean;
    errors: string[];
    warnings: string[];
  }> => {
    const response = await apiClient.post('/rules/validate', data);
    return response.data;
  },
};
