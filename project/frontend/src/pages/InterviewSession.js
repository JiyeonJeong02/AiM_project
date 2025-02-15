import React, { useState, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import SpeechRecognitionComponent from "../components/SpeechRecognition";
import { getInterviewResponse } from "../api/gptService";
import "./InterviewSession.css";

const INTERVIEW_TIME = 60;

const InterviewSession = () => {
  // location.state + localStorage 병합
  const locationState = useLocation().state || {};
  const storageState = JSON.parse(localStorage.getItem("interviewData") || "{}");
  const state = { ...storageState, ...locationState };

  const title = state.title || "AI 면접";
  const company = state.company || "";
  const job = state.job || "직무 미정";

  const [conversation, setConversation] = useState([
    { role: "bot", text: "자기소개를 해주세요." },
  ]);
  const [userAnswer, setUserAnswer] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const chatBoxRef = useRef(null);
  const videoRef = useRef(null);
  const timerRef = useRef(null);

  const { startListening, stopListening, resetTranscript } = SpeechRecognitionComponent({
    onResult: (text) => setUserAnswer(text),
  });

  // 스크롤 자동
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [conversation]);

  // 웹캠
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      .then((stream) => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err) => console.error("❌ 웹캠 오류:", err));
  }, []);

  // 봇 질문 -> 음성인식 자동 시작
  useEffect(() => {
    if (!isLoading && conversation[conversation.length - 1].role === "bot") {
      resetTranscript();
      startListening();
      setIsRecording(true);
    }
  }, [conversation, isLoading, resetTranscript, startListening]);

  const handleSubmitResponse = async () => {
    if (!userAnswer.trim() || isLoading) return;
    stopListening();
    setIsRecording(false);
    setIsLoading(true);

    const currentAnswer = userAnswer.trim();
    setUserAnswer("");
    resetTranscript();

    setConversation((prev) => [...prev, { role: "user", text: currentAnswer }]);

    // 백엔드 요청
    const botResponse = await getInterviewResponse(currentAnswer, company, job);
    setConversation((prev) => [...prev, { role: "bot", text: botResponse }]);

    setIsLoading(false);

    // 3초 후 다음 질문
    setTimeout(() => {
      resetTranscript();
      startListening();
      setIsRecording(true);
    }, 3000);
  };

  return (
    <div className="interview-session-container">
      {/* 헤더 */}
      <div className="interview-header">
        <h1>{title}</h1>
        <div className="header-subinfo">
          <p>지원 직무: {job}</p>
          {company && <p>기업명: {company}</p>}
        </div>
      </div>

      {/* 메인 컨텐츠 (가로 레이아웃) */}
      <div className="main-content">
        <div className="video-container">
          <video ref={videoRef} autoPlay playsInline muted />
        </div>
        <div className="chat-box" ref={chatBoxRef}>
          {conversation.map((msg, index) => (
            <p key={index} className={msg.role === "user" ? "user-msg" : "bot-msg"}>
              {msg.text}
            </p>
          ))}
          {isLoading && <p className="loading-msg">답변을 생성하는 중...</p>}
        </div>
      </div>

      {/* 사용자 입력 미리보기 + 답변 버튼 */}
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
