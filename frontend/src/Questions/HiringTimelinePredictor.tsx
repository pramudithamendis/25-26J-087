import { useState } from "react";
import { API_BASE_URL } from '../config/api';

const API_BASE = `${API_BASE_URL}/api/items`;

function formatDate(dateString: string) {
  return new Date(dateString).toISOString().replace("T", " ").substring(0, 19);
}

export default function HiringTimelinePredictor() {
  const [jobTitle, setJobTitle] = useState("SAP");
  const [salary, setSalary] = useState("120000");

  const [sourcingStart, setSourcingStart] = useState("");
  const [submissionDate, setSubmissionDate] = useState("");
  const [interviewStart, setInterviewStart] = useState("");
  const [interviewEnd, setInterviewEnd] = useState("");
  const [offered, setOffered] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, number> | null>(null);

  async function handlePredict() {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const token = localStorage.getItem("auth_token");

      const payload = {
        "Job Title": jobTitle || null,
        "Salary ($1000)": salary ? Number(salary) : null,
        "Sourcing Start": sourcingStart ? formatDate(sourcingStart) : null,
        "Submission Date": submissionDate ? formatDate(submissionDate) : null,
        "Interview Start": interviewStart ? formatDate(interviewStart) : null,
        "Interview End": interviewEnd ? formatDate(interviewEnd) : null,
        Offered: offered ? formatDate(offered) : null,
        Filled: null,
      };

      // Remove empty values automatically
      const cleanPayload = Object.fromEntries(Object.entries(payload).filter(([_, value]) => value !== null && value !== ""));

      const res = await fetch(`${API_BASE}/predict-hiring-timeline`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(cleanPayload),
      });

      if (!res.ok) {
        throw new Error(`Prediction failed (${res.status})`);
      }

      const data = await res.json();
      setResult(data.timeline_predictions);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto bg-white shadow-xl rounded-2xl p-8">
        <h2 className="text-2xl font-bold mb-6 text-gray-800">Hiring Timeline Predictor</h2>

        {/* FORM */}
        <div className="space-y-4 mb-8">
          <span>Job</span>
          <input type="text" placeholder="Job Title" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} className="w-full p-3 border rounded-lg" />

          <span>Salary</span>
          <input type="number" placeholder="Salary ($1000)" value={salary} onChange={(e) => setSalary(e.target.value)} className="w-full p-3 border rounded-lg" />

          <span>Sourcing Start</span>
          <input type="datetime-local" value={sourcingStart} onChange={(e) => setSourcingStart(e.target.value)} className="w-full p-3 border rounded-lg" />

          <span>Submission Date</span>
          <input type="datetime-local" value={submissionDate} onChange={(e) => setSubmissionDate(e.target.value)} className="w-full p-3 border rounded-lg" />

          <span>Interview Start</span>
          <input type="datetime-local" value={interviewStart} onChange={(e) => setInterviewStart(e.target.value)} className="w-full p-3 border rounded-lg" />

          <span>Interview End</span>
          <input type="datetime-local" value={interviewEnd} onChange={(e) => setInterviewEnd(e.target.value)} className="w-full p-3 border rounded-lg" />

          <span>Offered</span>
          <input type="datetime-local" value={offered} onChange={(e) => setOffered(e.target.value)} className="w-full p-3 border rounded-lg" placeholder="Offered Date" />
        </div>

        <button onClick={handlePredict} disabled={loading || !jobTitle || !salary} className="px-6 py-2 rounded-lg font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 transition">
          {loading ? "Predicting..." : "Predict Timeline"}
        </button>

        {error && <p className="text-red-600 mt-4 font-medium">{error}</p>}

        {/* RESULTS */}
        {result && (
          <div className="mt-8">
            <h3 className="text-xl font-semibold mb-4 text-gray-700">Predicted Remaining Stages</h3>

            <div className="space-y-3">
              {Object.entries(result).map(([stage, days]) => (
                <div key={stage} className="flex justify-between items-center bg-gray-50 border rounded-lg p-4">
                  <span className="font-medium text-gray-800">{stage}</span>
                  <span className="text-green-600 font-bold">{days} days</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
