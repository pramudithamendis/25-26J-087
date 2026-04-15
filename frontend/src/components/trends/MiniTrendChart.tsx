import type { CVTrendScoreHistory } from "../../types/adminTypes";

export const MiniTrendChart = ({
  history,
  onClick
}: {
  history: CVTrendScoreHistory[];
  onClick: () => void;
}) => {

  // ✅ Always sort history 
  const sortedHistory = [...history].sort((a, b) =>
    a.week_id.localeCompare(b.week_id)
  );

  if (sortedHistory.length === 0) {
    return (
      <div className="text-gray-400 text-xs">No data</div>
    );
  }

  const width = 100;
  const height = 40;

  const values = sortedHistory.map(d => d.trend_score);

  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue || 1;

  // ✅ FIX: prevent division by zero
  const xStep = values.length > 1 ? width / (values.length - 1) : width;

  const points = values.map((value, index) => {
    // ✅ center point if only 1 value
    const x = values.length > 1 ? index * xStep : width / 2;

    const normalizedValue = (value - minValue) / range;
    const y =
      height -
      (normalizedValue * (height * 0.8) + height * 0.1);

    return `${x},${y}`;
  }).join(" ");

  return (
    <div
      className="cursor-pointer hover:opacity-80 transition-opacity"
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      title="Click to view full history"
    >
      <svg width={width} height={height} className="block">
        <polyline
          points={points}
          fill="none"
          stroke="#3b82f6"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* ✅ Optional: draw a dot if only one data point */}
        {values.length === 1 && (
          <circle
            cx={width / 2}
            cy={
              height -
              ((values[0] - minValue) / range * (height * 0.8) + height * 0.1)
            }
            r={2}
            fill="#3b82f6"
          />
        )}
      </svg>
    </div>
  );
};