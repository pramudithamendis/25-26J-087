import { ReactNode } from 'react';

interface StatsCardProps {
  title: string;
  value: string | number;
  icon?: ReactNode;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  className?: string;
}

export const StatsCard = ({
  title,
  value,
  icon,
  trend,
  className = '',
}: StatsCardProps) => {
  return (
    <div
      className={`bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md hover:border-blue-200 transition-all duration-300 group ${className}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-500 mb-1">{title}</p>
          <p className="text-2xl font-bold text-slate-900 group-hover:text-blue-700 transition-colors duration-300">{value}</p>
          {trend && (
            <p
              className={`text-sm mt-2 font-medium ${trend.isPositive ? 'text-emerald-600' : 'text-rose-600'
                }`}
            >
              <span className={trend.isPositive ? 'text-emerald-500' : 'text-rose-500'}>
                {trend.isPositive ? '↑' : '↓'}
              </span>{' '}
              {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        {icon && (
          <div className="ml-4 flex-shrink-0">
            <div className="bg-blue-50 text-blue-600 rounded-xl p-3 ring-1 ring-blue-100 group-hover:bg-blue-600 group-hover:text-white transition-colors duration-300">
              {icon}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

