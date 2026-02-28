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
    <div style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h2>Repo File Browser</h2>

      <div style={{ marginBottom: 12 }}>
        <input placeholder="username" value={username} onChange={(e) => setUsername(e.target.value)} style={{ marginRight: 8 }} />
        <input placeholder="reponame" value={reponame} onChange={(e) => setReponame(e.target.value)} style={{ marginRight: 8 }} />
        <button onClick={loadFiles} disabled={!username || !reponame}>
          Load Files
        </button>
      </div>

      {loading && <p>Loading…</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      <div style={{ display: "flex", gap: 24 }}>
        <ul style={{ minWidth: 200 }}>
          {files.map((file) => (
            <li key={file}>
              <button
                style={{
                  background: "none",
                  border: "none",
                  padding: 0,
                  cursor: "pointer",
                  color: file === selectedFile ? "green" : "white",
                }}
                onClick={() => loadFile(file)}
              >
                {file}
              </button>
            </li>
          ))}
        </ul>

        <pre
          style={{
            flex: 1,
            background: "#000000ff",
            padding: 12,
            overflow: "auto",
            whiteSpace: "pre-wrap",
          }}
        >
          {fileContent || "Select a file to view its contents"}
        </pre>
        <button
          style={{ height: "50px" }}
          disabled={!selectedFile}
          onClick={() => {
            const params = new URLSearchParams({
              username,
              repoName: reponame,
              filename: selectedFile || "",
            });
            window.open(`/questions/ask?${params.toString()}`, "_blank"); // opens in new tab
          }}
        >
          Go to Questions
        </button>
      </div>
    </div>
  );
}
