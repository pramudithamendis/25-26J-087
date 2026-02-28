import { useState, useEffect } from 'react';
import { Table } from '../../components/shared/Table';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Alert } from '../../components/Alert';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { listAllUsers, exportUsers } from '../../services/adminService';
import type { UserListItem } from '../../types/adminTypes';

export const AdminUsersPage = () => {
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Filters
  const [roleFilter, setRoleFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [skip, setSkip] = useState(0);
  const [limit] = useState(50);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    loadUsers();
  }, [roleFilter, searchQuery, skip]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await listAllUsers({
        role: roleFilter || undefined,
        search: searchQuery || undefined,
        skip,
        limit,
      });
      setUsers(response.users);
      setTotalCount(response.count);
    } catch (err: any) {
      setError(err.detail || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      const blob = await exportUsers();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'users.csv';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setSuccess('Users exported successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.detail || 'Failed to export users');
    }
  };

  const columns = [
    { key: 'email', header: 'Email' },
    {
      key: 'name',
      header: 'Name',
      render: (user: UserListItem) => (
        <span>
          {user.first_name || ''} {user.last_name || ''}
        </span>
      ),
    },
    {
      key: 'role',
      header: 'Role',
      render: (user: UserListItem) => (
        <span className="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 capitalize">
          {user.role}
        </span>
      ),
    },
    { key: 'city', header: 'City' },
    {
      key: 'created_at',
      header: 'Registered',
      render: (user: UserListItem) => (
        <span>{user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</span>
      ),
    },
  ];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Admin - Users Management</h1>
          <p className="text-gray-600 mt-1">View all registered users</p>
        </div>
        <Button variant="primary" onClick={handleExport}>
          Export CSV
        </Button>
      </div>

      {error && (
        <Alert type="error" onClose={() => setError(null)} className="mb-6">
          {error}
        </Alert>
      )}

      {success && (
        <Alert type="success" onClose={() => setSuccess(null)} className="mb-6">
          {success}
        </Alert>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Search</label>
            <Input
              type="text"
              placeholder="Search by email or name..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setSkip(0);
              }}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Filter by Role</label>
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setSkip(0);
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            >
              <option value="">All Roles</option>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <LoadingSpinner size="lg" />
          </div>
        ) : (
          <>
            <Table
              columns={columns}
              data={users}
              emptyMessage="No users found"
            />
            {totalCount > limit && (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  Showing {skip + 1} to {Math.min(skip + limit, totalCount)} of {totalCount} users
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSkip(Math.max(0, skip - limit))}
                    disabled={skip === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSkip(skip + limit)}
                    disabled={skip + limit >= totalCount}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

