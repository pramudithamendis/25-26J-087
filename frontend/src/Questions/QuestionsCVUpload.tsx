import React, { useState, type ChangeEvent, type FormEvent } from "react";

const QuestionsCVUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [repos, setRepos] = useState<string[]>([]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setMessage("Please select a PDF file first.");
      return;
    }

    setLoading(true);
    setMessage(null);
    setRepos([]);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const token = localStorage.getItem("auth_token") || sessionStorage.getItem("auth_token");

      const headers: HeadersInit = {};

      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
      const response = await fetch("http://127.0.0.1:8000/api/items/extract-github-readme", {
        method: "POST",
        headers,
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to extract GitHub links");
      }

      const data = await response.json();
      setMessage(data.message || "Done!");
      setRepos(data.repos_stored || []);
    } catch (err: any) {
      setMessage(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: "2rem auto", fontFamily: "sans-serif" }}>
      <h1>GitHub README Extractor</h1>
      <form onSubmit={handleSubmit}>
        <input type="file" accept="application/pdf" onChange={handleFileChange} />
        <button type="submit" disabled={loading} style={{ marginLeft: 10 }}>
          {loading ? "Processing..." : "Upload PDF"}
        </button>
      </form>

      {message && <p style={{ marginTop: 20 }}>{message}</p>}

      {repos.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h3>Stored Repositories:</h3>
          <ul>
            {repos.map((repo) => (
              <li key={repo}>
                <a href={repo} target="_blank" rel="noopener noreferrer">
                  {repo}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default QuestionsCVUpload;
