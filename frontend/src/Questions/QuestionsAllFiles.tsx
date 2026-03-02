import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

const API_BASE = "http://127.0.0.1:8000/api/items"; // e.g. "http://localhost:8000"

export default function QuestionsAllFiles() {
  const [username, setUsername] = useState("pramudithamendis");
  const [reponame, setReponame] = useState("BI-backend");
  const [files, setFiles] = useState<string[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  async function loadFiles() {
    setError(null);
    setFiles([]);
    setSelectedFile(null);
    setFileContent("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/files/${username}/${reponame}`);

      if (!res.ok) {
        throw new Error(`Failed to load files (${res.status})`);
      }

      const data: string[] = await res.json();
      setFiles(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function loadFile(filename: string) {
    setError(null);
    setSelectedFile(filename);
    setFileContent("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/files/${username}/${reponame}/${filename}`);

      if (!res.ok) {
        throw new Error(`Failed to load file (${res.status})`);
      }

      const raw = await res.text();
      const text = JSON.parse(raw);
      setFileContent(text);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto bg-white shadow-xl rounded-2xl p-8">
        <h2 className="text-2xl font-bold text-gray-800 mb-6">Repo File Browser</h2>

        {/* Inputs */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <input
            placeholder="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="px-4 py-2 border rounded-lg w-full sm:w-auto
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <input
            placeholder="reponame"
            value={reponame}
            onChange={(e) => setReponame(e.target.value)}
            className="px-4 py-2 border rounded-lg w-full sm:w-auto
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          <button
            onClick={loadFiles}
            disabled={!username || !reponame}
            className="px-5 py-2 rounded-lg font-medium text-white
                     bg-gray-900 hover:bg-blue-600
                     disabled:bg-gray-400 disabled:cursor-not-allowed
                     transition"
          >
            Load Files
          </button>
        </div>

        {loading && <p className="text-gray-600 mb-4 animate-pulse">Loading…</p>}

        {error && <p className="text-red-600 font-medium mb-4">{error}</p>}

        {/* Main Layout */}
        <div className="flex flex-col lg:flex-row gap-8">
          {/* File List */}
          <ul className="w-full lg:w-64 bg-gray-50 rounded-xl p-4 space-y-2 border">
            {files.map((file) => (
              <li key={file}>
                <button
                  onClick={() => loadFile(file)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition
                  ${file === selectedFile ? "bg-green-100 text-green-700 font-semibold" : "hover:bg-gray-200 text-gray-700"}`}
                >
                  {file}
                </button>
              </li>
            ))}
          </ul>

          {/* File Content */}
          <div className="flex-1 flex flex-col gap-4">
            <pre
              className="flex-1 bg-black text-green-400 rounded-xl p-4 
                       overflow-auto text-sm whitespace-pre-wrap"
            >
              {fileContent || "Select a file to view its contents"}
            </pre>

            <button
              disabled={!selectedFile}
              onClick={() => {
                const params = new URLSearchParams({
                  username,
                  repoName: reponame,
                  filename: selectedFile || "",
                });
                window.open(`/questions/ask?${params.toString()}`, "_blank");
              }}
              className="self-start px-6 py-2 rounded-lg font-medium text-white
                       bg-green-600 hover:bg-green-700
                       disabled:bg-gray-400 disabled:cursor-not-allowed
                       transition"
            >
              Go to Questions
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
