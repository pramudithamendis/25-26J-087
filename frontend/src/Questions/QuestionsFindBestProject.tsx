import React, { useState } from "react";

interface Project {
  repo: string;
  readme: string;
  github_url: string;
  score: number;
}

interface MatchResponse {
  best_project: Project;
  ranking: Project[];
}

const QuestionsFindBestProject: React.FC = () => {
  const [jobDescription, setJobDescription] = useState("Looking for someone experienced in machine learning and NLP.");
  const [username, setUsername] = useState("pramudithamendis");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null); // Clear previous results

    try {
      const token = localStorage.getItem("auth_token") || sessionStorage.getItem("auth_token");

      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };

      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch("http://127.0.0.1:8000/api/items/match-project", {
        method: "POST",
        headers,
        body: JSON.stringify({
          job_description: jobDescription,
          username,
        }),
      });

      // First, check if response is OK
      if (!res.ok) {
        // Try to parse error response, but handle case where response might be empty
        const text = await res.text();

        if (text) {
          try {
            const errorData = JSON.parse(text);
            throw new Error(errorData.detail || `HTTP ${res.status}: ${res.statusText}`);
          } catch {
            throw new Error(`HTTP ${res.status}: ${res.statusText}. Response: ${text.substring(0, 100)}`);
          }
        } else {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
      }

      // Check if response has content
      const text = await res.text();

      if (!text || text.trim().length === 0) {
        throw new Error("Server returned empty response");
      }

      try {
        const data: MatchResponse = JSON.parse(text);
        setResult(data);
      } catch (parseError) {
        console.error("JSON Parse Error:", parseError, "Response text:", text);
        throw new Error(`Invalid JSON response from server. Response: ${text.substring(0, 200)}...`);
      }
    } catch (err: any) {
      setError(err.message);
      console.error("Error details:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Project Matcher</h1>

      <form onSubmit={handleSubmit} style={{ marginBottom: "2rem" }}>
        <div style={{ marginBottom: "1rem" }}>
          <label>
            Username: <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </label>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label>
            Job Description: <textarea value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} rows={5} cols={50} required />
          </label>
        </div>

        <button type="submit" disabled={loading}>
          {loading ? "Matching..." : "Find Best Project"}
        </button>
      </form>

      {error && <div style={{ color: "red" }}>{error}</div>}

      {result && (
        <div>
          <h2>Best Project</h2>
          <div style={{ border: "1px solid #ccc", padding: "1rem", marginBottom: "2rem" }}>
            <h3>{result.best_project.repo}</h3>
            <p>{result.best_project.readme}</p>
            <p>
              Score: {result.best_project.score} |{" "}
              <a href={result.best_project.github_url} target="_blank" rel="noopener noreferrer">
                GitHub
              </a>
            </p>
          </div>

          <h2>Ranking</h2>
          <ol>
            {result.ranking.map((proj) => (
              <li key={proj.repo} style={{ marginBottom: "1rem" }}>
                <strong>{proj.repo}</strong> - Score: {proj.score.toFixed(4)} -{" "}
                <a href={proj.github_url} target="_blank" rel="noopener noreferrer">
                  GitHub
                </a>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
};

export default QuestionsFindBestProject;
