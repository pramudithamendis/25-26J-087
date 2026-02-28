import { useState, FormEvent } from 'react';
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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 via-white to-blue-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl w-full space-y-8">
        <div className="text-center">
          <h2 className="text-4xl font-bold text-gray-900 mb-2">
            Create Account
          </h2>
          <p className="text-gray-600">
            Sign up to get started
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          {error && (
            <Alert type="error" onClose={clearError} className="mb-6">
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">
                Personal Information
              </h3>
              <p className="text-sm text-gray-600 mb-4">
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
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <p className="text-xs font-medium text-gray-700 mb-2">
                      Password Requirements:
                    </p>
                    <ul className="space-y-1">
                      {passwordRequirements.map((req, index) => (
                        <li
                          key={index}
                          className={`text-xs flex items-center gap-2 ${
                            req.met ? 'text-green-600' : 'text-gray-500'
                          }`}
                        >
                          <span className={req.met ? 'text-green-500' : 'text-gray-400'}>
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
              className="w-full"
              disabled={!allRequirementsMet}
            >
              Create Account
            </Button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium text-blue-600 hover:text-blue-700"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

