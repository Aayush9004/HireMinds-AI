import React from 'react';
import { Navbar } from './Navbar';
import { BrainCircuit, Heart } from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '7xl' | 'full';
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children, maxWidth = '7xl' }) => {
  const maxWidths = {
    sm: 'max-w-screen-sm',
    md: 'max-w-screen-md',
    lg: 'max-w-screen-lg',
    xl: 'max-w-screen-xl',
    '2xl': 'max-w-screen-2xl',
    '7xl': 'max-w-7xl',
    full: 'max-w-full',
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <Navbar />

      <main className={`flex-1 w-full ${maxWidths[maxWidth]} mx-auto px-4 sm:px-6 lg:px-8 py-8`}>
        {children}
      </main>

      <footer className="border-t border-slate-900 bg-slate-950/50 py-6 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-1.5">
            <BrainCircuit className="w-4 h-4 text-indigo-400" />
            <span className="font-semibold text-slate-300">HireMinds AI</span>
            <span>— Intelligent Candidate Assessment Platform</span>
          </div>
          <p className="text-slate-500">
            Explainable Decision Support • Zero Automated Rejections
          </p>
        </div>
      </footer>
    </div>
  );
};
