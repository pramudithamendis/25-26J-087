import type { RolePrediction } from '../../types/evaluationTypes';

interface RolePredictionsProps {
  predictions: RolePrediction[];
}

export const RolePredictions = ({ predictions }: RolePredictionsProps) => {
  if (predictions.length === 0) {
    return (
      <div className="text-sm text-gray-500">No role predictions available</div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Role Predictions</h3>
      <div className="space-y-2">
        {predictions.map((prediction, index) => {
          const similarity = (prediction.similarity * 100).toFixed(1);
          return (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
            >
              <span className="font-medium text-gray-900">
                {prediction.role}
              </span>
              <div className="flex items-center gap-3">
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all"
                    style={{ width: `${prediction.similarity * 100}%` }}
                  />
                </div>
                <span className="text-sm font-semibold text-gray-700 w-12 text-right">
                  {similarity}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

