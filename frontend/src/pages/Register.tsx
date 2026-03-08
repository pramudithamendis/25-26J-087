import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/Input';
import { Button } from '../components/Button';
import { Alert } from '../components/Alert';

interface PasswordRequirement {
  label: string;
  met: boolean;
}

export const Register = () => {
  const navigate = useNavigate();
  const { register, error, clearError, loading } = useAuth();

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [city, setCity] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formErrors, setFormErrors] = useState<{
    firstName?: string;
    lastName?: string;
    email?: string;
    city?: string;
    phoneNumber?: string;
    password?: string;
    confirmPassword?: string;
  }>({});

  const checkPasswordRequirements = (pwd: string): PasswordRequirement[] => {
    return [
      {
        label: 'At least 8 characters',
        met: pwd.length >= 8,
      },
      {
        label: 'At least one uppercase letter',
        met: /[A-Z]/.test(pwd),
      },
      {
        label: 'At least one lowercase letter',
        met: /[a-z]/.test(pwd),
      },
      {
        label: 'At least one digit',
        met: /[0-9]/.test(pwd),
      },
      {
        label: 'At least one special character',
        met: /[!@#$%^&*(),.?":{}|<>]/.test(pwd),
      },
      {
        label: 'Maximum 72 characters',
        met: pwd.length <= 72,
      },
    ];
  };

  const passwordRequirements = checkPasswordRequirements(password);
  const allRequirementsMet = passwordRequirements.every((req) => req.met);

  const validateForm = (): boolean => {
    const errors: {
      firstName?: string;
      lastName?: string;
      email?: string;
      city?: string;
      phoneNumber?: string;
      password?: string;
      confirmPassword?: string;
    } = {};

    // First name validation
    if (!firstName.trim()) {
      errors.firstName = 'First name is required';
    } else if (firstName.trim().length < 1 || firstName.trim().length > 50) {
      errors.firstName = 'First name must be between 1 and 50 characters';
    } else if (!/^[a-zA-Z\s\-']+$/.test(firstName.trim())) {
      errors.firstName = 'First name can only contain letters, spaces, hyphens, and apostrophes';
    }

    // Last name validation
    if (!lastName.trim()) {
      errors.lastName = 'Last name is required';
    } else if (lastName.trim().length < 1 || lastName.trim().length > 50) {
      errors.lastName = 'Last name must be between 1 and 50 characters';
    } else if (!/^[a-zA-Z\s\-']+$/.test(lastName.trim())) {
      errors.lastName = 'Last name can only contain letters, spaces, hyphens, and apostrophes';
    }

    // Email validation
    if (!email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Please enter a valid email address';
    }

    // City validation
    if (!city.trim()) {
      errors.city = 'City is required';
    } else if (city.trim().length < 1 || city.trim().length > 100) {
      errors.city = 'City must be between 1 and 100 characters';
    }

    // Phone number validation (optional)
    if (phoneNumber.trim()) {
      const cleaned = phoneNumber.replace(/[\s\-\(\)]/g, '');
      if (!/^\+?[0-9]{7,15}$/.test(cleaned)) {
        errors.phoneNumber = 'Phone number must be 7-15 digits, optionally starting with + for country code';
      }
    }

    // Password validation
    if (!password) {
      errors.password = 'Password is required';
    } else if (!allRequirementsMet) {
      errors.password = 'Password does not meet all requirements';
    }

    // Confirm password validation
    if (!confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
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
      await register({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        city: city.trim(),
        phone_number: phoneNumber.trim() || undefined,
        password,
      });
      navigate('/');
    } catch (err) {
      // Error is handled by AuthContext
    }
  };

  return (
    <div className="h-screen flex bg-slate-50 overflow-hidden">
      {/* Left Side - Image */}
      <div className="hidden lg:block lg:w-5/12 relative h-full">
        <img
          src="https://images.unsplash.com/photo-1522071820081-009f0129c71c?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80"
          alt="Team collaborating in modern office"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-blue-900/30 backdrop-blur-sm mix-blend-multiply"></div>
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900/80 to-transparent"></div>
        <div className="absolute bottom-12 left-12 right-12 text-white">
          <h2 className="text-4xl font-bold mb-4 tracking-tight">Join Our Platform</h2>
          <p className="text-lg text-slate-200">
            Create an account to evaluate candidate CVs, view trend scores, and generate automated performance assessments.
          </p>
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-7/12 flex items-center justify-center relative h-full overflow-y-auto px-4 sm:px-6 lg:px-12 xl:px-24">
        {/* Decorative subtle background blobs */}
        <div className="absolute top-[0%] right-[0%] w-[60%] h-[60%] bg-blue-400/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-[0%] left-[0%] w-[60%] h-[60%] bg-blue-300/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="w-full max-w-2xl space-y-8 relative z-10 py-12 my-auto">
          <div className="text-center lg:text-left">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-2 tracking-tight">
              Create Account
            </h2>
            <p className="text-slate-500 text-sm sm:text-base">
              Sign up to get started
            </p>
          </div>

          <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl shadow-blue-900/5 border border-slate-200/60 p-6 sm:p-8">
            {error && (
              <Alert type="error" onClose={clearError} className="mb-6">
                {error}
              </Alert>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-slate-900 mb-1">
                  Personal Information
                </h3>
                <p className="text-sm text-slate-500 mb-4">
                  Fields marked with * are required.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <Input
                  label="First Name"
                  type="text"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="John"
                  error={formErrors.firstName}
                  required
                  autoComplete="given-name"
                  disabled={loading}
                />

                <Input
                  label="Last Name"
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Doe"
                  error={formErrors.lastName}
                  required
                  autoComplete="family-name"
                  disabled={loading}
                />

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

                <Input
                  label="City"
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="New York"
                  error={formErrors.city}
                  required
                  autoComplete="address-level2"
                  disabled={loading}
                />

                <Input
                  label="Phone Number"
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+1 (555) 123-4567"
                  error={formErrors.phoneNumber}
                  helperText="Optional. Format: +1 (555) 123-4567"
                  autoComplete="tel"
                  disabled={loading}
                />

                <div className="md:col-span-2">
                  <Input
                    label="Password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Create a strong password"
                    error={formErrors.password}
                    required
                    autoComplete="new-password"
                    disabled={loading}
                  />

                  {password && (
                    <div className="mt-3 p-3 bg-blue-50/50 rounded-lg border border-blue-100">
                      <p className="text-xs font-medium text-slate-700 mb-2">
                        Password Requirements:
                      </p>
                      <ul className="space-y-1">
                        {passwordRequirements.map((req, index) => (
                          <li
                            key={index}
                            className={`text-xs flex items-center gap-2 ${req.met ? 'text-emerald-600' : 'text-slate-500'
                              }`}
                          >
                            <span className={req.met ? 'text-emerald-500' : 'text-slate-400'}>
                              {req.met ? '✓' : '○'}
                            </span>
                            {req.label}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                <div className="md:col-span-2">
                  <Input
                    label="Confirm Password"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter your password"
                    error={formErrors.confirmPassword}
                    required
                    autoComplete="new-password"
                    disabled={loading}
                  />
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                isLoading={loading}
                className="w-full shadow-sm mt-4"
                disabled={!allRequirementsMet}
              >
                Create Account
              </Button>
            </form>

            <div className="mt-8 text-center">
              <p className="text-sm text-slate-600">
                Already have an account?{' '}
                <Link
                  to="/login"
                  className="font-medium text-blue-600 hover:text-blue-700 transition-colors"
                >
                  Sign in
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
