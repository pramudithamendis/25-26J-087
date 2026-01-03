import { useAuth } from '../../contexts/AuthContext';

export const TopNav = () => {
  const { user } = useAuth();

  return (
    <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold text-gray-900">CV Analysis System</h2>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-sm text-gray-600">
          <span className="font-medium">{user?.email}</span>
        </div>
      </div>
    </div>
  );
};

