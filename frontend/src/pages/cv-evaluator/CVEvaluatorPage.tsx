import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { ArticleEvaluationStep } from "./steps/ArticleEvaluationStep";
import { InfoValidationStep } from "./steps/InfoValidationStep";
import { JobEvaluationStep } from "./steps/JobEvaluationStep";
import { TurnoverPredictionStep } from "./steps/TurnoverPredictionStep";
import { UploadCVStep } from "./steps/UploadCVStep";
import type { CVSubmitResponse } from "../../types/cv.types";
import { CheckCircle } from "lucide-react";
import { useAuth } from "../../contexts/AuthContext";
import { getJob } from "../../services/jobService";
import type { JobResponse } from "../../types/jobTypes";


interface Step {
    id: number;
    name: string;
    description: string;
}

const steps: Step[] = [
    { id: 1, name: 'Upload CV', description: 'Upload and parse your CV' },
    { id: 2, name: 'Validate Info', description: 'Review and correct parsed information' },
    { id: 3, name: 'Job Match', description: 'Compare with job description' },
    { id: 4, name: 'Article Match', description: 'Check against articles/skills' },
    { id: 5, name: 'Prediction', description: 'Turnover risk prediction' },
];

export const CVEvaluatorPage = () => {
    const { jobId: jobIdFromUrl } = useParams<{ jobId: string }>();
    const { user } = useAuth();

    const [currentStep, setCurrentStep] = useState<number>(1);
    const [cvData, setCvData] = useState<CVSubmitResponse | null>(null);
    const [cvFile, setCvFile] = useState<File | null>(null);
    const [completedSteps, setCompletedSteps] = useState<number[]>([]);
    const [jobData, setJobData] = useState<JobResponse | null>(null);

    // Fetch job details when jobId is available (from URL or after step 3 completes)
    useEffect(() => {
        if (jobIdFromUrl) {
            getJob(jobIdFromUrl)
                .then(setJobData)
                .catch(() => { /* non-fatal – step 5 will show a warning */ });
        }
    }, [jobIdFromUrl]);

    const handleNext = () => {
        if (currentStep < steps.length) {
            setCurrentStep(currentStep + 1);
        }
    };

    const handlePrevious = () => {
        if (currentStep > 1) {
            setCurrentStep(currentStep - 1);
        }
    };

    const handleStepComplete = (stepId: number) => {
        if (!completedSteps.includes(stepId)) {
            setCompletedSteps([...completedSteps, stepId]);
        }
    };

    const handleUploadSuccess = (response: CVSubmitResponse) => {
        setCvData(response);
        handleStepComplete(1);
    };

    const renderStep = () => {
        const stepProps = {
            cvData,
            onComplete: () => handleStepComplete(currentStep),
            onNext: handleNext,
        };

        switch (currentStep) {
            case 1:
                return <UploadCVStep onUploadSuccess={handleUploadSuccess} onFileUploaded={(file) => setCvFile(file)} onNext={handleNext} />;
            case 2:
                return <InfoValidationStep {...stepProps} />;
            case 3:
                return <JobEvaluationStep {...stepProps} cvFile={cvFile} />;
            case 4:
                return <ArticleEvaluationStep {...stepProps} />;
            case 5:
                return (
                    <TurnoverPredictionStep
                        {...stepProps}
                        jobId={jobIdFromUrl || jobData?._id}
                        jobTitle={jobData?.title}
                        jobDescription={jobData?.jd_text}
                        userEmail={user?.email}
                    />
                );
            default:
                return <UploadCVStep onUploadSuccess={handleUploadSuccess} onFileUploaded={(file) => setCvFile(file)} onNext={handleNext} />;
        }
    };

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-gray-900">CV Evaluator</h1>
                    <p className="mt-2 text-sm text-gray-600">
                        Complete all steps to get a comprehensive CV evaluation
                    </p>
                </div>

                {/* Progress Steps */}
                <div className="mb-8">
                    <div className="flex items-center justify-between">
                        {steps.map((step, index) => (
                            <div key={step.id} className="flex-1 relative">
                                {/* Connecting line */}
                                {index < steps.length - 1 && (
                                    <div className="absolute top-4 left-1/2 w-full h-0.5 bg-gray-200">
                                        <div
                                            className="h-full bg-blue-600 transition-all duration-500"
                                            style={{
                                                width: completedSteps.includes(step.id) && completedSteps.includes(steps[index + 1].id)
                                                    ? '100%'
                                                    : completedSteps.includes(step.id)
                                                        ? '50%'
                                                        : '0%'
                                            }}
                                        />
                                    </div>
                                )}

                                {/* Step indicator */}
                                <div className="relative flex flex-col items-center">
                                    <div
                                        className={`w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors ${completedSteps.includes(step.id)
                                            ? 'bg-green-500 border-green-500'
                                            : currentStep === step.id
                                                ? 'border-blue-500 bg-white'
                                                : 'border-gray-300 bg-white'
                                            }`}
                                    >
                                        {completedSteps.includes(step.id) ? (
                                            <CheckCircle className="w-5 h-5 text-white" />
                                        ) : (
                                            <span className={`text-sm font-medium ${currentStep === step.id ? 'text-blue-500' : 'text-gray-500'
                                                }`}>
                                                {step.id}
                                            </span>
                                        )}
                                    </div>
                                    <div className="mt-2 text-center">
                                        <p className={`text-sm font-medium ${currentStep === step.id ? 'text-blue-600' : 'text-gray-500'
                                            }`}>
                                            {step.name}
                                        </p>
                                        <p className="text-xs text-gray-400 hidden sm:block">
                                            {step.description}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Navigation Buttons */}
                <div className="flex justify-between items-center mb-6">
                    <button
                        onClick={handlePrevious}
                        disabled={currentStep === 1}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${currentStep === 1
                            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                            : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
                            }`}
                    >
                        ← Previous
                    </button>

                    <div className="text-sm text-gray-500">
                        Step {currentStep} of {steps.length}
                    </div>

                    <button
                        onClick={handleNext}
                        disabled={currentStep === steps.length || !completedSteps.includes(currentStep)}
                        className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${currentStep === steps.length || !completedSteps.includes(currentStep)
                            ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                            : 'bg-blue-600 text-white hover:bg-blue-700'
                            }`}
                    >
                        Next →
                    </button>
                </div>

                {/* Step Content */}
                <div className="bg-white rounded-lg p-6 border border-gray-200">
                    {renderStep()}
                </div>
            </div>
        </div>
    );
};