import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "./InterviewStart.css";

const InterviewStart = () => {
  const location = useLocation();
  const navigate = useNavigate(); // 🔹 페이지 이동을 위한 useNavigate 추가
  const { title, job } = location.state || { title: "AI 면접", job: "직무 미정" };

  const startInterview = () => {
    navigate("/interview-session", { state: { title, job } }); // 🔹 면접 시작 페이지로 이동
  };

  return (
    <div className="interview-start-container">
      <h1>{title}</h1>
      <h2>지원 직무: {job}</h2>
      <p>AI 면접을 시작합니다. 마이크 및 카메라를 확인해주세요.</p>
      <button className="start-button" onClick={startInterview}>
        면접 시작
      </button>
    </div>
  );
};

export default InterviewStart;
