import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Button } from '../../components/ui/Button';
import { Home } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <AppLayout maxWidth="md">
      <div className="py-20 text-center">
        <h1 className="text-7xl font-extrabold text-indigo-500 mb-4">404</h1>
        <h2 className="text-xl font-bold text-white mb-2">Page Not Found</h2>
        <p className="text-xs text-slate-400 max-w-sm mx-auto mb-6">
          The page or resource you are looking for does not exist or has been moved.
        </p>
        <Button variant="primary" onClick={() => navigate('/')} leftIcon={<Home className="w-4 h-4" />}>
          Back to Home
        </Button>
      </div>
    </AppLayout>
  );
};
