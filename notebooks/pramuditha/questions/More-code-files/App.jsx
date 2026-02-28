import { useState } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
// import "./App.css";
import Cards from "./components/Cards";
import Tables from "./components/Tables";
import Charts from "./components/Charts";
import { Routes, Route } from "react-router-dom";

function App() {
  return (
    <Routes>
      <Route path="/cards" element={<Cards />} />
      <Route path="/tables" element={<Tables />} />
      <Route path="/charts" element={<Charts />} />
    </Routes>
  );
}

export default App;
