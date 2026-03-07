// src/App.tsx
import React, { useState, useEffect } from "react";
import axios from "axios";
import { useLocation } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000/api/items";

interface AskResponse {
  questions: string;
}

const QuestionsAsk: React.FC = () => {
  const location = useLocation();
  const params = new URLSearchParams(location.search);

  const [username, setUsername] = useState(params.get("username") || "pramudithamendis");
  const [repoName, setRepoName] = useState(params.get("repoName") || "BI-backend");
  const [filenames, setFilenames] = useState<string[]>(params.get("filenames") ? JSON.parse(params.get("filenames")!) : []);
  const [folder, setFolder] = useState(`./uploads/repos/${username}/${repoName}`);
  const [questions, setQuestions] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Update folder path whenever username or repoName changes
  useEffect(() => {
    setFolder(`./uploads/repos/${username}/${repoName}`);
  }, [username, repoName]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setQuestions(null);

    try {
      const token = localStorage.getItem("auth_token");

      console.log("took token");
      console.log("folder", folder);
      console.log("filenames", filenames);
      const response = await axios.post<AskResponse>(
        `${API_BASE}/ask`,
        { folder, filenames },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      console.log("got response");

      setQuestions(response.data.questions);
    } catch (err: any) {
      if (err.response) {
        setError(err.response.data.detail || "Server Error");
      } else {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-flex-start p-6">
      <div className="w-full max-w-md space-y-6">
        {/* Title */}
        <h1 className="text-3xl font-bold text-center text-gray-800">Generate Questions and answers</h1>

        {/* Form Card */}
        <form onSubmit={handleSubmit} className="bg-white p-8 rounded-2xl shadow-lg space-y-5">
          {/* Username */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border border-gray-300 px-4 py-2 rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-blue-500
                       transition"
              placeholder="e.g. octocat"
              required
            />
          </div>

          {/* Repository Name */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Repository Name</label>
            <input
              type="text"
              value={repoName}
              onChange={(e) => setRepoName(e.target.value)}
              className="w-full border border-gray-300 px-4 py-2 rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-blue-500
                       transition"
              placeholder="e.g. my-project"
              required
            />
          </div>

          {/* Filename */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1">Selected Files</label>
            <div className="border border-gray-300 px-4 py-2 rounded-lg bg-gray-50 text-sm">{filenames.length > 0 ? filenames.join(", ") : "No files selected"}</div>
          </div>

          {/* Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg font-semibold text-white
                     bg-blue-600 hover:bg-blue-700
                     disabled:bg-gray-400 disabled:cursor-not-allowed
                     transition duration-200"
          >
            {loading ? "Generating..." : "Generate Questions and answers"}
          </button>
        </form>

        {/* Error */}
        {error && <div className="bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-lg text-sm">{error}</div>}

        {/* Questions Card */}
        {questions && (
          <div className="bg-white p-6 rounded-2xl shadow-lg w-364">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Generated Questions and answers</h2>
            <pre className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">{questions}</pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default QuestionsAsk;
