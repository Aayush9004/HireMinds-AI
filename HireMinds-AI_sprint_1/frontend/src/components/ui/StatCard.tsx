import React from 'react';
import { Card } from './Card';

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode | React.ElementType;
  description?: string;
  trend?: {
    value: string;
    isPositive: boolean;
  };
  onClick?: () => void;
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  description,
  trend,
  onClick,
  className = '',
}) => {
  const renderIcon = () => {
    if (!icon) return null;
    if (React.isValidElement(icon)) return icon;
    if (typeof icon === 'function') {
      const IconComp = icon as React.ElementType;
      return <IconComp className="w-5 h-5" />;
    }
    return icon;
  };

  return (
    <Card
      onClick={onClick}
      hoverable={!!onClick}
      className={`relative overflow-hidden ${className}`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-slate-400">{title}</p>
          <h4 className="text-2xl font-bold text-slate-100 mt-1">{value}</h4>
          {(subtitle || description) && (
            <p className="text-xs text-slate-500 mt-1">{subtitle || description}</p>
          )}
          {trend && (
            <p
              className={`text-xs mt-2 font-medium flex items-center gap-1 ${
                trend.isPositive ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              <span>{trend.isPositive ? '↑' : '↓'}</span>
              <span>{trend.value}</span>
            </p>
          )}
        </div>
        <div className="w-11 h-11 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
          {renderIcon()}
        </div>
      </div>
    </Card>
  );
};
