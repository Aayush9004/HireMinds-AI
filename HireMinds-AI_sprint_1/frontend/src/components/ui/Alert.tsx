import React from 'react';
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from 'lucide-react';

export type AlertType = 'info' | 'success' | 'warning' | 'error' | 'danger';

export interface AlertProps {
  type?: AlertType;
  variant?: AlertType;
  title?: string;
  children: React.ReactNode;
  className?: string;
  onClose?: () => void;
}

export const Alert: React.FC<AlertProps> = ({
  type,
  variant,
  title,
  children,
  className = '',
  onClose,
}) => {
  const effectiveType = variant === 'danger' ? 'error' : (type === 'danger' ? 'error' : (variant || type || 'info'));

  const styles = {
    info: {
      container: 'bg-indigo-950/40 border-indigo-500/30 text-indigo-200',
      icon: <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />,
    },
    success: {
      container: 'bg-emerald-950/40 border-emerald-500/30 text-emerald-200',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />,
    },
    warning: {
      container: 'bg-amber-950/40 border-amber-500/30 text-amber-200',
      icon: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />,
    },
    error: {
      container: 'bg-rose-950/40 border-rose-500/30 text-rose-200',
      icon: <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />,
    },
  };

  const current = styles[effectiveType as keyof typeof styles] || styles.info;

  return (
    <div
      className={`flex items-start gap-3 p-3.5 rounded-lg border text-xs leading-relaxed ${current.container} ${className}`}
      role="alert"
    >
      {current.icon}
      <div className="flex-1">
        {title && <h5 className="font-semibold text-slate-100 mb-0.5">{title}</h5>}
        <div>{children}</div>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="text-slate-400 hover:text-slate-200 p-0.5 rounded cursor-pointer"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
