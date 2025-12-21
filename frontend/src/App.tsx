import React from "react";
import { Routes, Route } from "react-router-dom";
import QuestionsCVUpload from "./Questions/QuestionsCVUpload";
import QuestionsFindBestProject from "./Questions/QuestionsFindBestProject";
import QuestionsClone from "./Questions/QuestionsClone";
import QuestionsAllFiles from "./Questions/QuestionsAllFiles";
import QuestionsAsk from "./Questions/QuestionsAsk";

function App() {
  return (
    <Routes>
      <Route path="/questions/upload" element={<QuestionsCVUpload />} />
      <Route path="/questions/bestproject" element={<QuestionsFindBestProject />} />
      <Route path="/questions/clone" element={<QuestionsClone />} />
      <Route path="/questions/allfiles" element={<QuestionsAllFiles />} />
      <Route path="/questions/ask" element={<QuestionsAsk />} />
    </Routes>
  );
}

export default App;
