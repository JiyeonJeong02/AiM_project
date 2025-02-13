import React, { useState, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import SpeechRecognitionComponent from "../components/SpeechRecognition";
import { getInterviewResponse } from "../api/gptService";
import "./InterviewSession.css";

const INTERVIEW_TIME = 60; // 답변 시간 (초)

const InterviewSession = () => {
  const location = useLocation();
  const { title, job } = location.state || { title: "AI 면접", job: "직무 미정" };

  const [conversation, setConversation] = useState([
    { role: "bot", text: "자기소개를 해주세요." },
  ]);
  const [userAnswer, setUserAnswer] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [timeLeft, setTimeLeft] = useState(INTERVIEW_TIME);
  const chatBoxRef = useRef(null);
  const videoRef = useRef(null);
  const timerRef = useRef(null);

  const { startListening, stopListening, resetTranscript } = SpeechRecognitionComponent({
    onResult: (text) => setUserAnswer(text),
  });

  // 채팅창 자동 스크롤
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [conversation]);

  // 웹캠 설정 (카메라 기능 유지)
  useEffect(() => {
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((stream) => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err) => console.error("❌ 웹캠 접근 오류:", err));
  }, []);

  // 봇 질문이 나타나면 자동으로 음성 인식 시작
  useEffect(() => {
    if (!isLoading && conversation[conversation.length - 1].role === "bot") {
      resetTranscript();
      startListening();
      setIsRecording(true);
    }
  }, [conversation, isLoading, resetTranscript, startListening]);

  const handleSubmitResponse = async () => {
    if (!userAnswer.trim() || isLoading) return; // 중복 요청 방지

    stopListening(); // 음성 인식 중단
    setIsRecording(false);
    setIsLoading(true);
    clearInterval(timerRef.current);

    const currentAnswer = userAnswer.trim();
    setUserAnswer("");
    resetTranscript();

    // 사용자의 답변 추가
    setConversation((prev) => [...prev, { role: "user", text: currentAnswer }]);

    // 선택된 소분류(job)를 두 번째 인자로 전달합니다.
    const botResponse = await getInterviewResponse(currentAnswer, job);
    setConversation((prev) => [...prev, { role: "bot", text: botResponse }]);

    setIsLoading(false);

    // GPT 응답 후 3초 대기 후 다음 질문을 위한 음성 인식 시작
    setTimeout(() => {
      console.log("🕒 3초 대기 후 다음 질문 진행...");
      resetTranscript();
      startListening();
      setIsRecording(true);
    }, 3000);
  };

  return (
    <div className="interview-session-container">
      <div className="interview-header">
        <h1>{title}</h1>
        <h2>지원 직무: {job}</h2>
      </div>

      <div className="video-container">
        <video ref={videoRef} autoPlay playsInline />
      </div>

      <div className="chat-box" ref={chatBoxRef}>
        {conversation.map((msg, index) => (
          <p key={index} className={msg.role === "user" ? "user-msg" : "bot-msg"}>
            {msg.text}
          </p>
        ))}
        {isLoading && <p className="loading-msg">답변을 생성하는 중...</p>}
      </div>

      {/* 답변 완료 버튼 (음성 인식 중이며, 사용자의 답변이 있을 때만 표시) */}
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
