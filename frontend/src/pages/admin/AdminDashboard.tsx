import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { StatsCard } from "../../components/shared/StatsCard";
import { Button } from "../../components/Button";
import { LoadingSpinner } from "../../components/shared/LoadingSpinner";
import { Alert } from "../../components/Alert";
import { getAdminStats } from "../../services/adminService";

import { Link } from "react-router-dom";

export const AdminDashboard = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    total_jobs: 0,
    total_applications: 0,
    total_users: 0,
    total_evaluations: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAdminStats();
      setStats(data);
    } catch (err: any) {
      setError(err.detail || "Failed to load statistics");
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
    <div className="space-y-6">
      <div className="mb-8 border-b border-slate-200 pb-6">
        <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Admin Dashboard</h1>
        <p className="text-slate-500 mt-2 text-lg">Manage jobs, applications, users, and evaluations</p>
      </div>

      {error && (
        <Alert type="error" onClose={() => setError(null)} className="mb-6">
          {error}
        </Alert>
      )}

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="Total Jobs"
          value={stats.total_jobs}
          icon={
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          }
        />
        <StatsCard
          title="Total Applications"
          value={stats.total_applications}
          icon={
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        />
        <StatsCard
          title="Total Users"
          value={stats.total_users}
          icon={
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          }
        />
        <StatsCard
          title="Total Evaluations"
          value={stats.total_evaluations}
          icon={
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
        <h2 className="text-xl font-semibold text-slate-900 mb-6 flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <Button variant="primary" onClick={() => navigate("/dashboard/admin/jobs")} className="w-full">
            Manage Jobs
          </Button>
          <Button variant="primary" onClick={() => navigate("/dashboard/admin/applications")} className="w-full">
            Manage Applications
          </Button>
          <Button variant="primary" onClick={() => navigate("/dashboard/admin/users")} className="w-full">
            Manage Users
          </Button>
          <Button variant="primary" onClick={() => navigate("/dashboard/admin/evaluations")} className="w-full">
            View Multi-Source-Evaluations
          </Button>
          <Button variant="primary" onClick={() => navigate("/dashboard/admin/trendscore")} className="w-full">
            View Trend Score
          </Button>
          <Button variant="primary" onClick={() => navigate("/dashboard/admin/turnover/history")} className="w-full">
            View Early Attrition Risk
          </Button>
          {/* Questions */}
          <Link to="/questions/upload" className="w-full">
            <Button variant="primary" className="w-full">
              Upload CV to extract readme
            </Button>
          </Link>
          {/*  */}
          <Link to="/questions/bestproject" className="w-full">
            <Button variant="primary" className="w-full">
              Find best matching project
            </Button>
          </Link>
          <Link to="/questions/clone" className="w-full">
            <Button variant="primary" className="w-full">
              Clone best matching project
            </Button>
          </Link>
          <Link to="/questions/allfiles" className="w-full">
            <Button variant="primary" className="w-full">
              Display all files
            </Button>
          </Link>
          <Link to="/hiring/timeline" className="w-full">
            <Button variant="primary" className="w-full">
              Predict hiring duration
            </Button>
          </Link>
          {/* <Button variant="primary" onClick={() => navigate("/questions/ask")} className="w-full">
            /questions/ask
          </Button> */}
          <Button variant="primary" onClick={() => navigate('/dashboard/admin/scores')} className="w-full">
            Scores View
          </Button>
        </div>
      </div>
    </div>
  );
};
