import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, AlertCircle, ArrowRight, History } from 'lucide-react';
import { uploadCV } from '../../services/cv.service';
import type { CVSubmitResponse } from '../../types/cv.types';
import './CVUpload.css';

const CVUpload: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
 
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<CVSubmitResponse | null>(null);
  const [error, setError] = useState('');

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      // Validate file type
      const validTypes = ['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
      if (!validTypes.includes(selectedFile.type)) {
        setError('Only PDF files are supported');
        return;
      }

      // Validate file size (max 10MB)
      if (selectedFile.size > 10 * 1024 * 1024) {
        setError('File size must be less than 10MB');
        return;
      }

      setFile(selectedFile);
      setError('');
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError('');

    try {
      const result = await uploadCV(file);
      setUploadResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleModuleNavigation = (path: string) => {
    if (uploadResult) {
      navigate(`${path}?cv_id=${uploadResult.cv_id}`);
    }
  };

  const handleReset = () => {
    setFile(null);
    setUploadResult(null);
    setError('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="cv-upload-container">
      <div className="cv-upload-card">
        {/* Header with History Button */}
        <div className="upload-header">
          <FileText className="header-icon" style={{ color: '#2563eb' }}/>
          <div style={{ flex: 1 }}>
            <h1>Upload Your CV</h1>
            <p>Upload your resume to begin the analysis</p>
          </div>
          <button
            onClick={() => navigate('/dashboard/admin/turnover/history')}
            className="history-button"
            title="View Prediction History"
          >
            <History size={20} />
            History
          </button>
        </div>

        {!uploadResult ? (
          <>
            {/* File Drop Zone */}
            <div
              className={`drop-zone ${file ? 'has-file' : ''}`}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.docx"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
             
              {file ? (
                <div className="file-info">
                  <FileText size={48} />
                  <p className="file-name">{file.name}</p>
                  <p className="file-size">{(file.size / 1024).toFixed(2)} KB</p>
                </div>
              ) : (
                <div className="upload-prompt">
                  <Upload size={48} />
                  <p>Click to browse</p>
                  <small>PDF (max 10MB)</small>
                </div>
              )}
            </div>

            {/* Error Message */}
            {error && (
              <div className="error-message">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            {/* Upload Button */}
            {file && (
              <div className="upload-actions">
                <button
                  onClick={handleReset}
                  className="reset-button"
                  disabled={uploading}
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  className="upload-button"
                  disabled={uploading}
                >
                  {uploading ? (
                    <>
                      <div className="spinner"></div>
                      Parsing CV...
                    </>
                  ) : (
                    <>
                      <Upload size={18} />
                      Upload
                    </>
                  )}
                </button>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Success Message */}
            <div className="success-card">
              <CheckCircle className="success-icon" />
              <h2>CV Uploaded Successfully!</h2>
              <p className="cv-name">
                Candidate: <strong>{uploadResult.parsed_data.name || 'Unknown'}</strong>
              </p>

              {/* Module Navigation */}
              <div className="module-navigation">
                
                <div className="module-buttons">
                  <button
                    onClick={() => handleModuleNavigation('/dashboard/admin/turnover')}
                    className="module-button turnover"
                  >
                    <span>Turnover Risk Assessment</span>
                    <ArrowRight size={18} />
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default CVUpload;