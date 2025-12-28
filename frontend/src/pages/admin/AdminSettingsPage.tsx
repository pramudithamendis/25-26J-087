import { useState, useEffect, FormEvent } from 'react';
import { Button } from '../../components/Button';
import { Input } from '../../components/Input';
import { Alert } from '../../components/Alert';
import { LoadingSpinner } from '../../components/shared/LoadingSpinner';
import { getSettings, updateSettings } from '../../services/adminService';
import type { SystemSettings } from '../../types/adminTypes';

export const AdminSettingsPage = () => {
  const [settings, setSettings] = useState<SystemSettings>({
    evaluation_threshold_selected: 75,
    evaluation_threshold_review: 60,
    email_notifications_enabled: true,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getSettings();
      setSettings(response.settings);
    } catch (err: any) {
      setError(err.detail || 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setError(null);
      await updateSettings(settings);
      setSuccess('Settings updated successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.detail || 'Failed to update settings');
    } finally {
      setSaving(false);
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
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Admin - System Settings</h1>
        <p className="text-gray-600 mt-1">Configure system-wide settings</p>
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

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Evaluation Thresholds */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Evaluation Thresholds</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Score for "Selected" (0-100)
                </label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={settings.evaluation_threshold_selected}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      evaluation_threshold_selected: parseInt(e.target.value) || 75,
                    })
                  }
                  required
                />
                <p className="mt-1 text-sm text-gray-500">
                  Candidates with scores at or above this threshold will be marked as "Selected"
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Minimum Score for "Review" (0-100)
                </label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  value={settings.evaluation_threshold_review}
                  onChange={(e) =>
                    setSettings({
                      ...settings,
                      evaluation_threshold_review: parseInt(e.target.value) || 60,
                    })
                  }
                  required
                />
                <p className="mt-1 text-sm text-gray-500">
                  Candidates with scores at or above this threshold (but below Selected) will be marked as "Review"
                </p>
              </div>
            </div>
          </div>

          {/* Email Notifications */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Email Notifications</h3>
            <div className="flex items-center">
              <input
                type="checkbox"
                id="email_notifications"
                checked={settings.email_notifications_enabled}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    email_notifications_enabled: e.target.checked,
                  })
                }
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="email_notifications" className="ml-2 block text-sm text-gray-900">
                Enable email notifications
              </label>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Send email notifications for important events (new applications, evaluation completions, etc.)
            </p>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end pt-4 border-t border-gray-200">
            <Button type="submit" variant="primary" isLoading={saving} disabled={saving}>
              Save Settings
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

