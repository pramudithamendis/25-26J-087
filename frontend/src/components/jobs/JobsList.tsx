import { useState, useEffect } from 'react';
import { JobCard } from './JobCard';
import { SearchBar } from '../shared/SearchBar';
import { EmptyState } from '../shared/EmptyState';
import { LoadingSpinner } from '../shared/LoadingSpinner';
import { Button } from '../Button';
import type { Job } from '../../types/jobTypes';

interface JobsListProps {
  jobs: Job[];
  loading?: boolean;
  onSearch: (query: string) => void;
  onCreateNew?: () => void;
  showCreateButton?: boolean;
}

export const JobsList = ({
  jobs,
  loading = false,
  onSearch,
  onCreateNew,
  showCreateButton = false,
}: JobsListProps) => {
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    onSearch(searchQuery);
  }, [searchQuery, onSearch]);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div>
        <div className="mb-6">
          <SearchBar placeholder="Search jobs..." onSearch={setSearchQuery} />
        </div>
        <EmptyState
          title="No jobs found"
          description={
            showCreateButton
              ? "Get started by creating your first job posting."
              : "No job postings available at the moment."
          }
          action={
            showCreateButton && onCreateNew ? (
              <Button variant="primary" onClick={onCreateNew}>
                Create Job
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="flex-1 max-w-md">
          <SearchBar placeholder="Search jobs..." onSearch={setSearchQuery} />
        </div>
        {showCreateButton && onCreateNew && (
          <Button variant="primary" onClick={onCreateNew}>
            Create Job
          </Button>
        )}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {jobs
          .filter((job) => job._id) // Filter out jobs without _id
          .map((job) => (
            <JobCard key={job._id} job={job} />
          ))}
      </div>
    </div>
  );
};

