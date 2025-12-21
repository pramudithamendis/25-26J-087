// src/App.tsx
import React, { useState } from "react";
import axios from "axios";

interface AskResponse {
  questions: string;
}

const QuestionsAsk: React.FC = () => {
  const [folder, setFolder] = useState("./uploads/repos/testUser");
  const [filename, setFilename] = useState("logging.js");
  const [questions, setQuestions] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setQuestions(null);

    try {
      // Example in handleSubmit
      const token = localStorage.getItem("auth_token"); // Or wherever you store it

      const response = await axios.post<AskResponse>(
        "http://127.0.0.1:8000/api/items/ask",
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
          <label className="block mb-1 font-semibold">Folder:</label>
          <input type="text" value={folder} onChange={(e) => setFolder(e.target.value)} className="w-full border px-3 py-2 rounded" required />
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
