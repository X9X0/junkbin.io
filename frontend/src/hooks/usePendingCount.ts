import { useQuery } from '@tanstack/react-query';
import { products } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import { usePageVisibility } from './usePageVisibility';

export function usePendingCount(): number {
  const { user, isAuthenticated } = useAuth();
  const isVisible = usePageVisibility();
  const isMod = isAuthenticated && (user?.is_moderator || user?.is_staff);

  const { data } = useQuery({
    queryKey: ['pendingCounts'],
    queryFn: products.pendingCounts,
    enabled: !!isMod && isVisible,
    refetchInterval: isVisible ? 60000 : false,
    staleTime: 30000,
  });

  if (!data) return 0;
  return data.products + data.schematics + data.recipes + data.images + data.component_images + data.datasheets;
}
