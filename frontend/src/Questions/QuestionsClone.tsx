import React, { useState } from "react";

type CloneRequest = {
  repo_url: string;
  dest: string;
};

const QuestionsClone: React.FC = () => {
  const [repoUrl, setRepoUrl] = useState("https://github.com/pramudithamendis/BI-backend.git");
  const [destination, setDestination] = useState("./uploads/repos/pramudithamendis/testEcommerce-Recommendation-app");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

      const res = await fetch("http://127.0.0.1:8000/api/items/clone", {
        method: "POST",
        headers,
        body: JSON.stringify({ repo_url: repoUrl, dest: destination } as CloneRequest),
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
        <input type="text" placeholder="Repository URL" value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} style={{ width: "300px", marginRight: "1rem" }} />
        <input type="text" placeholder="Destination Path" value={destination} onChange={(e) => setDestination(e.target.value)} style={{ width: "300px" }} />
      </div>
      <button onClick={handleClone} disabled={loading}>
        {loading ? "Cloning..." : "Clone Repo"}
      </button>
      {response && <p style={{ color: "green", marginTop: "1rem" }}>{response}</p>}
      {error && <p style={{ color: "red", marginTop: "1rem" }}>{error}</p>}
    </div>
  );
};

export default QuestionsClone;
