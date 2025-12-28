import { useState, useRef } from 'react';
import { Button } from '../Button';
import { LoadingSpinner } from '../shared/LoadingSpinner';

interface FileUploadProps {
  label: string;
  accept?: string;
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}

export const FileUpload = ({
  label,
  accept = '.pdf',
  onUpload,
  disabled = false,
}: FileUploadProps) => {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError(null);
    setUploading(true);

    try {
      await onUpload(file);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err: any) {
      setError(err.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        {label}
      </label>
      <div className="flex items-center gap-4">
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleFileSelect}
          disabled={disabled || uploading}
          className="hidden"
          id={`file-upload-${label.replace(/\s+/g, '-')}`}
        />
        <label
          htmlFor={`file-upload-${label.replace(/\s+/g, '-')}`}
          className={`flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
            disabled || uploading ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {uploading ? (
            <>
              <LoadingSpinner size="sm" />
              <span className="text-sm text-gray-600">Uploading...</span>
            </>
          ) : (
            <>
              <svg
                className="w-5 h-5 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <span className="text-sm text-gray-600">Choose File</span>
            </>
          )}
        </label>
        <span className="text-sm text-gray-500">
          {accept === '.pdf' ? 'PDF only' : accept}
        </span>
      </div>
      {error && (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
};

