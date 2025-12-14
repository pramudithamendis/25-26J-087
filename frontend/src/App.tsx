import React from "react";
import { Routes, Route } from "react-router-dom";
import QuestionsCVUpload from "./Questions/QuestionsCVUpload";
import QuestionsFindBestProject from "./Questions/QuestionsFindBestProject";
import QuestionsClone from "./Questions/QuestionsClone";

function App() {
  return (
    <Routes>
      <Route path="/questions/upload" element={<QuestionsCVUpload />} />
      <Route path="/questions/bestproject" element={<QuestionsFindBestProject />} />
      <Route path="/questions/clone" element={<QuestionsClone />} />
    </Routes>
  );
}

export default App;
