import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { EnvelopeIcon, LockClosedIcon, UserIcon } from '@heroicons/react/24/outline';
import { Button, Input, Alert } from '@/components/ui';
import { authApi } from '@/services';
import { useAuthStore } from '@/stores';
import { ROUTES } from '@/config';

const registerSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword'],
});

type RegisterFormData = z.infer<typeof registerSchema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setUser, setTokens } = useAuthStore();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const registerMutation = useMutation({
    mutationFn: (data: RegisterFormData) =>
      authApi.register({
        name: data.name,
        email: data.email,
        password: data.password,
      }),
    onSuccess: async (tokens) => {
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await authApi.getMe();
      setUser(user);
      navigate(ROUTES.DASHBOARD);
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    },
  });

  const onSubmit = (data: RegisterFormData) => {
    setError(null);
    registerMutation.mutate(data);
  };

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white text-center mb-8">
        Create your account
      </h2>

      {error && (
        <Alert variant="error" className="mb-6" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Input
          label="Full name"
          type="text"
          autoComplete="name"
          leftIcon={<UserIcon className="h-5 w-5" />}
          error={errors.name?.message}
          {...register('name')}
        />

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
          autoComplete="new-password"
          leftIcon={<LockClosedIcon className="h-5 w-5" />}
          error={errors.password?.message}
          {...register('password')}
        />

        <Input
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          leftIcon={<LockClosedIcon className="h-5 w-5" />}
          error={errors.confirmPassword?.message}
          {...register('confirmPassword')}
        />

        <Button
          type="submit"
          className="w-full"
          isLoading={registerMutation.isPending}
        >
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
        Already have an account?{' '}
        <Link
          to={ROUTES.LOGIN}
          className="font-medium text-primary-600 hover:text-primary-500"
        >
          Sign in
        </Link>
      </p>
    </div>
  );
}
