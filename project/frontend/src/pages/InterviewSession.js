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

  // 웹캠 설정 (muted 속성으로 에코 방지)
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

  // 봇 질문이 나타나면 자동 음성 인식 시작
  useEffect(() => {
    if (!isLoading && conversation[conversation.length - 1].role === "bot" && !isInterviewOver) {
      resetTranscript();
      startListening();
      setIsRecording(true);
    }
  }, [conversation, isLoading, resetTranscript, startListening, isInterviewOver]);

  // 봇의 메시지가 업데이트되면 TTS로 읽어줍니다.
  useEffect(() => {
    const lastMessage = conversation[conversation.length - 1];
    if (lastMessage && lastMessage.role === "bot") {
      const utterance = new SpeechSynthesisUtterance(lastMessage.text);
      utterance.lang = "ko-KR";
      utterance.rate = 1.2; // 속도를 기본보다 50% 빠르게 설정 (원하는 속도로 조절 가능)
      window.speechSynthesis.speak(utterance);
    }
  }, [conversation]);

  // 면접 결과 확인 버튼 핸들러: 전체 대화 내용을 결합해 GPT 피드백을 받아 결과 페이지로 이동
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

    // 질문 5개 이상이면 면접 종료 처리
    if (questionCount >= 5) {
      setConversation((prev) => [
        ...prev,
        { role: "bot", text: "면접이 종료되었습니다. 결과 확인 버튼을 눌러주세요." },
      ]);
      setIsInterviewOver(true);
      setIsLoading(false);
      return;
    }

    // 5개 미만이면 다음 질문 생성
    const botResponse = await getInterviewResponse(currentAnswer, company, job);
    setConversation((prev) => [...prev, { role: "bot", text: botResponse }]);
    setQuestionCount((prev) => prev + 1);
    setIsLoading(false);

    // 3초 후 다음 질문을 위한 음성 인식 시작
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
        <p className="question-progress">
          {isInterviewOver ? "면접이 종료되었습니다." : `질문 ${questionCount} / 5`}
        </p>
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

      {/* 면접 종료 시 결과 확인 버튼 */}
      {isInterviewOver && (
        <div className="user-input-preview">
          {isViewingResults ? (
            <p className="loading-msg">결과를 불러오는 중...</p>
          ) : (
            <button className="submit-button" onClick={handleViewResults}>
              결과 확인
            </button>
          )}
        </div>
      )}

      {/* 면접 진행 중일 때 사용자 입력 및 답변 완료 버튼 */}
      {!isInterviewOver && isRecording && userAnswer && (
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
