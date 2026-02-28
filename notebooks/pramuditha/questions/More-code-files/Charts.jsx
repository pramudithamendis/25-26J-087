import { useEffect, useState } from "react";
import axios from "axios";
import WalletBalanceChart from "./ChartminiComponents/WalletBalanceChart";
import GamePlayDaysChart from "./ChartminiComponents/GamePlayDaysChart";
import CommissionChart from "./ChartminiComponents/other/CommissionChart";
import "./Charts.css";

export default function Charts() {
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchTables() {
      try {
        const res = await axios.get("http://localhost:3000/api/charts");
        setTables(res.data.results);
      } catch (err) {
        console.error("Failed fetching charts:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchTables();
  }, []);

  if (loading) return <h1 className="loading">Loading charts...</h1>;

  function getNeededCols(data, xaxis, yaxis) {
    if ((xaxis = "date_")) {
      return data.map((row) => ({
        _x: row["date_"].split("T")[0],
        _y: Number(row[yaxis]) || 0,
      }));
    } else {
      return data.map((row) => ({
        _x: row[xaxis] || "Unknown",
        _y: Number(row[yaxis]) || 0,
      }));
    }
  }

  return (
    <div className="charts-root">
      <h1 className="charts-title">Analytics Dashboard</h1>

      <div className="charts-grid">
        {tables.map((table, index) => {
          const type = table.chart_type;
          const data = table.data ?? [];

          return (
            <div className="chart-card" key={index}>
              <h2 className="chart-card-title">{table.metric_name || "Chart"}</h2>

              {type === "bar_chart" && <WalletBalanceChart data={getNeededCols(data, "email", "total_balance")} />}
              {type === "bar_chart" && <WalletBalanceChart data={getNeededCols(data, "date_", "remainder_you_keep_32pct")} />}
              {type === "line_chart" && <GamePlayDaysChart data={getNeededCols(data, "date_", "total_sessions")} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
