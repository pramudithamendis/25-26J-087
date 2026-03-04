import { useState } from "react";
import { uploadCV } from "../../../services/cv.service";
import { FileIcon, UploadCloudIcon, XIcon } from "lucide-react";
import type { CVSubmitResponse } from "../../../types/cv.types";

interface UploadCVStepProps {
    onUploadSuccess?: (response: CVSubmitResponse) => void;
    onFileUploaded?: (file: File) => void;
    onNext?: () => void;
}

export const UploadCVStep = ({ onUploadSuccess, onFileUploaded, onNext }: UploadCVStepProps) => {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [dragActive, setDragActive] = useState(false);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            validateAndSetFile(selectedFile);
        }
    };

    const validateAndSetFile = (selectedFile: File) => {
        // Check file type
        const validTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
        if (!validTypes.includes(selectedFile.type)) {
            setError('Please upload a PDF or DOC file');
            return;
        }

        // Check file size (max 5MB)
        if (selectedFile.size > 5 * 1024 * 1024) {
            setError('File size should be less than 5MB');
            return;
        }

        setFile(selectedFile);
        setError('');
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        const droppedFile = e.dataTransfer.files?.[0];
        if (droppedFile) {
            validateAndSetFile(droppedFile);
        }
    };

    const handleSubmit = async () => {
        if (!file) {
            setError('Please select a CV file');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const response = await uploadCV(file);
            console.log('CV uploaded successfully:', response);

            if (onUploadSuccess) {
                onUploadSuccess(response);
            }

            if (onFileUploaded && file) {
                onFileUploaded(file);
            }

            if (onNext) {
                onNext();
            }
        } catch (err: any) {
            setError(err.message || 'CV upload failed');
        } finally {
            setLoading(false);
        }
    };

    const removeFile = () => {
        setFile(null);
    };

    const formatFileSize = (bytes: number) => {
        if (bytes < 1024) return bytes + ' bytes';
        else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
        else return (bytes / 1048576).toFixed(1) + ' MB';
    };

    return (
        <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Upload Your CV</h2>
                <p className="text-gray-600 mb-6">
                    Upload your CV and we'll automatically extract and analyze your information
                </p>

                {/* File Upload Area */}
                <div
                    className={`relative border-2 border-dashed rounded-lg p-8 transition-colors ${dragActive
                        ? 'border-blue-500 bg-blue-50'
                        : file
                            ? 'border-green-500 bg-green-50'
                            : 'border-gray-300 hover:border-gray-400'
                        }`}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                >
                    <input
                        type="file"
                        id="cv-upload"
                        className="hidden"
                        accept=".pdf,.doc,.docx"
                        onChange={handleFileChange}
                    />

                    {!file ? (
                        <div className="text-center">
                            <UploadCloudIcon className="mx-auto h-12 w-12 text-gray-400" />
                            <label
                                htmlFor="cv-upload"
                                className="mt-4 cursor-pointer inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                            >
                                Select CV File
                            </label>
                            <p className="mt-2 text-sm text-gray-500">
                                or drag and drop your file here
                            </p>
                            <p className="mt-1 text-xs text-gray-400">
                                Supported formats: PDF, DOC, DOCX (Max 5MB)
                            </p>
                        </div>
                    ) : (
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                                <FileIcon className="h-8 w-8 text-green-600" />
                                <div>
                                    <p className="text-sm font-medium text-gray-900">{file.name}</p>
                                    <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                                </div>
                            </div>
                            <button
                                onClick={removeFile}
                                className="p-1 hover:bg-gray-200 rounded-full transition-colors"
                            >
                                <XIcon className="h-5 w-5 text-gray-500" />
                            </button>
                        </div>
                    )}
                </div>

                {/* Error Message */}
                {error && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                        <p className="text-sm text-red-600">{error}</p>
                    </div>
                )}

                {/* Submit Button */}
                <div className="mt-6">
                    <button
                        onClick={handleSubmit}
                        disabled={!file || loading}
                        className={`w-full py-3 px-4 rounded-md text-white font-medium transition-colors ${!file || loading
                            ? 'bg-gray-400 cursor-not-allowed'
                            : 'bg-blue-600 hover:bg-blue-700'
                            }`}
                    >
                        {loading ? (
                            <div className="flex items-center justify-center">
                                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Uploading...
                            </div>
                        ) : (
                            'Upload and Analyze CV'
                        )}
                    </button>
                </div>

                {/* File Requirements */}
                <div className="mt-4 text-xs text-gray-400 text-center">
                    <p>Your CV will be securely processed and analyzed</p>
                </div>
            </div>
        </div>
    );
};