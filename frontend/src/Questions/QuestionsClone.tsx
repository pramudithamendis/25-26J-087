import React, { useState } from "react";

type CloneRequest = {
  repo_url: string;
  dest: string;
};

const QuestionsClone: React.FC = () => {
  const [username, setUsername] = useState("pramudithamendis");
  const [repoName, setRepoName] = useState("BI-backend");
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
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Clone Repository</h1>

      <div style={{ marginBottom: "1rem" }}>
        <div style={{ marginBottom: "0.5rem" }}>
          <label style={{ display: "block", marginBottom: "0.25rem" }}>GitHub Username:</label>
          <input type="text" placeholder="GitHub username" value={username} onChange={(e) => setUsername(e.target.value)} style={{ width: "300px" }} />
        </div>

        <div style={{ marginBottom: "0.5rem" }}>
          <label style={{ display: "block", marginBottom: "0.25rem" }}>Repository Name:</label>
          <input type="text" placeholder="Repository name" value={repoName} onChange={(e) => setRepoName(e.target.value)} style={{ width: "300px" }} />
        </div>

        <div style={{ marginBottom: "0.5rem" }}>
          <label style={{ display: "block", marginBottom: "0.25rem" }}>Base Destination Path:</label>
          {/* <input type="text" placeholder="Destination path" value={destination} onChange={(e) => setDestination(e.target.value)} style={{ width: "300px" }} /> */}
          <small style={{ color: "#666", display: "block", marginTop: "0.25rem" }}>Repository will be cloned to: {getDestinationPath()}</small>
        </div>

        <div style={{ marginBottom: "1rem", padding: "1rem", borderRadius: "4px" }}>
          <strong>Generated Repository URL:</strong>
          <div style={{ marginTop: "0.25rem", wordBreak: "break-all" }}>{getRepoUrl()}</div>
        </div>
      </div>

      <button
        onClick={handleClone}
        disabled={loading || !username || !repoName || !destination}
        style={{
          padding: "0.5rem 1rem",
          backgroundColor: loading ? "#ccc" : "#007bff",
          color: "white",
          border: "none",
          borderRadius: "4px",
          cursor: loading ? "not-allowed" : "pointer",
        }}
      >
        {loading ? "Cloning..." : "Clone Repository"}
      </button>

      {response && (
        <div style={{ color: "green", marginTop: "1rem", padding: "1rem", backgroundColor: "#e7f7e7", borderRadius: "4px" }}>
          <strong>Success:</strong> {response}
        </div>
      )}

      {error && (
        <div style={{ color: "red", marginTop: "1rem", padding: "1rem", backgroundColor: "#ffe7e7", borderRadius: "4px" }}>
          <strong>Error:</strong> {error}
        </div>
      )}
    </div>
  );
};

export default QuestionsClone;
