import { ReactElement, ReactNode } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '../context/AuthContext';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

interface AllProvidersProps {
  children: ReactNode;
}

function AllProviders({ children }: AllProvidersProps) {
  const queryClient = createTestQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>{children}</BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

// Custom render that includes all providers
function customRender(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Re-export everything from testing-library
export * from '@testing-library/react';
export { userEvent } from '@testing-library/user-event';

// Override render method
export { customRender as render };

// Helper to create a QueryClient for component tests
export { createTestQueryClient };

// Test user data
export const testUser = {
  id: 'test-user-id',
  username: 'testuser',
  email: 'test@example.com',
  reputation_score: 100,
  contribution_count: 10,
  is_trusted: false,
  is_moderator: false,
  created_at: '2024-01-01T00:00:00Z',
};

export const trustedUser = {
  ...testUser,
  id: 'trusted-user-id',
  username: 'trusteduser',
  is_trusted: true,
  reputation_score: 500,
  contribution_count: 100,
};

export const moderatorUser = {
  ...testUser,
  id: 'moderator-user-id',
  username: 'moderator',
  is_moderator: true,
};
