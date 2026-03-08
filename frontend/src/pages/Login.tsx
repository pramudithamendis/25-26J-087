import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { Alert } from '../components/Alert';

export const Login = () => {
  const navigate = useNavigate();
  const { login, error, clearError, loading } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [formErrors, setFormErrors] = useState<{
    email?: string;
    password?: string;
  }>({});

  const validateForm = (): boolean => {
    const errors: { email?: string; password?: string } = {};

    if (!email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Please enter a valid email address';
    }

    if (!password) {
      errors.password = 'Password is required';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    clearError();

    if (!validateForm()) {
      return;
    }

    try {
      await login({ email, password });
      navigate('/');
    } catch (err) {
      // Error is handled by AuthContext
    }
  };

  return (
    <div className="h-screen flex bg-slate-50 overflow-hidden">
      {/* Left Side - Image */}
      <div className="hidden lg:block lg:w-1/2 relative h-full">
        <img
          src="https://images.unsplash.com/photo-1497215728101-856f4ea42174?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80"
          alt="Office dashboard workspace"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-blue-900/30 backdrop-blur-sm mix-blend-multiply"></div>
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent"></div>
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <h2 className="text-4xl font-bold mb-4 tracking-tight">Streamline Your Hiring</h2>
          <p className="text-lg text-slate-200">
            Access advanced analytics, trend scores, and early attrition predictions all in one intuitive dashboard.
          </p>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center relative h-full overflow-y-auto px-4 sm:px-6 lg:px-12 xl:px-24">
        {/* Decorative subtle background blobs */}
        <div className="absolute top-[0%] right-[0%] w-[60%] h-[60%] bg-blue-400/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-[0%] left-[0%] w-[60%] h-[60%] bg-blue-300/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="w-full max-w-md space-y-8 relative z-10 py-12 my-auto">
          <div className="text-center lg:text-left">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-2 tracking-tight">
              Welcome Back
            </h2>
            <p className="text-slate-500 text-sm sm:text-base">
              Sign in to your account to continue
            </p>
          </div>

          <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl shadow-blue-900/5 border border-slate-200/60 p-6 sm:p-8">
            {error && (
              <Alert type="error" onClose={clearError} className="mb-6">
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <Input
                label="Email Address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                error={formErrors.email}
                required
                autoComplete="email"
                disabled={loading}
              />

              <div>
                <Input
                  label="Password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  error={formErrors.password}
                  required
                  autoComplete="current-password"
                  disabled={loading}
                />
                <div className="mt-2 text-right">
                  <Link
                    to="/forgot-password"
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium transition-colors"
                  >
                    Forgot password?
                  </Link>
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={loading}
                className="w-full"
              >
                Sign In
              </Button>
            </form>

            <div className="mt-8 text-center">
              <p className="text-sm text-slate-600">
                Don't have an account?{" "}
                <Link
                  to="/register"
                  className="font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  Sign up
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
