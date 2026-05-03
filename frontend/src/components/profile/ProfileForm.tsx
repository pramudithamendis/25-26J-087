import { useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { Input } from '../Input';
import { Button } from '../Button';
import type { User } from '../../types/auth';
import type { UserUpdate } from '../../services/userService';

interface ProfileFormProps {
  user: User;
  onSubmit: (data: UserUpdate) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export const ProfileForm = ({
  user,
  onSubmit,
  onCancel,
  isLoading = false,
}: ProfileFormProps) => {
  const [name, setName] = useState('');
  const [githubHandle, setGithubHandle] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [errors, setErrors] = useState<{
    name?: string;
    githubHandle?: string;
    githubUrl?: string;
    linkedinUrl?: string;
  }>({});

  useEffect(() => {
    if (user) {
      setName(user.name || '');
      setGithubHandle(user.github_handle || '');
      setGithubUrl(user.github_url || '');
      setLinkedinUrl(user.linkedin_url || '');
    }
  }, [user]);

  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    if (name && name.length < 2) {
      newErrors.name = 'Name must be at least 2 characters';
    }

    if (githubHandle && githubHandle.length > 39) {
      newErrors.githubHandle = 'GitHub handle must be 39 characters or less';
    }

    // Validate GitHub URL format if provided
    if (githubUrl.trim()) {
      const githubPattern = /^(https?:\/\/)?(www\.)?github\.com\/[a-zA-Z0-9]([a-zA-Z0-9]|-(?![.-])){0,38}(\/)?$/i;
      if (!githubPattern.test(githubUrl.trim())) {
        newErrors.githubUrl = 'Invalid GitHub URL format. Use: https://github.com/username or github.com/username';
      }
    }

    // LinkedIn URL has no validation (as per previous requirement)

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const data: UserUpdate = {
      name: name.trim() || undefined,
      github_handle: githubHandle.trim() || undefined,
      github_url: githubUrl.trim() || undefined,
      linkedin_url: linkedinUrl.trim() || undefined,
    };

    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={errors.name}
        placeholder="Your full name"
        disabled={isLoading}
      />

      <Input
        label="GitHub Handle (optional)"
        value={githubHandle}
        onChange={(e) => setGithubHandle(e.target.value)}
        error={errors.githubHandle}
        placeholder="username"
        disabled={isLoading}
      />

      <div className="pt-4 border-t border-gray-200">
        <h3 className="text-sm font-medium text-gray-700 mb-4">
          Professional Profiles
        </h3>

        <div className="space-y-4">
          <Input
            label="GitHub URL (optional)"
            type="url"
            value={githubUrl}
            onChange={(e) => setGithubUrl(e.target.value)}
            error={errors.githubUrl}
            placeholder="https://github.com/username"
            helperText="Your GitHub profile URL"
            disabled={isLoading}
          />

          <Input
            label="LinkedIn URL (optional)"
            type="url"
            value={linkedinUrl}
            onChange={(e) => setLinkedinUrl(e.target.value)}
            error={errors.linkedinUrl}
            placeholder="https://linkedin.com/in/username"
            helperText="Your LinkedIn profile URL"
            disabled={isLoading}
          />
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" isLoading={isLoading}>
          Save Changes
        </Button>
      </div>
    </form>
  );
};
