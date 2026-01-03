import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/Button';
import { useNavigate } from 'react-router-dom';

export const Home = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-100">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Welcome, {user?.email}!
              </h1>
              <p className="text-gray-600">
                You are successfully authenticated.
              </p>
            </div>
            <Button variant="outline" onClick={handleLogout}>
              Logout
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="p-6 bg-blue-50 rounded-lg border border-blue-100">
              <h3 className="text-lg font-semibold text-blue-900 mb-2">
                User Information
              </h3>
              <div className="space-y-2 text-sm text-blue-700">
                <p><span className="font-medium">Email:</span> {user?.email}</p>
                <p><span className="font-medium">Role:</span> {user?.role}</p>
              </div>
            </div>

            <div className="p-6 bg-purple-50 rounded-lg border border-purple-100">
              <h3 className="text-lg font-semibold text-purple-900 mb-2">
                Quick Actions
              </h3>
              <p className="text-sm text-purple-700">
                Your dashboard content will appear here.
              </p>
            </div>

            <div className="p-6 bg-green-50 rounded-lg border border-green-100">
              <h3 className="text-lg font-semibold text-green-900 mb-2">
                Status
              </h3>
              <p className="text-sm text-green-700">
                Authentication is working correctly!
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

