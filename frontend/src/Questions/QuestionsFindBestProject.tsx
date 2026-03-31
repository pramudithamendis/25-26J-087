import React, { useState, useEffect } from "react";

interface Project {
  repo: string;
  readme: string;
  github_url: string;
  score: number;
  user: string;
}

interface MatchResponse {
  best_project: Project;
  ranking: Project[];
}

const QuestionsFindBestProject: React.FC = () => {
  const [jobDescription, setJobDescription] = useState("Looking for someone experienced in machine learning and NLP.");
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUsername = async () => {
      try {
        const email = localStorage.getItem("currentEmail");
        const token = localStorage.getItem("auth_token") || sessionStorage.getItem("auth_token");

        if (!email) return;

        const headers: HeadersInit = {
          "Content-Type": "application/json",
        };

        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        console.log("email", email);
        const res = await fetch(`http://127.0.0.1:8000/api/items/cvs/email/${encodeURIComponent(email)}`, {
          headers,
        });

        if (!res.ok) return;

        const data = await res.json();

        if (data.username) {
          setUsername(data.username);
        }
        console.log("data.username", data.username);
      } catch (err) {
        console.error("Failed to fetch username:", err);
      }
    };

    fetchUsername();
  }, []);

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
        console.log(data);
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
    <div className="min-h-screen bg-gray-100 p-6 flex justify-center">
      <div className="w-full max-w-3xl bg-white shadow-xl rounded-2xl p-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-8 text-center">Project Matcher</h1>

        <form onSubmit={handleSubmit} className="space-y-6 mb-10">
          {/* Username */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-4 py-2
                       focus:outline-none focus:ring-2 focus:ring-blue-500
                       focus:border-transparent transition"
            />
          </div>

          {/* Job Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Job Description</label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              rows={5}
              required
              className="w-full rounded-lg border border-gray-300 px-4 py-2
                       focus:outline-none focus:ring-2 focus:ring-blue-500
                       focus:border-transparent transition resize-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-lg font-semibold text-white
                     bg-gray-900 hover:bg-blue-600
                     disabled:bg-gray-400 disabled:cursor-not-allowed
                     transition duration-200"
          >
            {loading ? "Matching..." : "Find Best Project"}
          </button>
        </form>

        {/* Error */}
        {error && <div className="mb-6 p-4 rounded-lg bg-red-100 text-red-700 font-medium">{error}</div>}

        {/* Results */}
        {result && (
          <div className="space-y-8">
            {/* Best Project */}
            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-4">Best Project</h2>

              <div className="border border-gray-200 rounded-xl p-6 shadow-sm bg-gray-50">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Username: {result.best_project.github_url.split("/").at(-2)}</h3>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Repo    : {result.best_project.repo}</h3>  

                <p className="text-gray-700 mb-4 whitespace-pre-wrap">{result.best_project.readme}</p>

                <div className="text-sm text-gray-600">
                  Score: <span className="font-semibold">{result.best_project.score}</span> |{" "}
                  <a href={result.best_project.github_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline font-medium">
                    GitHub
                  </a>
                </div>
              </div>
            </div>

            {/* Ranking */}
            <div>
              <h2 className="text-xl font-bold text-gray-800 mb-4">Ranking</h2>

              <ol className="space-y-4 list-decimal list-inside">
                {result.ranking.map((proj) => (
                  <li key={proj.repo} className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
                      <div>
                        <span className="font-semibold text-gray-900">{proj.repo}</span> <span className="text-gray-600">— Score: {proj.score.toFixed(4)}</span>
                      </div>

                      <a href={proj.github_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-sm font-medium">
                        GitHub
                      </a>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default QuestionsFindBestProject;
