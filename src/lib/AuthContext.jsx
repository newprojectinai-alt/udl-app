import { createContext, useContext, useEffect, useState } from 'react';
import { getCurrentUser, loginAs, logout as logoutUser } from '@/services/authService';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoadingAuth, setIsLoadingAuth] = useState(true);
  const [authError, setAuthError] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  const checkUserAuth = async () => {
    setIsLoadingAuth(true);
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setIsAuthenticated(!!currentUser);
      setAuthError(null);
    } catch (error) {
      setAuthError({ type: 'unknown', message: error.message });
      setIsAuthenticated(false);
    } finally {
      setIsLoadingAuth(false);
      setAuthChecked(true);
    }
  };

  useEffect(() => {
    checkUserAuth();
  }, []);

  const logout = async () => {
    await logoutUser();
    setUser(null);
    setIsAuthenticated(false);
    window.location.href = '/';
  };

  const switchRole = async (role) => {
    const nextUser = await loginAs(role);
    setUser(nextUser);
    setIsAuthenticated(true);
    window.location.href = `/${role}`;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoadingAuth,
        isLoadingPublicSettings: false,
        authError,
        appPublicSettings: null,
        authChecked,
        logout,
        navigateToLogin: () => {},
        checkUserAuth,
        checkAppState: checkUserAuth,
        switchRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
