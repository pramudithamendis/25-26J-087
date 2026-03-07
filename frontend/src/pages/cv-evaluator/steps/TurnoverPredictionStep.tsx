import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Briefcase, Clock, TrendingUp, CheckCircle } from "lucide-react";
import type { CVSubmitResponse, Work } from "../../../types/cv.types";
import { predictTurnover } from "../../../services/turnover-api.service";

interface TurnoverPredictionStepProps {
    cvData?: CVSubmitResponse | null;
    jobId?: string | null;
    jobTitle?: string;
    jobDescription?: string;
    jobLocation?: string;
    userEmail?: string;
    onNext?: () => void;
    onComplete?: () => void;
}

const monthsBetween = (start: string, end: string): number => {
    try {
        const s = new Date(start);
        const e = end.toLowerCase() === 'present' || end === '' ? new Date() : new Date(end);
        return Math.max(0, (e.getFullYear() - s.getFullYear()) * 12 + (e.getMonth() - s.getMonth()));
    } catch {
        return 0;
    }
};

const formatDuration = (months: number): string => {
    if (months < 12) return `${months} month${months !== 1 ? 's' : ''}`;
    const years = (months / 12).toFixed(1);
    return `${years} year${parseFloat(years) !== 1 ? 's' : ''}`;
};

const deriveCareerStats = (work: Work[]) => {
    const validJobs = work.filter(w => w.startDate);
    if (validJobs.length === 0) return null;

    const durations = validJobs.map(w =>
        monthsBetween(w.startDate!, w.endDate || 'present')
    ).filter(d => d > 0);

    const totalMonths = durations.reduce((a, b) => a + b, 0);
    const avgMonths = durations.length > 0 ? Math.round(totalMonths / durations.length) : 0;
    const positions = validJobs.map(w => w.position || '').filter(Boolean);
    const hasProgression = positions.length >= 2;

    return {
        totalMonths,
        avgMonths,
        jobCount: validJobs.length,
        hasProgression,
        latestRole: positions[0] || '',
    };
};

const getCareerPatternText = (stats: ReturnType<typeof deriveCareerStats>): string => {
    if (!stats) return "Your career history has been analysed.";
    const { jobCount, avgMonths, hasProgression, latestRole } = stats;

    if (jobCount === 1) return "Your CV shows focused experience in a single role, indicating strong commitment.";
    if (avgMonths >= 24 && hasProgression) return `Your career shows steady growth${latestRole ? ` in ${latestRole} roles` : ''}, with consistent long-term commitment to each position.`;
    if (avgMonths >= 12) return "Your career history reflects a balanced mix of roles with reasonable tenure at each position.";
    return "Your career shows diverse experience across multiple roles and organisations.";
};

export const TurnoverPredictionStep = ({
    cvData,
    jobId,
    jobTitle,
    jobDescription,
    jobLocation,
    userEmail,
    onNext,
    onComplete,
}: TurnoverPredictionStepProps) => {
    const navigate = useNavigate();
    const email = userEmail || cvData?.data?.user_email || "";
    const cvId = cvData?.data?.cv_id || "";
    const work = cvData?.data?.work || [];
    const name = cvData?.data?.basics?.name || "";

    const missingCV = !email;
    const missingJob = !jobId || !jobTitle || !jobDescription;

    const hasPredicted = useRef(false);
    const [predictionStatus, setPredictionStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');

    useEffect(() => {
        if (missingCV || missingJob || hasPredicted.current || !cvId || !jobDescription) return;

        hasPredicted.current = true;
        setPredictionStatus('running');

        predictTurnover({
            cv_id: cvId,
            job_description: jobDescription,
            job_location: jobLocation,
        })
            .then(() => {
                setPredictionStatus('done');
                onComplete?.();
                // Redirect to jobs page with notification flag after short delay
                setTimeout(() => {
                    navigate('/dashboard/jobs', {
                        state: { notification: 'CV submitted. You will be notified if selected.' }
                    });
                }, 1500);
            })
            .catch(() => {
                setPredictionStatus('error');
                onComplete?.();
                // Still redirect even on error
                setTimeout(() => {
                    navigate('/dashboard/jobs', {
                        state: { notification: 'CV submitted. You will be notified if selected.' }
                    });
                }, 1500);
            });
    }, [cvId, jobDescription]);

    const stats = deriveCareerStats(work);

    if (missingCV || missingJob) {
        return (
            <div className="py-10 flex flex-col items-center gap-4 text-center text-gray-500">
                <AlertCircle size={40} className="text-yellow-500" />
                <div>
                    <p className="font-semibold text-gray-700 text-lg">Missing Information</p>
                    <p className="text-sm mt-1">
                        {missingCV
                            ? "CV data is not available. Please complete Step 1 first."
                            : "Job details are not available. Please complete Step 3 first."}
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div>
            {/* Header */}
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Career Stability Insights</h2>
                <p className="mt-1 text-sm text-gray-500">
                    A summary of your career history and work patterns based on your CV.
                </p>
            </div>

            {/* Context strip */}
            <div className="mb-6 flex flex-wrap gap-3">
                <div className="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-lg px-4 py-2 text-sm">
                    <span className="text-blue-400 font-semibold">CV</span>
                    <span className="text-gray-700 font-medium">{name || email}</span>
                </div>
                <div className="flex items-center gap-2 bg-indigo-50 border border-indigo-100 rounded-lg px-4 py-2 text-sm">
                    <span className="text-indigo-400 font-semibold">Job</span>
                    <span className="text-gray-700 font-medium">{jobTitle}</span>
                </div>
            </div>

            {/* Stats Cards */}
            {stats ? (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-2 shadow-sm">
                        <div className="flex items-center gap-2 text-blue-500">
                            <Briefcase size={18} />
                            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Total Work Experience</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">{formatDuration(stats.totalMonths)}</p>
                    </div>

                    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-2 shadow-sm">
                        <div className="flex items-center gap-2 text-indigo-500">
                            <Clock size={18} />
                            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Average Job Duration</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">{formatDuration(stats.avgMonths)}</p>
                    </div>

                    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-2 shadow-sm">
                        <div className="flex items-center gap-2 text-green-500">
                            <TrendingUp size={18} />
                            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">Positions Held</span>
                        </div>
                        <p className="text-2xl font-bold text-gray-900">{stats.jobCount}</p>
                    </div>
                </div>
            ) : (
                <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-xl text-sm text-gray-500 text-center">
                    No work experience data found in your CV.
                </div>
            )}

            {/* Career Pattern */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-5 mb-6">
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-400 mb-1">Career Pattern</p>
                <p className="text-gray-700 text-sm leading-relaxed">{getCareerPatternText(stats)}</p>
            </div>

            {/* Prediction status */}
            <div className="flex items-center gap-2 text-xs text-gray-400">
                {predictionStatus === 'running' && (
                    <>
                        <div className="w-3 h-3 border-2 border-gray-300 border-t-blue-400 rounded-full animate-spin" />
                        <span>Finalising your profile analysis...</span>
                    </>
                )}
                {predictionStatus === 'done' && (
                    <>
                        <CheckCircle size={14} className="text-green-400" />
                        <span>Profile analysis complete. Redirecting...</span>
                    </>
                )}
                {predictionStatus === 'error' && (
                    <span>Profile analysis could not be completed. Redirecting...</span>
                )}
            </div>
        </div>
    );
};