import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { StatsCard } from '../components/shared/StatsCard';
import { Button } from '../components/Button';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import { useAuth } from '../contexts/AuthContext';
import { listJobs } from '../services/jobService';
import type { Job } from '../types/jobTypes';

export const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [stats, setStats] = useState({
    jobs: 0,
    evaluations: 0,
  });
  const [loading, setLoading] = useState(true);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      // Load jobs to get count
      const jobsResponse = await listJobs();
      setStats({
        jobs: jobsResponse.count,
        evaluations: 0, // TODO: Implement evaluations list API
      });
      setRecentJobs(jobsResponse.jobs.slice(0, 5));
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
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
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">Welcome to your CV Analysis System</p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <StatsCard
          title="Total Jobs"
          value={stats.jobs}
          icon={
            <svg
              className="w-8 h-8"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          }
        />
        <StatsCard
          title="Total Evaluations"
          value={stats.evaluations}
          icon={
            <svg
              className="w-8 h-8"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          }
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Button
            variant="primary"
            onClick={() => navigate('/dashboard/profile')}
            className="w-full"
          >
            My Profile
          </Button>
          <Button
            variant="primary"
            onClick={() => navigate('/dashboard/jobs')}
            className="w-full"
          >
            {isAdmin ? 'Manage Jobs' : 'Browse Jobs'}
          </Button>
          {isAdmin && (
            <>
              <Button
                variant="primary"
                onClick={() => navigate('/dashboard/admin')}
                className="w-full"
              >
                Admin Dashboard
              </Button>
              <Button
                variant="outline"
                onClick={() => navigate('/dashboard/jobs')}
                className="w-full"
              >
                Create Job
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Recent Jobs */}
      {recentJobs.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Recent Jobs
            </h2>
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/dashboard/jobs')}
            >
              View All
            </Button>
          </div>
          <div className="space-y-3">
            {recentJobs.map((job) => (
              <div
                key={job._id}
                onClick={() => navigate(`/dashboard/jobs/${job._id}`)}
                className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
              >
                <h3 className="font-medium text-gray-900">{job.title}</h3>
                <p className="text-sm text-gray-500 mt-1">
                  Created: {new Date(job.created_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

