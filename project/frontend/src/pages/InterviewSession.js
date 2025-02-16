import React, { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import SpeechRecognitionComponent from "../components/SpeechRecognition";
import { getInterviewResponse, getInterviewFeedback } from "../api/gptService";
import "./InterviewSession.css";

const INTERVIEW_TIME = 60;

const InterviewSession = () => {
  // location.state와 localStorage의 데이터를 병합합니다.
  const locationState = useLocation().state || {};
  const storageState = JSON.parse(localStorage.getItem("interviewData") || "{}");
  const state = { ...storageState, ...locationState };

  const title = state.title || "AI 면접";
  const company = state.company || "";
  const job = state.job || "직무 미정";

  // 질문 개수 관리 (첫 질문은 이미 있으므로 1부터 시작)
  const [questionCount, setQuestionCount] = useState(1);
  const [conversation, setConversation] = useState([
    { role: "bot", text: "자기소개를 해주세요." },
  ]);
  const [userAnswer, setUserAnswer] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isInterviewOver, setIsInterviewOver] = useState(false);
  const [isViewingResults, setIsViewingResults] = useState(false);

  const chatBoxRef = useRef(null);
  const videoRef = useRef(null);
  const navigate = useNavigate();

  const { startListening, stopListening, resetTranscript } = SpeechRecognitionComponent({
    onResult: (text) => setUserAnswer(text),
  });


  // 채팅창 자동 스크롤
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [conversation]);

  // 웹캠 설정
  useEffect(() => {
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: true })
      .then((stream) => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err) => console.error("❌ 웹캠 오류:", err));
  }, []);

  // 봇 메시지 -> 자동 음성 인식
  useEffect(() => {
    if (!isLoading && conversation[conversation.length - 1].role === "bot" && !isInterviewOver) {
      resetTranscript();
      startListening();
      setIsRecording(true);
    }
  }, [conversation, isLoading, resetTranscript, startListening, isInterviewOver]);

  // 봇 메시지 TTS
  useEffect(() => {
    const lastMessage = conversation[conversation.length - 1];
    if (lastMessage && lastMessage.role === "bot") {
      const utterance = new SpeechSynthesisUtterance(lastMessage.text);
      utterance.lang = "ko-KR";
      utterance.rate = 1.1;
      window.speechSynthesis.speak(utterance);
    }
  }, [conversation]);

  // 결과 확인
  const handleViewResults = async () => {
    setIsViewingResults(true);
    const conversationText = conversation
      .map((msg) => (msg.role === "user" ? "면접자: " : "면접관: ") + msg.text)
      .join("\n");
    try {
      const feedbackResponse = await getInterviewFeedback(conversationText);
      navigate("/interview-results", { state: { feedback: feedbackResponse, conversation } });
    } catch (error) {
      console.error("피드백 요청 오류:", error);
      setIsViewingResults(false);
    }
  };

  // 답변 전송
  const handleSubmitResponse = async () => {
    if (!userAnswer.trim() || isLoading) return;
    stopListening();
    setIsRecording(false);
    setIsLoading(true);

    const currentAnswer = userAnswer.trim();
    setUserAnswer("");
    resetTranscript();

    // 사용자 답변 추가
    setConversation((prev) => [...prev, { role: "user", text: currentAnswer }]);

    // 질문 5개 이상 -> 종료
    if (questionCount >= 5) {
      setConversation((prev) => [
        ...prev,
        { role: "bot", text: "면접이 종료되었습니다. 결과 확인 버튼을 눌러주세요." },
      ]);
      setIsInterviewOver(true);
      setIsLoading(false);
      return;
    }

    // 새 질문 생성
    const botResponse = await getInterviewResponse(currentAnswer, company, job);
    setConversation((prev) => [...prev, { role: "bot", text: botResponse }]);
    setQuestionCount((prev) => prev + 1);
    setIsLoading(false);

    // 3초 후 다음 질문 음성 인식
    setTimeout(() => {
      resetTranscript();
      startListening();
      setIsRecording(true);
    }, 3000);
  };

  return (
    <div className="interview-page">
      {/* 상단 영역 (제목, 직무, 질문 카운트 등) */}
      <div className="chat-header">
        <div className="header-left">
          <h2 className="chat-title">{title}</h2>
          <p className="chat-subtitle">
            직무: {job}
            {company && ` | 기업명: ${company}`}
          </p>
        </div>
        <div className="header-right">
          <span className="question-count">
            {isInterviewOver ? "면접 종료" : `질문 ${questionCount} / 5`}
          </span>
        </div>
      </div>

      {/* 메인 컨텐츠 */}
      <div className="main-content">
        {/* 웹캠 영역 (더 크게) */}
        <div className="video-area">
          <video ref={videoRef} autoPlay playsInline muted />
        </div>

        {/* 채팅 박스 */}
        <div className="chat-area">
          <div className="messages" ref={chatBoxRef}>
            {conversation.map((msg, index) => (
              <div
                key={index}
                className={`message-bubble ${msg.role === "user" ? "user-bubble" : "bot-bubble"}`}
              >
                {msg.text}
              </div>
            ))}
            {isLoading && <div className="loading-msg">답변을 생성하는 중...</div>}
          </div>

          {/* 면접 종료 시 결과 버튼 */}
          {isInterviewOver && (
            <div className="action-panel">
              {isViewingResults ? (
                <div className="loading-msg">결과를 불러오는 중...</div>
              ) : (
                <button className="action-button" onClick={handleViewResults}>
                  결과 확인
                </button>
              )}
            </div>
          )}

          {/* 진행 중일 때 답변 완료 버튼 */}
          {!isInterviewOver && isRecording && userAnswer && (
            <div className="action-panel">
              <div className="answer-preview">
                <span>🗣 {userAnswer}</span>
              </div>
              <button className="action-button" onClick={handleSubmitResponse}>
                답변 완료
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default InterviewSession;
