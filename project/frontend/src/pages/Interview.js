import React from "react";
import { Link } from "react-router-dom";
import "./Interview.css";

const Interview = () => {
  return (
    <div className="interview-page">
      <header className="header-section">
        <div className="intro">
          <h1>AI 면접 소개</h1>
          <p>
            AI 면접은 면접 제목 입력, 지원 직무 선택 후 이어서 답변하는 방식으로 진행됩니다.
          </p>
          <p>
            총 10개의 질문이 주어지며, 전체 면접 소요시간은 약 20분입니다.
          </p>
        </div>
        <div className="instructions">
          <h2>이용 방법 안내</h2>
          <ul>
            <li>면접 전에 마이크와 카메라 등의 사전 준비를 완료하세요.</li>
            <li>각 질문에 대해 자연스럽게 답변을 이어서 녹음합니다.</li>
            <li>"답변 완료" 버튼을 누르면 해당 답변이 전송됩니다.</li>
            <li>면접 후 사용자의 답변을 바탕으로 피드백이 제공됩니다.</li>
          </ul>
          <Link to="/start-interview">
            <button className="start-button">AI 면접 시작하기</button>
          </Link>
        </div>
      </header>
    </div>
  );
};

export default Interview;
