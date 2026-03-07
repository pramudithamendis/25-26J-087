import { AlertCircle } from "lucide-react";
import type { CVSubmitResponse } from "../../../types/cv.types";
import { TurnoverRiskTabSafe } from "../../../components/turnover/TurnoverRiskTab";

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
    // Derive email: prefer explicitly passed userEmail, fall back to CV data
    const email = userEmail || cvData?.data?.user_email || "";

    const missingCV = !email;
    const missingJob = !jobId || !jobTitle || !jobDescription;

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
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Turnover Risk Prediction</h2>
                <p className="mt-1 text-sm text-gray-500">
                    Assess the likelihood of early attrition based on your CV profile and the
                    selected job description.
                </p>
            </div>

            {/* Context summary strip */}
            <div className="mb-6 flex flex-wrap gap-3">
                <div className="flex items-center gap-2 bg-blue-50 border border-blue-100 rounded-lg px-4 py-2 text-sm">
                    <span className="text-blue-400 font-semibold">CV</span>
                    <span className="text-gray-700 font-medium">
                        {cvData?.data?.basics?.name || email}
                    </span>
                </div>
                <div className="flex items-center gap-2 bg-indigo-50 border border-indigo-100 rounded-lg px-4 py-2 text-sm">
                    <span className="text-indigo-400 font-semibold">Job</span>
                    <span className="text-gray-700 font-medium">{jobTitle}</span>
                </div>
            </div>

            {/* TurnoverRiskTab — the full prediction widget */}
            <TurnoverRiskTabSafe
                userEmail={email}
                jobId={jobId}
                jobTitle={jobTitle}
                jobDescription={jobDescription}
                jobLocation={jobLocation}  
            />
        </div>
    );
};