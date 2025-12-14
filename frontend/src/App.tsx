import React from "react";
import { Routes, Route } from "react-router-dom";
import QuestionsCVUpload from "./Questions/QuestionsCVUpload";
import QuestionsFindBestProject from "./Questions/QuestionsFindBestProject";

function App() {
  return (
    <Routes>
      <Route path="/questions/upload" element={<QuestionsCVUpload />} />
      <Route path="/questions/bestproject" element={<QuestionsFindBestProject />} />
    </Routes>
  );
}

export default App;
