import React from "react";
import { useLocation, Link } from "react-router-dom";
import "./InterviewResults.css";

const InterviewResults = () => {
  const { state } = useLocation();
  const { feedback, conversation } = state || {};

  // 피드백 텍스트에서 * 와 - 제거 (정규표현식 사용)
  const sanitizedFeedback = feedback ? feedback.replace(/[*-]/g, '') : '';

  // 대화 기록과 피드백을 하나의 텍스트로 결합하는 함수
  const generateTextData = () => {
    const conversationText = conversation
      ? conversation
          .map((msg) =>
            (msg.role === "user" ? "면접자: " : "면접관: ") + msg.text
          )
          .join("\n")
      : "";
    return `피드백:\n${sanitizedFeedback}\n\n대화 기록:\n${conversationText}`;
  };

  // 텍스트 파일 다운로드 함수
  const handleDownload = () => {
    const textData = generateTextData();
    const blob = new Blob([textData], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);

    // 임시 링크를 생성하고 클릭하여 다운로드 실행
    const a = document.createElement("a");
    a.href = url;
    a.download = "interview_results.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // URL 객체 해제
    URL.revokeObjectURL(url);
  };

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
        {conversation &&
          conversation.map((msg, index) => (
            <p key={index} className={msg.role === "user" ? "user-msg" : "bot-msg"}>
              {msg.role === "user" ? "면접자: " : "면접관: "}
              {msg.text}
            </p>
          ))}
      </div>
      <div className="action-buttons">
        <button className="download-button" onClick={handleDownload}>
          결과 다운로드
        </button>
        <Link to="/">
          <button className="back-button">홈으로 돌아가기</button>
        </Link>
      </div>
    </div>
  );
};

export default InterviewResults;
