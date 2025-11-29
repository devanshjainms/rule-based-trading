import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { EnvelopeIcon, LockClosedIcon } from '@heroicons/react/24/outline';
import { Button, Input, Alert } from '@/components/ui';
import { authApi } from '@/services';
import { useAuthStore } from '@/stores';
import { ROUTES } from '@/config';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const { setUser, setTokens } = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await authApi.getMe();
      setUser(user);
      navigate(ROUTES.DASHBOARD);
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    },
  });

  const onSubmit = (data: LoginFormData) => {
    setError(null);
    loginMutation.mutate(data);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white text-center mb-8">
        Sign in to your account
      </h2>

      {error && (
        <Alert variant="error" className="mb-6" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Input
          label="Email address"
          type="email"
          autoComplete="email"
          leftIcon={<EnvelopeIcon className="h-5 w-5" />}
          error={errors.email?.message}
          {...register('email')}
        />

        <Input
          label="Password"
          type="password"
          autoComplete="current-password"
          leftIcon={<LockClosedIcon className="h-5 w-5" />}
          error={errors.password?.message}
          {...register('password')}
        />

        <Button
          type="submit"
          className="w-full"
          isLoading={loginMutation.isPending}
        >
          Sign in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
        Don't have an account?{' '}
        <Link
          to={ROUTES.REGISTER}
          className="font-medium text-primary-600 hover:text-primary-500"
        >
          Sign up
        </Link>
      </p>
    </div>
  );
}
