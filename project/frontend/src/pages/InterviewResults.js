import React from "react";
import { useLocation, Link } from "react-router-dom";
import "./InterviewResults.css";

const InterviewResults = () => {
  const { state } = useLocation();
  const { feedback, conversation } = state || {};

  // 피드백 텍스트에서 * 와 - 제거 (정규표현식 사용)
  const sanitizedFeedback = feedback ? feedback.replace(/[*-]/g, '') : '';

  return (
    <div className="results-container">
      <h1>면접 결과</h1>
      {feedback ? (
        <div className="feedback-box">
          <h2>피드백</h2>
          <p>{sanitizedFeedback}</p>
        </div>
      ) : (
        <p>피드백을 가져올 수 없습니다.</p>
      )}
      <div className="conversation-box">
        <h2>대화 기록</h2>
        {conversation && conversation.map((msg, index) => (
          <p key={index} className={msg.role === "user" ? "user-msg" : "bot-msg"}>
            {msg.role === "user" ? "면접자: " : "면접관: "}
            {msg.text}
          </p>
        ))}
      </div>
      <Link to="/">
        <button className="back-button">홈으로 돌아가기</button>
      </Link>
    </div>
  );
};

export default InterviewResults;
