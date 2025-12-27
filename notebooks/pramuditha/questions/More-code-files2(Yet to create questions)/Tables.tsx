import { useEffect, useState } from "react";
import "./Tables.css";

interface MetricResult {
  metric_name: string[];
  sql: string;
  field_names: string[];
  data: Record<string, any>[];
}

export default function App() {
  const [tables, setTables] = useState<MetricResult[]>([]);
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});

  useEffect(() => {
    async function loadData() {
      try {
        const res = await fetch("http://localhost:3000/api/tables");
        const json = await res.json();
        setTables(json.results || []);
      } catch (err) {
        console.error("Failed to fetch data:", err);
      }
    }
    loadData();
  }, []);

  const toggleSQL = (index: number) => {
    setExpanded((prev) => ({
      ...prev,
      [index]: !prev[index],
    }));
  };

  return (
    <div className="dashboard-root">
      <h1 className="dashboard-title">Gameon BI Metrics Dashboard</h1>

      <div className="dashboard-grid">
        {tables.map((metric, index) => (
          <div className="metric-card" key={index}>
            <div className="metric-header">
              <h2 className="metric-title">{metric.metric_name[0]}</h2>
            </div>

            {expanded[index] && <pre className="sql-box">{metric.sql}</pre>}

            <div className="table-wrapper">
              <table className="metric-table">
                <thead>
                  <tr>
                    {metric.field_names.map((field) => (
                      <th key={field}>{field}</th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {metric.data.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {metric.field_names.map((field) => (
                        <td key={field}>{String(row[field] ?? "")}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
