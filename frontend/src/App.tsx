import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AuthForm from './components/auth/AuthForm';
import CVUpload from './components/cv/CVUpload';
import TurnoverDashboard from './components/turnover/TurnoverDashboard';
import TurnoverHistoryPage from './components/turnover/TurnoverHistoryPage';
import TurnoverResultsView from './components/turnover/TurnoverResultsView';
import { isAuthenticated } from './services/auth.service';

// Protected Route wrapper
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ============================================ */}
        {/* PUBLIC ROUTES */}
        {/* ============================================ */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<AuthForm />} />
        <Route path="/register" element={<AuthForm />} />

        {/* ============================================ */}
        {/* SHARED ROUTES*/}
        {/* ============================================ */}
        <Route
          path="/cv/upload"
          element={
            <ProtectedRoute>
              <CVUpload />
            </ProtectedRoute>
          }
        />

        {/* ============================================ */}
        {/* TURNOVER PREDICTION */}
        {/* ============================================ */}
        <Route
          path="/turnover"
          element={
            <ProtectedRoute>
              <TurnoverDashboard />
            </ProtectedRoute>
          }
        />
        
        <Route
          path="/turnover/history"
          element={
            <ProtectedRoute>
              <TurnoverHistoryPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/turnover/results"
          element={
            <ProtectedRoute>
              <TurnoverResultsView />
            </ProtectedRoute>
          }
        />


        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
