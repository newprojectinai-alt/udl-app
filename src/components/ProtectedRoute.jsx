import { Outlet } from 'react-router-dom';
import { useAuth } from '@/lib/AuthContext';

export default function ProtectedRoute({ unauthenticatedElement = null }) {
  const { isAuthenticated, isLoadingAuth } = useAuth();
  if (isLoadingAuth) return <div className="fixed inset-0 flex items-center justify-center">Loading...</div>;
  if (!isAuthenticated) return unauthenticatedElement;
  return <Outlet />;
}
