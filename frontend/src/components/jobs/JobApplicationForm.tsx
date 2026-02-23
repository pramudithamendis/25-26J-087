import { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { Input } from '../Input';
import { Button } from '../Button';
import { FileUpload } from '../candidates/FileUpload';
import { Alert } from '../Alert';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { getCurrentUserProfile } from '../../services/userService';
import { applyToJob } from '../../services/applicationService';
import type { User } from '../../types/auth';
import type { ApplicationData } from '../../types/applicationTypes';

interface JobApplicationFormProps {
  jobId: string;
  onSubmit: (evaluationId: string) => void;
  onCancel: () => void;
}

export const JobApplicationForm = ({
  jobId,
  onSubmit,
  onCancel,
}: JobApplicationFormProps) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form fields
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [city, setCity] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [linkedinResumeFile, setLinkedinResumeFile] = useState<File | null>(null);

  // Form errors
  const [formErrors, setFormErrors] = useState<{
    firstName?: string;
    lastName?: string;
    city?: string;
    phoneNumber?: string;
    githubUrl?: string;
    linkedinUrl?: string;
  }>({});

  useEffect(() => {
    loadUserProfile();
  }, []);

  const loadUserProfile = async () => {
    try {
      setLoading(true);
      const userData = await getCurrentUserProfile();
      setUser(userData);
      
      // Pre-populate form fields
      setFirstName(userData.first_name || '');
      setLastName(userData.last_name || '');
      setEmail(userData.email || '');
      setCity(userData.city || '');
      setPhoneNumber(userData.phone_number || '');
      setGithubUrl(userData.github_url || '');
      setLinkedinUrl(userData.linkedin_url || '');
    } catch (err: any) {
      setError(err.detail || 'Failed to load user profile');
    } finally {
      setLoading(false);
    }
  };

  const validateForm = (): boolean => {
    const errors: typeof formErrors = {};

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

    // GitHub URL validation (optional)
    if (githubUrl.trim()) {
      const githubPattern = /^(https?:\/\/)?(www\.)?github\.com\/[a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38}(\/)?$/i;
      if (!githubPattern.test(githubUrl.trim())) {
        errors.githubUrl = 'Invalid GitHub URL format. Use: https://github.com/username or github.com/username';
      }
    }

    // LinkedIn URL validation removed - no validation required

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleResumeUpload = async (file: File) => {
    setResumeFile(file);
  };

  const handleLinkedInResumeUpload = async (file: File) => {
    setLinkedinResumeFile(file);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    try {
      setSubmitting(true);

      const applicationData: ApplicationData = {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        city: city.trim(),
        phone_number: phoneNumber.trim() || undefined,
        // Always include URLs (even if empty string) so they're saved/updated in profile
        github_url: githubUrl.trim() || '',
        linkedin_url: linkedinUrl.trim() || '',
        resume: resumeFile || undefined,
        linkedin_resume: linkedinResumeFile || undefined,
      };

      const response = await applyToJob(jobId, applicationData);
      // Navigate to confirmation page
      onSubmit(response.application_id);
    } catch (err: any) {
      setError(err.detail || 'Failed to submit application. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <Alert type="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Section 1: Personal Information */}
      <div className="space-y-4">
        <div className="pb-3 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Personal Information
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Fields marked with * are required.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="First Name"
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            placeholder="John"
            error={formErrors.firstName}
            required
            autoComplete="given-name"
            disabled={submitting}
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
            disabled={submitting}
          />

          <Input
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            autoComplete="email"
            disabled={true}
            className="bg-gray-50"
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
            disabled={submitting}
          />

          <div className="md:col-span-2">
            <Input
              label="Phone Number"
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+1 (555) 123-4567"
              error={formErrors.phoneNumber}
              autoComplete="tel"
              disabled={submitting}
            />
          </div>
        </div>
      </div>

      {/* Section 2: Application Details */}
      <div className="space-y-4 pt-6 border-t border-gray-200">
        <div className="pb-3">
          <h3 className="text-lg font-semibold text-gray-900">
            Application Materials
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Provide your GitHub and LinkedIn profiles, and upload your resumes.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="GitHub URL"
            type="url"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
            placeholder="https://github.com/username"
            error={formErrors.githubUrl}
            autoComplete="url"
            disabled={submitting}
          />

          <Input
            label="LinkedIn URL"
            type="url"
            value={linkedinUrl}
            onChange={(e) => setLinkedinUrl(e.target.value)}
            placeholder="https://linkedin.com/in/username"
            error={formErrors.linkedinUrl}
            autoComplete="url"
            disabled={submitting}
          />
        </div>

        <div className="space-y-4">
          <div>
            <FileUpload
              label="Upload Resume (PDF)"
              accept=".pdf"
              onUpload={handleResumeUpload}
              disabled={submitting}
            />
            {user?.cv_file_path && !resumeFile && (
              <p className="mt-2 text-sm text-green-600">
                ✓ Current resume: {user.cv_file_path.split('/').pop()}
              </p>
            )}
            {resumeFile && (
              <p className="mt-2 text-sm text-blue-600">
                ✓ New file selected: {resumeFile.name}
              </p>
            )}
          </div>

          <div>
            <FileUpload
              label="Upload LinkedIn Resume (PDF)"
              accept=".pdf"
              onUpload={handleLinkedInResumeUpload}
              disabled={submitting}
            />
            {user?.linkedin_file_path && !linkedinResumeFile && (
              <p className="mt-2 text-sm text-green-600">
                ✓ Current LinkedIn resume: {user.linkedin_file_path.split('/').pop()}
              </p>
            )}
            {linkedinResumeFile && (
              <p className="mt-2 text-sm text-blue-600">
                ✓ New file selected: {linkedinResumeFile.name}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Submit Buttons */}
      <div className="flex justify-end gap-3 pt-6 border-t border-gray-200">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </Button>
        <Button
          type="submit"
          variant="primary"
          isLoading={submitting}
          disabled={submitting}
        >
          Submit Application
        </Button>
      </div>
    </form>
  );
};

