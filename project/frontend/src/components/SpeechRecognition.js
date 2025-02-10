import { useState, useEffect, useRef, useCallback } from "react";

const SpeechRecognitionComponent = ({ onResult }) => {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);
  const transcriptRef = useRef("");

  useEffect(() => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      console.error("❌ 브라우저가 음성 인식을 지원하지 않습니다.");
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognitionRef.current = new SpeechRecognition();
    recognitionRef.current.continuous = true; // 사용자가 말하는 동안 계속 인식
    recognitionRef.current.interimResults = true;
    recognitionRef.current.lang = "ko-KR";

    recognitionRef.current.onstart = () => {
      console.log("🎙 Speech recognition started");
      setIsListening(true);
    };

    recognitionRef.current.onresult = (event) => {
      let finalTranscript = transcriptRef.current;
      for (let i = event.resultIndex; i < event.results.length; i++) {
        // isFinal이 true인 결과만 누적합니다.
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript + " ";
        }
      }
      transcriptRef.current = finalTranscript;
      // 부모 컴포넌트에 누적된 최종 결과를 전달
      onResult(finalTranscript.trim());
    };

    recognitionRef.current.onerror = (event) => {
      // "aborted" 오류 등은 콘솔에 경고만 표시하고 무시합니다.
      if (event.error === "aborted" || event.error === "no-speech") {
        console.warn("⚠ Speech recognition error (ignored):", event.error);
      } else {
        console.error("⚠ Speech recognition error:", event.error);
      }
    };

    recognitionRef.current.onend = () => {
      console.log("🛑 Speech recognition ended");
      setIsListening(false);
    };

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [onResult]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current || isListening) return;
    console.log("🎙 Starting speech recognition...");
    setIsListening(true);
    transcriptRef.current = "";
    try {
      recognitionRef.current.start();
    } catch (err) {
      console.error("Failed to start speech recognition:", err);
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      console.log("🛑 Stopping speech recognition");
      try {
        recognitionRef.current.stop();
      } catch (err) {
        console.error("Failed to stop speech recognition:", err);
      }
    }
  }, [isListening]);

  const resetTranscript = useCallback(() => {
    transcriptRef.current = "";
  }, []);

  return { startListening, stopListening, resetTranscript, isListening };
};

export default SpeechRecognitionComponent;
