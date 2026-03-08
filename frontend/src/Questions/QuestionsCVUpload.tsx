import React, { useState, type ChangeEvent, type FormEvent } from "react";

const QuestionsCVUpload: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [repos, setRepos] = useState<string[]>([]);
  const [githubUsername, setGithubUsername] = useState<string | null>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const copyToClipboard = async () => {
    if (githubUsername) {
      await navigator.clipboard.writeText(githubUsername);
      alert("Copied to clipboard!");
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

      if (data.repos_stored && data.repos_stored.length > 0) {
        const url = data.repos_stored[0];
        const username = url.split("github.com/")[1].split("/")[0];
        setGithubUsername(username);
      }

      console.log(data.repos_stored[0]);

    } catch (err: any) {
      setMessage(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-6">
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">GitHub README Extractor</h1>

        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4">
          <input
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            className="flex-1 block w-full text-sm text-gray-700 
                     file:mr-4 file:py-2 file:px-4
                     file:rounded-lg file:border-0
                     file:text-sm file:font-semibold
                     file:bg-gray-900 file:text-white
                     hover:file:bg-blue-600
                     cursor-pointer"
          />

          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 rounded-lg font-medium text-white
                     bg-gray-900 hover:bg-blue-600
                     disabled:bg-gray-400 disabled:cursor-not-allowed
                     transition duration-200"
          >
            {loading ? "Processing..." : "Upload PDF"}
          </button>
        </form>

        {message && <p className="mt-6 text-sm font-medium text-gray-700">{message}</p>}

        {repos.length > 0 && (
          <div className="mt-6">
            <h3 className="font-semibold text-gray-800 mb-2">Stored Repositories:</h3>

            <ul className="space-y-2">
              {repos.map((repo) => (
                <li key={repo}>
                  <a href={repo} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline break-all">
                    {repo}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {githubUsername && (
          <div className="mt-4 flex items-center gap-3">
            <span className="text-gray-800 font-medium">GitHub Username: {githubUsername}</span>

            <button onClick={copyToClipboard} className="px-3 py-1 text-sm rounded-lg bg-gray-900 text-white hover:bg-blue-600">
              Copy
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default QuestionsCVUpload;
