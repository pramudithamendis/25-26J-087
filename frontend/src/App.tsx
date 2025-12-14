import React from "react";
import { Routes, Route } from "react-router-dom";
import QuestionsCVUpload from "./Questions/QuestionsCVUpload";

function App() {
  return (
    <Routes>
      <Route path="/questions/upload" element={<QuestionsCVUpload />} />
    </Routes>
  );
}

export default App;
