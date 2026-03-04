import { useState, useEffect } from "react";
import { AlertCircle, Briefcase, CheckCircle, FileUp, Loader2, Upload, XCircle } from "lucide-react";
import { applyToJob} from "../../../services/applicationService";
import type { CVSubmitResponse } from "../../../types/cv.types";
import { useParams } from "react-router-dom";
import type { ApplicationData } from "../../../types/applicationTypes";
import type { ApplyToJobResponse } from "../../../services/jobService";

interface JobEvaluationStepProps {
    cvData?: CVSubmitResponse | null;
    cvFile?: File | null;
    onNext?: () => void;
    onComplete?: () => void;
}

export const JobEvaluationStep = ({ cvData, cvFile, onNext, onComplete }: JobEvaluationStepProps) => {
    const { jobId } = useParams<{ jobId: string }>();
    const [selectedJobId, setSelectedJobId] = useState<string | null>(jobId || null);
    const [linkedinFile, setLinkedinFile] = useState<File | null>(null);
    const [applying, setApplying] = useState(false);
    const [error, setError] = useState('');
    const [result, setResult] = useState<ApplyToJobResponse | null>(null);

    // If jobId exists in URL, we don't need to fetch jobs
    const hasJobIdInUrl = !!jobId;

    useEffect(() => {
        if (jobId) {
            setSelectedJobId(jobId);
        }
    }, [jobId]);

    const handleLinkedinUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (file.size > 5 * 1024 * 1024) {
                setError('LinkedIn PDF must be less than 5MB');
                return;
            }
            setLinkedinFile(file);
            setError('');
        }
    };

    const handleApply = async () => {
        if (!selectedJobId) {
            setError('No job selected');
            return;
        }

        setApplying(true);
        setError('');

          const applicationData: ApplicationData = {
                first_name: cvData?.data.basics?.name?.split(' ')[0] || '',
                last_name: cvData?.data.basics?.name?.split(' ')[1] || '',
                city: cvData?.data.basics?.address || '',
                phone_number: cvData?.data.basics?.phone || undefined,
                // Always include URLs (even if empty string) so they're saved/updated in profile
                github_url: cvData?.data.basics?.github || '',
                linkedin_url: cvData?.data.basics?.linkedin || '',
                resume: cvFile || undefined,
                linkedin_resume: linkedinFile || undefined,
              };


        try {
            const response = await applyToJob(
                selectedJobId,
                applicationData
            );
            setResult(response);
            if (onComplete) onComplete();
        } catch (err: any) {
            setError(err.detail || err.message || 'Application failed');
        } finally {
            setApplying(false);
        }
    };

    const handleContinue = () => {
        if (onNext) onNext();
    };

    if (!cvData) {
        return (
            <div className="text-center py-12">
                <AlertCircle className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-500">No CV data available. Please upload a CV first.</p>
            </div>
        );
    }

    // Show result after successful application
    if (result) {
        return (
            <div className="max-w-2xl mx-auto">
                <div className="text-center py-8">
                    <CheckCircle className="mx-auto h-16 w-16 text-green-500 mb-4" />
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">Application Submitted!</h2>
                    <p className="text-gray-600 mb-6">{result.message}</p>

                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 inline-block text-left">
                        <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                            <span className="text-gray-500">Application ID:</span>
                            <span className="font-mono text-gray-800">{result.application_id}</span>
                            <span className="text-gray-500">Status:</span>
                            <span className="capitalize font-medium text-blue-600">{result.status}</span>
                        </div>
                    </div>

                    <p className="text-gray-500 text-sm mb-6">
                        Your CV is being evaluated against the job description. This happens in the background.
                    </p>

                    <button
                        onClick={handleContinue}
                        className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium flex items-center gap-2 mx-auto transition-colors"
                    >
                        <CheckCircle className="h-5 w-5" />
                        Continue to Next Step
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Job Match Evaluation</h2>
                <p className="text-gray-600">
                    {hasJobIdInUrl 
                        ? "Your CV will be evaluated against the specified job."
                        : "Select a job to evaluate your CV against. Your previously uploaded CV will be automatically submitted."
                    }
                </p>
            </div>

            {/* CV File Status */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6 flex items-center gap-2">
                <FileUp className="h-5 w-5 text-blue-600 flex-shrink-0" />
                <span className="text-sm text-blue-800">
                    {cvFile
                        ? <>CV file attached: <span className="font-medium">{cvFile.name}</span></>
                        : 'CV data will be used from your profile'
                    }
                </span>
            </div>

            {/* Job ID Display (when from URL) */}
            {hasJobIdInUrl && (
                <div className="mb-6">
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center gap-3">
                            <Briefcase className="h-5 w-5 text-gray-500" />
                            <div>
                                <p className="text-sm text-gray-500">Job ID from URL</p>
                                <p className="font-mono text-sm text-gray-800">{jobId}</p>
                            </div>
                            <CheckCircle className="h-5 w-5 text-green-500 ml-auto" />
                        </div>
                    </div>
                </div>
            )}

            {/* LinkedIn Upload (Optional) */}
            <div className="mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    LinkedIn PDF <span className="text-gray-400 text-sm font-normal">(Optional)</span>
                </h3>
                <p className="text-gray-500 text-sm mb-3">
                    Upload your LinkedIn profile PDF for a more comprehensive evaluation.
                </p>

                {linkedinFile ? (
                    <div className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg p-3">
                        <div className="flex items-center gap-2">
                            <FileUp className="h-5 w-5 text-green-600" />
                            <span className="text-sm font-medium text-green-800">{linkedinFile.name}</span>
                            <span className="text-xs text-green-600">
                                ({(linkedinFile.size / 1024).toFixed(1)} KB)
                            </span>
                        </div>
                        <button
                            onClick={() => setLinkedinFile(null)}
                            className="p-1 hover:bg-green-100 rounded-full transition-colors"
                        >
                            <XCircle className="h-4 w-4 text-green-600" />
                        </button>
                    </div>
                ) : (
                    <label className="flex items-center justify-center gap-2 p-4 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-gray-400 hover:bg-gray-50 transition-colors">
                        <Upload className="h-5 w-5 text-gray-400" />
                        <span className="text-gray-500 text-sm">Click to upload LinkedIn PDF</span>
                        <input
                            type="file"
                            accept=".pdf"
                            onChange={handleLinkedinUpload}
                            className="hidden"
                        />
                    </label>
                )}
            </div>

            {/* Error */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-6 flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
                    <p className="text-red-700 text-sm">{error}</p>
                </div>
            )}

            {/* Apply Button */}
            <div className="flex justify-end">
                <button
                    onClick={handleApply}
                    disabled={!selectedJobId || applying}
                    className={`px-6 py-3 rounded-lg font-medium flex items-center gap-2 transition-colors ${!selectedJobId || applying
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-blue-600 text-white hover:bg-blue-700'
                        }`}
                >
                    {applying ? (
                        <>
                            <Loader2 className="h-5 w-5 animate-spin" />
                            Submitting Application...
                        </>
                    ) : (
                        <>
                            <Briefcase className="h-5 w-5" />
                            {hasJobIdInUrl ? 'Evaluate Against Job' : 'Apply to Job'}
                        </>
                    )}
                </button>
            </div>
        </div>
    );
};