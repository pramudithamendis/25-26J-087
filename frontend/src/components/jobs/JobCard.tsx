import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import type { Job } from '../../types/jobTypes';

interface JobCardProps {
  job: Job;
}

export const JobCard = ({ job }: JobCardProps) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const handleClick = () => {
    if (!job._id) {
      console.error('Job ID is missing:', job);
      return;
    }
    navigate(`/dashboard/jobs/${job._id}`);
  };

  const preview = job.jd_text.substring(0, 150);
  const truncated = job.jd_text.length > 150;

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow cursor-pointer"
    >
      <h3 className="text-lg font-semibold text-gray-900 mb-2">{job.title}</h3>
      <p className="text-sm text-gray-600 mb-4 line-clamp-3">
        {preview}
        {truncated && '...'}
      </p>
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex flex-col gap-1">
          <span>
            Created: {new Date(job.created_at).toLocaleDateString()}
          </span>
          {job.application_count !== undefined && (
            <span className="text-gray-600 font-medium">
              {job.application_count === 0
                ? 'No applications yet'
                : `${job.application_count} ${job.application_count === 1 ? 'application' : 'applications'}`}
            </span>
          )}
        </div>
        <span className="text-blue-600 hover:text-blue-700 font-medium">
          {isAdmin ? 'View Details →' : 'View & Apply →'}
        </span>
      </div>
    </div>
  );
};

