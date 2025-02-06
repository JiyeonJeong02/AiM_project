import React, { useState, useEffect, useRef } from "react";

const SpeechRecognitionComponent = ({ onResult }) => {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);
  const transcriptRef = useRef(""); // 🔹 전체 문장을 저장하는 변수

  useEffect(() => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      console.error("브라우저가 음성 인식을 지원하지 않습니다.");
      return;
    }

    recognitionRef.current = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognitionRef.current.continuous = true;
    recognitionRef.current.interimResults = true;
    recognitionRef.current.lang = "ko-KR";

    recognitionRef.current.onresult = (event) => {
      let newTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          newTranscript += event.results[i][0].transcript;
        }
      }
      
      if (newTranscript) {
        transcriptRef.current += newTranscript + " "; // ✅ 새로운 문장을 누적
        onResult(transcriptRef.current.trim()); // ✅ 전체 문장을 업데이트
      }
    };

    recognitionRef.current.onerror = (event) => {
      console.error("음성 인식 오류 발생:", event.error);
    };

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [onResult]);

  const startListening = () => {
    if (recognitionRef.current && !isListening) {
      setIsListening(true);
      transcriptRef.current = ""; // ✅ 새로운 질문마다 답변 초기화 (핵심 수정)
      recognitionRef.current.start();
    }
  };

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      setIsListening(false);
      recognitionRef.current.stop();
    }
  };

  const resetTranscript = () => {
    transcriptRef.current = ""; // ✅ 새로운 질문 시작 시 초기화
  };

  return { startListening, stopListening, resetTranscript };
};

export default SpeechRecognitionComponent;
