import type { ScoreBreakdown } from '../../types/evaluationTypes';

interface ScoreBreakdownProps {
  breakdown: ScoreBreakdown;
}

export const ScoreBreakdown = ({ breakdown }: ScoreBreakdownProps) => {
  const entries = Object.entries(breakdown).filter(
    ([_, value]) => typeof value === 'number' && value > 0
  );

  if (entries.length === 0) {
    return (
      <div className="text-sm text-gray-500">No breakdown data available</div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Score Breakdown</h3>
      <div className="space-y-3">
        {entries.map(([key, value]) => {
          const percentage = Math.min(value, 100);
          const label = key
            .split('_')
            .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');

          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-700">
                  {label}
                </span>
                <span className="text-sm font-semibold text-gray-900">
                  {value.toFixed(1)}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

