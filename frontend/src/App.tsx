import QuestionsCVUpload from "./Questions/QuestionsCVUpload";
import QuestionsFindBestProject from "./Questions/QuestionsFindBestProject";
import QuestionsClone from "./Questions/QuestionsClone";
import QuestionsAllFiles from "./Questions/QuestionsAllFiles";
import QuestionsAsk from "./Questions/QuestionsAsk";
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AdminRoute } from './components/AdminRoute';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { ProfilePage } from './pages/ProfilePage';
import { JobsPage } from './pages/JobsPage';
import { JobDetailPage } from './pages/JobDetailPage';
import { JobApplicationPage } from './pages/JobApplicationPage';
import { ApplicationConfirmationPage } from './pages/ApplicationConfirmationPage';
import { EvaluationDetailPage } from './pages/EvaluationDetailPage';
import { AdminDashboard } from './pages/admin/AdminDashboard';
import { AdminJobsPage } from './pages/admin/AdminJobsPage';
import { AdminApplicationsPage } from './pages/admin/AdminApplicationsPage';
import { AdminUsersPage } from './pages/admin/AdminUsersPage';
import { AdminEvaluationsPage } from './pages/admin/AdminEvaluationsPage';
import { JobApplicantsPage } from './pages/admin/JobApplicantsPage';
import { JobApplicantDetailPage } from './pages/admin/JobApplicantDetailPage';
import { AdminTrendScorePage } from './pages/admin/AdminTrendScorePage'
import './App.css';
function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <Dashboard />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/profile"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <ProfilePage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/jobs"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <JobsPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/jobs/:jobId"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <JobDetailPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/jobs/:jobId/apply"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <JobApplicationPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/jobs/:jobId/apply/confirmation"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <ApplicationConfirmationPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard/evaluations/:evaluationId"
            element={
              <ProtectedRoute>
                <DashboardLayout>
                  <EvaluationDetailPage />
                </DashboardLayout>
              </ProtectedRoute>
            }
          />
          {/* Admin Routes */}
          <Route
            path="/dashboard/admin"
            element={
              <AdminRoute>
                <DashboardLayout>
                  <AdminDashboard />
                </DashboardLayout>
              </AdminRoute>
            }
          />
          <Route
            path="/dashboard/admin/jobs"
            element={
              <AdminRoute>
                <DashboardLayout>
                  <AdminJobsPage />
                </DashboardLayout>
              </AdminRoute>
            }
          />
          <Route
            path="/dashboard/admin/jobs/:jobId/applicants"
            element={
              <AdminRoute>
                <DashboardLayout>
                  <JobApplicantsPage />
                </DashboardLayout>
              </AdminRoute>
            }
          />
          <Route
            path="/dashboard/admin/jobs/:jobId/applicants/:applicationId"
            element={
              <AdminRoute>
                <DashboardLayout>
                  <JobApplicantDetailPage />
                </DashboardLayout>
              </AdminRoute>
            }
          />
          <Route
            path="/dashboard/admin/applications"
            element={
              <AdminRoute>
                <DashboardLayout>
                  <AdminApplicationsPage />
                </DashboardLayout>
              </AdminRoute>
            }
          />
          <Route
            path="/dashboard/admin/users"
            element={
              <AdminRoute>
                <DashboardLayout>
                  <AdminUsersPage />
                </DashboardLayout>
              </AdminRoute>
            }
          />
          <Route
            path="/dashboard/admin/evaluations"
            element={
              <AdminRoute>
                <DashboardLayout>
                  <AdminEvaluationsPage />
                </DashboardLayout>
              </AdminRoute>
            }
          />
           <Route
            path="/dashboard/admin/trendscore"
            element={
              <AdminRoute>
                <DashboardLayout>
                  <AdminTrendScorePage />
                </DashboardLayout>
              </AdminRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Navigate to="/dashboard" replace />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
          <Route path="/questions/upload" element={<QuestionsCVUpload />} />
          <Route path="/questions/bestproject" element={<QuestionsFindBestProject />} />
          <Route path="/questions/clone" element={<QuestionsClone />} />
          <Route path="/questions/allfiles" element={<QuestionsAllFiles />} />
          <Route path="/questions/ask" element={<QuestionsAsk />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
