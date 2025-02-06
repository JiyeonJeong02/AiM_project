import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./StartInterview.css"; // 스타일 적용

const StartInterview = () => {
  const [title, setTitle] = useState("");
  const [job, setJob] = useState("");
  const navigate = useNavigate();

  // 확인 버튼 클릭 시 실행
  const handleConfirm = () => {
    if (!title.trim() || !job.trim()) {
      alert("제목과 직무를 입력해주세요.");
      return;
    }
    navigate("/interview-start", { state: { title, job } }); // 면접 시작 페이지로 데이터 전달
  };

  return (
    <div className="start-interview-container">
      {/* 기본 정보 섹션 */}
      <div className="info-header">
    
        <h1>제목과 직무를 입력해 주세요.</h1>
        <p>사용자의 기본 정보를 입력하는 단계입니다. 제목과 직무를 입력해주세요.</p>
      </div>

      {/* 입력 폼 컨테이너 */}
      <div className="form-container">
        <div className="form-section">
          {/* 제목 입력 */}
          <label htmlFor="title">제목</label>
          <input 
            type="text" 
            id="title" 
            placeholder="예: AI 면접 연습 #1"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />

          {/* 직무 선택 */}
          <label htmlFor="job">직무 선택</label>
          <input 
            type="text" 
            id="job" 
            placeholder="지원 직무를 입력하세요"
            value={job}
            onChange={(e) => setJob(e.target.value)}
          />

          {/* 확인 버튼 */}
          <button className="confirm-button" onClick={handleConfirm}>확인</button>
        </div>

        {/* 이미지 영역 */}
        <div className="image-section">
          <img src="/images/pho.jpeg" alt="면접 준비" />
        </div>
      </div>
    </div>
  );
};

export default StartInterview;
