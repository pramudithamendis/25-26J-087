// src/App.tsx
import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://127.0.0.1:8000/api/items";

interface AskResponse {
  questions: string;
}

const QuestionsAsk: React.FC = () => {
  const [username, setUsername] = useState("pramudithamendis");
  const [repoName, setRepoName] = useState("BI-backend");
  const [filename, setFilename] = useState("db.js");
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

      const response = await axios.post<AskResponse>(
        `${API_BASE}/ask`,
        { folder, filename },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

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
    <div className="min-h-screen flex flex-col items-center justify-center p-4 bg-gray-100">
      <h1 className="text-2xl font-bold mb-4">Generate Questions</h1>

      <form onSubmit={handleSubmit} className="w-full max-w-md bg-white p-6 rounded shadow">
        <div className="mb-4">
          <label className="block mb-1 font-semibold">Username:</label>
          <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full border px-3 py-2 rounded" required />
        </div>

        <div className="mb-4">
          <label className="block mb-1 font-semibold">Repository Name:</label>
          <input type="text" value={repoName} onChange={(e) => setRepoName(e.target.value)} className="w-full border px-3 py-2 rounded" required />
        </div>

        <div className="mb-4">
          <label className="block mb-1 font-semibold">Filename:</label>
          <input type="text" value={filename} onChange={(e) => setFilename(e.target.value)} className="w-full border px-3 py-2 rounded" required />
        </div>

        <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition" disabled={loading}>
          {loading ? "Generating..." : "Generate Questions"}
        </button>
      </form>

      {error && <p className="text-red-600 mt-4">{error}</p>}

      {questions && (
        <div className="mt-6 w-full max-w-md bg-white p-6 rounded shadow">
          <h2 className="text-xl font-semibold mb-2">Generated Questions:</h2>
          <pre className="whitespace-pre-wrap">{questions}</pre>
        </div>
      )}
    </div>
  );
};

export default QuestionsAsk;
