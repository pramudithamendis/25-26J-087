import { useState, type FormEvent, useEffect } from 'react';
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
  const [projectType, setProjectType] = useState<string>('general');
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
      setProjectType(job.project_type || 'general');
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

    const data: JobCreate | JobUpdate = {
      title: title.trim(),
      jd_text: jdText.trim(),
      location: location || undefined,
      project_type: projectType,
    };

    await onSubmit(data);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      {/* Top row: Title + Project type - compact, no scroll */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="min-w-0">
          <Input
            label="Job Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            error={errors.title}
            required
            disabled={isLoading}
          />
        </div>
        <div className="min-w-0">
          <label className="block text-sm font-medium text-slate-700 mb-1.5">
            Project type
          </label>
          <select
            value={projectType}
            onChange={(e) => setProjectType(e.target.value)}
            disabled={isLoading}
            className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition-all duration-200 disabled:bg-slate-50 disabled:cursor-not-allowed"
          >
            <option value="general">General</option>
            <option value="r_and_d">R&D Project</option>
            <option value="production">Production Project</option>
            <option value="support">Support</option>
          </select>
          <p className="mt-1 text-xs text-slate-500">
            Affects how CVs are scored (e.g. R&D vs Production).
          </p>
        </div>
      </div>

      {/* Location dropdown */}
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1.5">
          Job Location
        </label>
        {isRemote ? (
          <input
            className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-slate-400 bg-slate-100 cursor-not-allowed"
            value="Remote"
            readOnly
            disabled
          />
        ) : (
          <select
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            disabled={isLoading}
            className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition-all duration-200 disabled:bg-slate-50 disabled:cursor-not-allowed"
          >
            <option value="">Select location (optional)</option>
            {locations.map(loc => (
              <option key={loc} value={loc}>{loc}</option>
            ))}
          </select>
        )}
        {isRemote && (
          <p className="mt-1.5 text-sm text-slate-500">Remote position — location auto-filled</p>
        )}
      </div>

      {/* Job Description - fixed height so no scroll */}
      <div className="min-h-0">
        <div className="flex items-baseline justify-between gap-2 mb-1.5">
          <label className="text-sm font-medium text-slate-700">
            Job Description <span className="text-red-500">*</span>
          </label>
          <span className="text-xs text-slate-500 tabular-nums">{jdText.length} / 50,000</span>
        </div>
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={5}
          className={`w-full px-3.5 py-2.5 border rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 transition-all duration-200 disabled:bg-slate-50 disabled:cursor-not-allowed resize-y min-h-[100px] max-h-[200px] ${
            errors.jdText
              ? 'border-red-400 focus:ring-red-400'
              : 'border-slate-200'
          }`}
          placeholder="Enter the full job description..."
          required
          disabled={isLoading}
        />
        {errors.jdText && (
          <p className="mt-1 text-sm text-red-600">{errors.jdText}</p>
        )}
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-2 border-t border-slate-100">
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

