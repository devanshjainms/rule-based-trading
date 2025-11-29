import { Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Navbar from './Navbar';
import { tradingApi } from '@/services';
import { ENGINE_STATUS_POLL_INTERVAL } from '@/config';

export default function MainLayout() {
  const { data: engineStatus } = useQuery({
    queryKey: ['engineStatus'],
    queryFn: tradingApi.getEngineStatus,
    refetchInterval: ENGINE_STATUS_POLL_INTERVAL,
    retry: false,
  });

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar engineStatus={engineStatus} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
