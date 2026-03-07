import { useState, useEffect } from 'react';
import { Button } from '../components/Button';
import { FileUpload } from '../components/candidates/FileUpload';
import { ProfileForm } from '../components/profile/ProfileForm';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/shared/LoadingSpinner';
import {
  getCurrentUserProfile,
  updateProfile,
  uploadUserCV,
  uploadLinkedIn,
} from '../services/userService';
import { useAuth } from '../contexts/AuthContext';
import type { User } from '../types/auth';
import type { UserUpdate } from '../services/userService';

export const ProfilePage = () => {
  const { user: authUser, setUser } = useAuth();
  const isAdmin = authUser?.role === 'admin';
  const [user, setUserState] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getCurrentUserProfile();
      setUserState(data);
      // Update auth context with latest user data
      if (setUser) {
        setUser(data);
      }
    } catch (err: any) {
      setError(err.detail || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (data: UserUpdate) => {
    try {
      setIsUpdating(true);
      const updated = await updateProfile(data);
      setUserState(updated);
      // Update auth context
      if (setUser) {
        setUser(updated);
      }
      setIsEditing(false);
    } catch (err: any) {
      setError(err.detail || 'Failed to update profile');
      throw err;
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCVUpload = async (file: File) => {
    await uploadUserCV(file);
    await loadProfile();
  };

  const handleLinkedInUpload = async (file: File) => {
    await uploadLinkedIn(file);
    await loadProfile();
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!user) {
    return (
      <div>
        <Alert type="error">{error || 'Failed to load profile'}</Alert>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Profile</h1>
        <p className="text-gray-600 mt-1">
          {isAdmin ? 'View your profile information' : 'Manage your profile information and upload documents'}
        </p>
      </div>

      {error && (
        <Alert type="error" onClose={() => setError(null)} className="mb-6">
          {error}
        </Alert>
      )}

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">
            Profile Information
          </h2>
          {!isAdmin && (
            <Button
              variant={isEditing ? 'outline' : 'primary'}
              onClick={() => setIsEditing(!isEditing)}
            >
              {isEditing ? 'Cancel Edit' : 'Edit Profile'}
            </Button>
          )}
        </div>

        {isEditing ? (
          <ProfileForm
            user={user}
            onSubmit={handleUpdate}
            onCancel={() => setIsEditing(false)}
            isLoading={isUpdating}
          />
        ) : (
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Email</h3>
              <p className="text-gray-900">{user.email}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-1">Role</h3>
              <p className="text-gray-900 capitalize">{user.role}</p>
            </div>
            {user.name && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">Name</h3>
                <p className="text-gray-900">{user.name}</p>
              </div>
            )}
            {user.github_handle && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">
                  GitHub Handle
                </h3>
                <p className="text-gray-900">{user.github_handle}</p>
              </div>
            )}
            {user.github_url && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">
                  GitHub URL
                </h3>
                <p className="text-gray-900">
                  <a
                    href={user.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 underline"
                  >
                    {user.github_url}
                  </a>
                </p>
              </div>
            )}
            {user.linkedin_url && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-1">
                  LinkedIn URL
                </h3>
                <p className="text-gray-900">
                  <a
                    href={user.linkedin_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 underline"
                  >
                    {user.linkedin_url}
                  </a>
                </p>
              </div>
            )}

            {!isAdmin && (
              <div className="pt-6 border-t border-gray-200 space-y-4">
                <h3 className="text-lg font-semibold text-gray-900">
                  Upload Documents
                </h3>
                <FileUpload
                  label="CV (PDF)"
                  onUpload={handleCVUpload}
                  disabled={!user}
                />
                {user.cv_file_path && (
                  <p className="text-sm text-green-600">
                    ✓ CV uploaded: {user.cv_file_path.split('/').pop()}
                  </p>
                )}
                <FileUpload
                  label="LinkedIn Profile (PDF)"
                  onUpload={handleLinkedInUpload}
                  disabled={!user}
                />
                {user.linkedin_file_path && (
                  <p className="text-sm text-green-600">
                    ✓ LinkedIn uploaded:{' '}
                    {user.linkedin_file_path.split('/').pop()}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

