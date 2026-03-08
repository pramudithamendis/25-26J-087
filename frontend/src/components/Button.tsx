import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: ReactNode;
}

export const Button = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled,
  className = '',
  children,
  ...props
}: ButtonProps) => {
  const baseClasses = `
    font-medium rounded-lg
    transition-all duration-200
    focus:outline-none focus:ring-2 focus:ring-offset-2
    disabled:opacity-50 disabled:cursor-not-allowed
    flex items-center justify-center gap-2
  `;

  const variantClasses = {
    primary: `
      bg-blue-600 text-white shadow-sm shadow-blue-600/20
      hover:bg-blue-700 hover:shadow-md hover:shadow-blue-600/30 hover:-translate-y-0.5
      focus:ring-blue-500
      active:bg-blue-800 active:translate-y-0
      transition-all duration-300
    `,
    secondary: `
      bg-slate-800 text-white shadow-sm shadow-slate-800/20
      hover:bg-slate-900 hover:shadow-md hover:-translate-y-0.5
      focus:ring-slate-500
      active:bg-black active:translate-y-0
      transition-all duration-300
    `,
    outline: `
      border-2 border-slate-200 text-slate-700 bg-white shadow-sm
      hover:bg-slate-50 hover:border-blue-300 hover:text-blue-700 hover:-translate-y-0.5
      focus:ring-slate-500
      active:bg-slate-100 active:translate-y-0
      transition-all duration-300
    `,
    danger: `
      bg-red-600 text-white
      hover:bg-red-700
      focus:ring-red-500
      active:bg-red-800
    `,
  };

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2.5 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <svg
          className="animate-spin h-5 w-5"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      )}
      {children}
    </button>
  );
};

