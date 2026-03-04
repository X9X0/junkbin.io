import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import i18n from '../i18n';
import type { User, LoginCredentials, RegisterData } from '../types';
import { auth } from '../api/endpoints';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  googleLogin: (credential: string) => Promise<{ created: boolean }>;
  githubLogin: (code: string) => Promise<{ created: boolean }>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

function applyUserLanguage(userData: User) {
  if (userData.preferred_language) {
    i18n.changeLanguage(userData.preferred_language);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // First get CSRF token, then check auth status
    auth.getCsrfToken()
      .then(() => auth.me())
      .then((userData) => {
        setUser(userData);
        applyUserLanguage(userData);
      })
      .catch(() => {
        // Not authenticated or token invalid
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (credentials: LoginCredentials) => {
    // Login sets HttpOnly cookies automatically
    await auth.login(credentials);
    const userData = await auth.me();
    setUser(userData);
    applyUserLanguage(userData);
  };

  const register = async (data: RegisterData) => {
    await auth.register(data);
    // Auto-login after registration
    await login({ username: data.username, password: data.password });
  };

  const googleLogin = async (credential: string) => {
    const result = await auth.googleLogin(credential);
    const userData = await auth.me();
    setUser(userData);
    applyUserLanguage(userData);
    return { created: result.created };
  };

  const githubLogin = async (code: string) => {
    const result = await auth.githubLogin(code);
    const userData = await auth.me();
    setUser(userData);
    applyUserLanguage(userData);
    return { created: result.created };
  };

  const refreshUser = async () => {
    const userData = await auth.me();
    setUser(userData);
  };

  const logout = async () => {
    try {
      // Call logout endpoint to clear cookies and blacklist token
      await auth.logout();
    } catch {
      // Ignore errors, still clear local state
    }
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        googleLogin,
        githubLogin,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
