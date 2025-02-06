import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Home from "./pages/Home";
import Interview from "./pages/Interview";
import Results from "./pages/Results";
import Settings from "./pages/Settings";
import "./App.css"; // 스타일 적용
import StartInterview from "./pages/StartInterview";
import InterviewStart from "./pages/InterviewStart";
import InterviewSession from "./pages/InterviewSession";

function App() {
  return (
    <Router>
      <Navbar />
      <div className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/interview" element={<Interview />} />
          <Route path="/results" element={<Results />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/start-interview" element={<StartInterview />} />
          <Route path="/interview-start" element={<InterviewStart />} />
          <Route path="/interview-session" element={<InterviewSession />} />
          
        </Routes>
        
      </div>
    </Router>
  );
}

export default App;
