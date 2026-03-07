import React, { useState } from "react";

type CloneRequest = {
  repo_url: string;
  dest: string;
};

const QuestionsClone: React.FC = () => {
  const [username, setUsername] = useState("pramudithamendis");
  const [repoName, setRepoName] = useState("Xpress-Hirely");
  const [destination, setDestination] = useState("./uploads/repos");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Generate the repo URL from username and repoName
  const getRepoUrl = () => {
    return `https://github.com/${username}/${repoName}.git`;
  };

  // Generate the destination path from username and repoName
  const getDestinationPath = () => {
    return `${destination}/${username}/${repoName}`;
  };

  const handleClone = async () => {
    setLoading(true);
    setResponse(null);
    setError(null);

    try {
      const token = localStorage.getItem("auth_token") || sessionStorage.getItem("auth_token");

      const headers: HeadersInit = {
        "Content-Type": "application/json",
      };

      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const repoUrl = getRepoUrl();
      const destPath = getDestinationPath();

      const res = await fetch("http://127.0.0.1:8000/api/items/clone", {
        method: "POST",
        headers,
        body: JSON.stringify({ repo_url: repoUrl, dest: destPath } as CloneRequest),
      });

      // Check if response has content
      const text = await res.text();

      if (!text) {
        throw new Error("Empty response from server");
      }

      // Try to parse as JSON
      let data;
      try {
        data = JSON.parse(text);
      } catch (parseError) {
        throw new Error(`Server returned non-JSON response: ${text.substring(0, 100)}`);
      }

      if (!res.ok) {
        throw new Error(data.detail || data.message || `HTTP ${res.status}: ${text}`);
      }

      setResponse(`Cloned ${data.repo} to ${data.destination}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-6">
      <div className="w-full max-w-xl bg-white shadow-xl rounded-2xl p-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Clone Repository</h1>

        <div className="space-y-4">
          {/* GitHub Username */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">GitHub Username:</label>
            <input
              type="text"
              placeholder="GitHub username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                       focus:outline-none focus:ring-2 focus:ring-blue-500
                       focus:border-blue-500 transition"
            />
          </div>

          {/* Repository Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Repository Name:</label>
            <input
              type="text"
              placeholder="Repository name"
              value={repoName}
              onChange={(e) => setRepoName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg
                       focus:outline-none focus:ring-2 focus:ring-blue-500
                       focus:border-blue-500 transition"
            />
          </div>

          {/* Destination Path */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Base Destination Path:</label>

            <small className="block text-gray-500 mt-1">Repository will be cloned to:</small>

            <div className="text-sm text-gray-700 break-all mt-1 bg-gray-50 p-2 rounded">{getDestinationPath()}</div>
          </div>

          {/* Generated Repo URL */}
          <div className="bg-gray-50 p-4 rounded-lg border">
            <strong className="block text-sm text-gray-700">Generated Repository URL:</strong>
            <div className="mt-2 text-sm text-blue-600 break-all">{getRepoUrl()}</div>
          </div>
        </div>

        {/* Button */}
        <button
          onClick={handleClone}
          disabled={loading || !username || !repoName || !destination}
          className={`mt-6 w-full py-2 px-4 rounded-lg font-medium text-white transition
          ${loading || !username || !repoName || !destination ? "bg-gray-400 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"}`}
        >
          {loading ? "Cloning..." : "Clone Repository"}
        </button>

        {/* Success */}
        {response && (
          <div className="mt-6 p-4 rounded-lg bg-green-100 text-green-800 border border-green-200">
            <strong>Success:</strong> {response}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mt-6 p-4 rounded-lg bg-red-100 text-red-800 border border-red-200">
            <strong>Error:</strong> {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default QuestionsClone;
