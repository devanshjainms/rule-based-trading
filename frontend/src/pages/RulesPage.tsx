import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PlusIcon, PencilIcon, TrashIcon, PlayIcon, StopIcon } from '@heroicons/react/24/outline';
import { rulesApi } from '@/services';
import type { Rule, CreateRuleRequest, UpdateRuleRequest } from '@/types';
import { Card, Button, Badge, Spinner, Modal, Input, Alert } from '@/components/ui';

type RuleFormData = CreateRuleRequest;

const defaultRuleForm: RuleFormData = {
  name: '',
  symbol: '',
  conditions: [],
  actions: [],
  is_active: true,
  priority: 1,
};

export function RulesPage() {
  const queryClient = useQueryClient();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [formData, setFormData] = useState<RuleFormData>(defaultRuleForm);
  const [conditionsJson, setConditionsJson] = useState('[]');
  const [actionsJson, setActionsJson] = useState('[]');
  const [error, setError] = useState<string | null>(null);

  const { data: rules, isLoading } = useQuery({
    queryKey: ['rules'],
    queryFn: rulesApi.getAll,
  });

  const createMutation = useMutation({
    mutationFn: rulesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      closeModal();
    },
    onError: (err: Error) => setError(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateRuleRequest }) =>
      rulesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
      closeModal();
    },
    onError: (err: Error) => setError(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => rulesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const enableMutation = useMutation({
    mutationFn: (id: string) => rulesApi.enable(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const disableMutation = useMutation({
    mutationFn: (id: string) => rulesApi.disable(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const openCreateModal = () => {
    setEditingRule(null);
    setFormData(defaultRuleForm);
    setConditionsJson('[]');
    setActionsJson('[]');
    setError(null);
    setIsModalOpen(true);
  };

  const openEditModal = (rule: Rule) => {
    setEditingRule(rule);
    setFormData({
      name: rule.name,
      description: rule.description,
      symbol: rule.symbol,
      conditions: rule.conditions,
      actions: rule.actions,
      is_active: rule.is_active,
      priority: rule.priority,
    });
    setConditionsJson(JSON.stringify(rule.conditions, null, 2));
    setActionsJson(JSON.stringify(rule.actions, null, 2));
    setError(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingRule(null);
    setFormData(defaultRuleForm);
    setError(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      const conditions = JSON.parse(conditionsJson);
      const actions = JSON.parse(actionsJson);

      const payload = {
        ...formData,
        conditions,
        actions,
      };

      if (editingRule) {
        updateMutation.mutate({ id: editingRule.id, data: payload });
      } else {
        createMutation.mutate(payload);
      }
    } catch {
      setError('Invalid JSON in conditions or actions');
    }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this rule?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleToggle = (rule: Rule) => {
    if (rule.is_active) {
      disableMutation.mutate(rule.id);
    } else {
      enableMutation.mutate(rule.id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Trading Rules
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage your automated trading rules
          </p>
        </div>
        <Button onClick={openCreateModal} leftIcon={<PlusIcon className="h-5 w-5" />}>
          Create Rule
        </Button>
      </div>

      {error && (
        <Alert variant="error" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Rules Grid */}
      {rules && rules.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {rules.map((rule) => (
            <Card key={rule.id} className="relative">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {rule.name}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {rule.symbol}
                  </p>
                </div>
                <Badge variant={rule.is_active ? 'success' : 'gray'}>
                  {rule.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </div>

              <div className="space-y-3 text-sm">
                {rule.description && (
                  <p className="text-gray-600 dark:text-gray-300">{rule.description}</p>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Priority</span>
                  <span className="text-gray-900 dark:text-white">{rule.priority}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Conditions</span>
                  <span className="text-gray-900 dark:text-white">{rule.conditions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Actions</span>
                  <span className="text-gray-900 dark:text-white">{rule.actions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">Triggered</span>
                  <span className="text-gray-900 dark:text-white">{rule.trigger_count} times</span>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700 flex gap-2">
                <Button
                  size="sm"
                  variant={rule.is_active ? 'ghost' : 'primary'}
                  onClick={() => handleToggle(rule)}
                  disabled={enableMutation.isPending || disableMutation.isPending}
                  leftIcon={rule.is_active ? 
                    <StopIcon className="h-4 w-4" /> : 
                    <PlayIcon className="h-4 w-4" />
                  }
                >
                  {rule.is_active ? 'Disable' : 'Enable'}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => openEditModal(rule)}
                  leftIcon={<PencilIcon className="h-4 w-4" />}
                >
                  Edit
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleDelete(rule.id)}
                  disabled={deleteMutation.isPending}
                  className="text-red-600 hover:text-red-700 dark:text-red-400"
                >
                  <TrashIcon className="h-4 w-4" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            No trading rules yet. Create your first rule to get started.
          </p>
          <Button onClick={openCreateModal} leftIcon={<PlusIcon className="h-5 w-5" />}>
            Create Rule
          </Button>
        </Card>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={closeModal}
        title={editingRule ? 'Edit Rule' : 'Create New Rule'}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <Alert variant="error" onDismiss={() => setError(null)}>
              {error}
            </Alert>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              label="Rule Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="My Trading Rule"
              required
            />
            <Input
              label="Symbol"
              value={formData.symbol}
              onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
              placeholder="RELIANCE"
              required
            />
          </div>

          <Input
            label="Description"
            value={formData.description || ''}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Optional description for this rule"
          />

          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Priority"
              type="number"
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: Number(e.target.value) })}
              min={1}
              required
            />
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Active</span>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Conditions (JSON)
            </label>
            <textarea
              value={conditionsJson}
              onChange={(e) => setConditionsJson(e.target.value)}
              className="w-full h-32 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm font-mono text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder='[{"indicator": "rsi", "operator": "lt", "value": 30}]'
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Actions (JSON)
            </label>
            <textarea
              value={actionsJson}
              onChange={(e) => setActionsJson(e.target.value)}
              className="w-full h-32 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-4 py-2 text-sm font-mono text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder='[{"action": "buy", "quantity": 10, "order_type": "MARKET"}]'
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button type="button" variant="secondary" onClick={closeModal}>
              Cancel
            </Button>
            <Button
              type="submit"
              isLoading={createMutation.isPending || updateMutation.isPending}
            >
              {editingRule ? 'Update Rule' : 'Create Rule'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
