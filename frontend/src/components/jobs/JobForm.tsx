import { useState, FormEvent, useEffect } from 'react';
import { Input } from '../Input';
import { Button } from '../Button';
import apiClient from '../../config/api';
import type { JobCreate, JobUpdate, Job } from '../../types/jobTypes';

interface JobFormProps {
  job?: Job;
  onSubmit: (data: JobCreate | JobUpdate) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export const JobForm = ({ 
  job, 
  onSubmit, 
  onCancel, 
  isLoading = false 
}: JobFormProps) => {
  const [title, setTitle] = useState('');
  const [jdText, setJdText] = useState('');
  const [location, setLocation] = useState('');
  const [locations, setLocations] = useState<string[]>([]);
  const [errors, setErrors] = useState<{ 
    title?: string; 
    jdText?: string 
  }>({});
  const isRemote = title.toLowerCase().includes('remote');

  useEffect(() => {
    fetchLocations();
    if (job) {
      setTitle(job.title);
      setJdText(job.jd_text);
      setLocation(job.location || '');
    }
  }, [job]);

  useEffect(() => {
    if (isRemote) setLocation('Remote');
    else if (!job?.location) setLocation('');
  }, [isRemote]);

  const fetchLocations = async () => {
    try {
      const res = await apiClient.get('/locations');
      setLocations((res.data.locations || []).map((l: any) => l.name));
    } catch {}
  };

  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    if (!title.trim()) {
      newErrors.title = 'Title is required';
    } else if (title.length < 3) {
      newErrors.title = 'Title must be at least 3 characters';
    }

    if (!jdText.trim()) {
      newErrors.jdText = 'Job description is required';
    } else if (jdText.length < 50) {
      newErrors.jdText = 'Job description must be at least 50 characters';
    } else if (jdText.length > 50000) {
      newErrors.jdText = 'Job description must be less than 50,000 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    await onSubmit({ title: title.trim(), jd_text: jdText.trim(), location });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <Input
        label="Job Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        error={errors.title}
        required
        disabled={isLoading}
      />

      {/* Location dropdown */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          Job Location
        </label>
        {isRemote ? (
          <input
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-gray-400 bg-gray-100 cursor-not-allowed"
            value="Remote"
            readOnly
            disabled
          />
        ) : (
          <select
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            disabled={isLoading}
            className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            <option value="">Select location (optional)</option>
            {locations.map(loc => (
              <option key={loc} value={loc}>{loc}</option>
            ))}
          </select>
        )}
        {isRemote && (
          <p className="mt-1.5 text-sm text-gray-500">Remote position — location auto-filled</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">
          Job Description 
          <span className="text-red-500 ml-1">*</span>
        </label>
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={12}
          className={`w-full px-4 py-2.5 border rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 disabled:bg-gray-100 disabled:cursor-not-allowed ${
            errors.jdText 
            ? 'border-red-500 focus:ring-red-500' 
            : 'border-gray-300 focus:border-blue-500'
          }`}
          placeholder="Enter the full job description..."
          required
          disabled={isLoading}
        />
        {errors.jdText && (
          <p className="mt-1.5 text-sm text-red-600">{errors.jdText}</p>
        )}
        <p className="mt-1.5 text-sm text-gray-500">
          {jdText.length} / 50,000 characters
        </p>
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" isLoading={isLoading}>
          {job ? 'Update' : 'Create'}
        </Button>
      </div>
    </form>
  );
};

