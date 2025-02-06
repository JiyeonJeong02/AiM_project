import React, { useState, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import SpeechRecognitionComponent from "../components/SpeechRecognition";
import { getInterviewResponse } from "../components/ChatGPTService";
import "./InterviewSession.css";

const INTERVIEW_TIME = 30; // ⏳ 답변 시간 (초)

const InterviewSession = () => {
  const location = useLocation();
  const { title, job } = location.state || { title: "AI 면접", job: "직무 미정" };

  const [conversation, setConversation] = useState([{ role: "bot", text: "자기소개를 해주세요." }]);
  const [userAnswer, setUserAnswer] = useState(""); // ✅ 면접자의 답변
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [timeLeft, setTimeLeft] = useState(INTERVIEW_TIME);
  const chatBoxRef = useRef(null);
  const timerRef = useRef(null);

  const { startListening, stopListening, resetTranscript } = SpeechRecognitionComponent({
    onResult: (text) => setUserAnswer(text),
  });
  

  // 🔹 웹캠 설정
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true, audio: true }).then((stream) => {
      const video = document.querySelector("video");
      if (video) video.srcObject = stream;
    });
  }, []);

  const handleStartRecording = () => {
    stopListening(); // 🔥 기존 음성 인식 종료 후 재시작
  
    setUserAnswer(""); // ✅ 이전 답변 초기화
    setIsRecording(true);
    setTimeLeft(INTERVIEW_TIME);
    clearInterval(timerRef.current);
  
    resetTranscript(); // ✅ 새로운 질문 시작할 때 음성 인식 초기화 (핵심 추가)
  
    // ⏳ 타이머 시작
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          stopListening();
          handleSubmitResponse();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  
    setTimeout(() => startListening(), 500); // ✅ 0.5초 딜레이 후 음성 인식 시작
  };
  
  const handleSubmitResponse = async () => {
    if (!userAnswer.trim()) return;
  
    stopListening(); // ✅ 답변 전송 전 음성 인식 중지
    setIsRecording(false);
    clearInterval(timerRef.current);
    setIsLoading(true);
  
    const currentAnswer = userAnswer.trim(); // ✅ 현재 답변 저장
    setUserAnswer(""); // ✅ 바로 초기화하여 다음 질문에서 이전 답변 남는 것 방지
  
    setConversation((prev) => [...prev, { role: "user", text: currentAnswer }]);
  
    const botResponse = await getInterviewResponse(currentAnswer);
    setConversation((prev) => [...prev, { role: "bot", text: botResponse }]);
  
    setIsLoading(false);
  
    // ✅ 다음 질문 진행
    setTimeout(() => {
      setUserAnswer(""); // ✅ 새로운 질문 전 기존 답변 다시 초기화
      handleStartRecording();
    }, 1000);
  };
  

  return (
    <div className="interview-session-container">
      <div className="interview-header">
        <h1>{title}</h1>
        <h2>지원 직무: {job}</h2>
      </div>

      {/* 🔹 타이머 UI */}
      {isRecording && (
        <div className="timer">
          ⏳ 남은 시간: {timeLeft}초
        </div>
      )}

      <div className="video-container">
        <video autoPlay playsInline />
      </div>

      <div className="chat-box" ref={chatBoxRef}>
        {conversation.map((msg, index) => (
          <p key={index} className={msg.role === "user" ? "user-msg" : "bot-msg"}>
            {msg.text}
          </p>
        ))}
        {isLoading && <p className="loading-msg">답변을 생성하는 중...</p>}
      </div>

      {/* 🔹 답변 시작 버튼 */}
      {!isRecording && (
        <button className="start-button" onClick={handleStartRecording}>
          답변 시작
        </button>
      )}

      {/* 🔹 답변 완료 버튼 */}
      {isRecording && userAnswer && (
        <div className="user-input-preview">
          <p>🗣 면접자 답변: {userAnswer}</p>
          <button className="submit-button" onClick={handleSubmitResponse}>
            답변 완료
          </button>
        </div>
      )}
    </div>
  );
};

export default InterviewSession;
