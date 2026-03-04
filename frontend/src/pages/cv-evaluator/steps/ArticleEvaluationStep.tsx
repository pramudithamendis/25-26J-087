import { useState, useEffect } from "react";
import { AlertCircle, BarChart3, CheckCircle, Loader2, TrendingUp } from "lucide-react";
import { calculateCVTrendScore, type TrendScoreResult } from "../../../services/trendService";
import type { CVSubmitResponse } from "../../../types/cv.types";

interface ArticleEvaluationStepProps {
    cvData?: CVSubmitResponse | null;
    onNext?: () => void;
    onComplete?: () => void;
}

export const ArticleEvaluationStep = ({ cvData, onNext, onComplete }: ArticleEvaluationStepProps) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [result, setResult] = useState<TrendScoreResult | null>(null);

    const cvId = cvData?.data?.cv_id;

    const handleCalculate = async () => {
        if (!cvId) {
            setError('No CV data available. Please upload a CV first.');
            return;
        }

        setLoading(true);
        setError('');
        try {
            const data = await calculateCVTrendScore(cvId);
            setResult(data);
        } catch (err: any) {
            setError(err.message || 'Failed to calculate trend score');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (cvId && !result && !loading) {
            handleCalculate();
        }
    }, [cvId]);

    const getScoreColor = (score: number) => {
        if (score >= 0.7) return 'text-green-600';
        if (score >= 0.4) return 'text-yellow-600';
        return 'text-red-500';
    };

    const getScoreBarWidth = (score: number) => {
        return `${Math.min(score * 100, 100)}%`;
    };

    const handleContinue = () => {
        if (onComplete) onComplete();
        if (onNext) onNext();
    };

    if (!cvId) {
        return (
            <div className="text-center py-12">
                <AlertCircle className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <p className="text-gray-500">No CV data available. Please upload a CV first.</p>
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto">
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Skill Trend Analysis</h2>
                <p className="text-gray-600">
                    We analyze your CV skills against current industry trends to see how relevant your skillset is.
                </p>
            </div>

            {/* Loading State */}
            {loading && (
                <div className="text-center py-12">
                    <Loader2 className="mx-auto h-10 w-10 text-blue-500 animate-spin mb-4" />
                    <p className="text-gray-600 font-medium">Analyzing your skills against current trends...</p>
                    <p className="text-gray-400 text-sm mt-1">This may take a moment</p>
                </div>
            )}

            {/* Error State */}
            {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
                    <div className="flex items-center">
                        <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
                        <p className="text-red-700">{error}</p>
                    </div>
                    <button
                        onClick={handleCalculate}
                        className="mt-3 px-4 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200 text-sm"
                    >
                        Retry
                    </button>
                </div>
            )}

            {/* Results */}
            {result && !loading && (
                <div className="space-y-6">
                    {/* Overall Score Card */}
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-6">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center">
                                <BarChart3 className="h-6 w-6 text-blue-600 mr-2" />
                                <h3 className="text-lg font-semibold text-gray-900">Overall Trend Score</h3>
                            </div>
                            <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded-full">
                                Week: {result.week_id}
                            </span>
                        </div>
                        <div className="flex items-end gap-3">
                            <span className={`text-4xl font-bold ${getScoreColor(result.cv_trend_score)}`}>
                                {(result.cv_trend_score * 100).toFixed(1)}%
                            </span>
                            <span className="text-gray-500 text-sm mb-1">trend relevance</span>
                        </div>
                        <div className="mt-3 bg-gray-200 rounded-full h-3 overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-1000"
                                style={{ width: getScoreBarWidth(result.cv_trend_score) }}
                            />
                        </div>
                    </div>

                    {/* Matched Skills */}
                    <div className="bg-white border border-gray-200 rounded-xl p-6">
                        <div className="flex items-center mb-4">
                            <TrendingUp className="h-5 w-5 text-green-600 mr-2" />
                            <h3 className="text-lg font-semibold text-gray-900">
                                Matched Trending Skills ({result.skills_matched.length})
                            </h3>
                        </div>

                        {result.skills_matched.length === 0 ? (
                            <p className="text-gray-500 text-center py-4">
                                No trending skills matched in your CV. Consider adding more current skills.
                            </p>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {result.skills_matched
                                    .sort((a, b) => b.score - a.score)
                                    .map((skill, index) => (
                                        <div
                                            key={index}
                                            className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-3 border border-gray-100"
                                        >
                                            <span className="font-medium text-gray-800">{skill.skill}</span>
                                            <div className="flex items-center gap-2">
                                                <div className="w-16 bg-gray-200 rounded-full h-2 overflow-hidden">
                                                    <div
                                                        className="h-full bg-green-500 rounded-full"
                                                        style={{ width: getScoreBarWidth(skill.score) }}
                                                    />
                                                </div>
                                                <span className={`text-sm font-semibold ${getScoreColor(skill.score)}`}>
                                                    {(skill.score * 100).toFixed(0)}%
                                                </span>
                                            </div>
                                        </div>
                                    ))}
                            </div>
                        )}
                    </div>

                    {/* Continue Button */}
                    <div className="flex justify-end pt-4">
                        <button
                            onClick={handleContinue}
                            className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium flex items-center gap-2 transition-colors"
                        >
                            <CheckCircle className="h-5 w-5" />
                            Continue to Next Step
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};