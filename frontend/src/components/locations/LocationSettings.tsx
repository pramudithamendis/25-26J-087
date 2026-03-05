import React, { useState, useEffect } from 'react';
import { MapPin, Plus, Trash2, Loader2, Building2, AlertCircle, CheckCircle2 } from 'lucide-react';
import apiClient from '../../config/api';
import './LocationSettings.css';

interface Location {
  _id: string;
  name: string;
  created_at: string;
}

const LocationSettings: React.FC = () => {
  const [locations, setLocations] = useState<Location[]>([]);
  const [loading, setLoading] = useState(true);
  const [newLocation, setNewLocation] = useState('');
  const [adding, setAdding] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchLocations();
  }, []);

  const fetchLocations = async () => {
    try {
      const res = await apiClient.get('/locations');
      setLocations(res.data.locations || []);
    } catch (e) {
      setError('Failed to load locations');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    const name = newLocation.trim();
    if (!name) return;
    setAdding(true);
    setError('');
    setSuccess('');
    try {
      const res = await apiClient.post('/locations', { name });
      setLocations(prev => [...prev, res.data.location].sort((a, b) => a.name.localeCompare(b.name)));
      setNewLocation('');
      setSuccess(`"${name}" added successfully`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to add location');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Remove "${name}" from branch locations?`)) return;
    setDeletingId(id);
    setError('');
    try {
      await apiClient.delete(`/locations/${id}`);
      setLocations(prev => prev.filter(l => l._id !== id));
      setSuccess(`"${name}" removed`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to delete location');
    } finally {
      setDeletingId(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleAdd();
  };

  return (
    <div className="ls-container">
      <div className="ls-header">
        <div className="ls-header-icon">
          <Building2 size={22} />
        </div>
        <div>
          <h2>Branch Locations</h2>
          <p>Manage the office locations available when running early attrition risk assessments</p>
        </div>
      </div>

      {/* Add new location */}
      <div className="ls-add-card">
        <label className="ls-label">
          <MapPin size={14} />
          Add New Location
        </label>
        <div className="ls-add-row">
          <input
            className="ls-input"
            type="text"
            placeholder="e.g. Kandy, Sri Lanka"
            value={newLocation}
            onChange={e => setNewLocation(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={adding}
          />
          <button
            className="ls-add-btn"
            onClick={handleAdd}
            disabled={adding || !newLocation.trim()}
          >
            {adding ? <Loader2 size={16} className="ls-spin" /> : <Plus size={16} />}
            Add
          </button>
        </div>
        <small className="ls-hint">Include ", Sri Lanka" at the end for accurate geocoding</small>
      </div>

      {/* Feedback */}
      {error && (
        <div className="ls-alert ls-alert-error">
          <AlertCircle size={15} />
          {error}
        </div>
      )}
      {success && (
        <div className="ls-alert ls-alert-success">
          <CheckCircle2 size={15} />
          {success}
        </div>
      )}

      {/* Locations list */}
      <div className="ls-list-card">
        <div className="ls-list-header">
          <span>Current Locations</span>
          <span className="ls-count">{locations.length} locations</span>
        </div>

        {loading ? (
          <div className="ls-loading">
            <Loader2 size={20} className="ls-spin" />
            Loading locations...
          </div>
        ) : locations.length === 0 ? (
          <div className="ls-empty">No locations configured</div>
        ) : (
          <div className="ls-list">
            {locations.map(loc => (
              <div key={loc._id} className="ls-list-item">
                <div className="ls-item-left">
                  <MapPin size={14} className={loc.name === 'Remote' ? 'ls-icon-remote' : 'ls-icon-pin'} />
                  <span className="ls-item-name">{loc.name}</span>
                  {loc.name === 'Remote' && <span className="ls-badge-remote">Remote</span>}
                </div>
                <button
                  className="ls-delete-btn"
                  onClick={() => handleDelete(loc._id, loc.name)}
                  disabled={deletingId === loc._id}
                  title="Remove location"
                >
                  {deletingId === loc._id
                    ? <Loader2 size={14} className="ls-spin" />
                    : <Trash2 size={14} />
                  }
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="ls-info">
        <AlertCircle size={13} />
        <p>These locations appear as options when running early attrition risk assessments. 
          Accurate location names improve commute distance calculations.</p>
      </div>
    </div>
  );
};

export default LocationSettings;