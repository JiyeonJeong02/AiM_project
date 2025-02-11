import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./StartInterview.css";

const StartInterview = () => {
  const [title, setTitle] = useState("");
  const [job, setJob] = useState("");
  const [selectedJob, setSelectedJob] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const navigate = useNavigate();

  // API 호출: 검색어(query)를 포함하여 ncs_code에서 ncsLclasCdNm 검색
  const fetchSuggestions = async (query) => {
    try {
      const response = await fetch(`/api/ncs-codes?search=${encodeURIComponent(query)}`);
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data);
      } else {
        console.error("Error fetching suggestions");
      }
    } catch (error) {
      console.error("Error fetching suggestions:", error);
    }
  };

  // 직무 입력 변경 시, 선택된 직무 초기화
  const handleJobChange = (e) => {
    setJob(e.target.value);
    setSelectedJob("");
  };

  // 추천 항목 클릭 시 처리
  const handleSelectSuggestion = (suggestion) => {
    setJob(suggestion.ncsLclasCdNm);
    setSelectedJob(suggestion.ncsLclasCdNm);
    setSuggestions([]);
  };

  const handleConfirm = () => {
    if (!title.trim() || !job.trim() || !selectedJob.trim()) {
      alert("제목과 직무를 올바르게 입력해주세요.");
      return;
    }
    navigate("/interview-start", { state: { title, job: selectedJob } });
  };

  return (
    <div className="start-interview-container">
      <div className="info-header">
        <h1>제목과 직무를 입력해 주세요.</h1>
        <p>사용자의 기본 정보를 입력하는 단계입니다. 제목과 직무를 입력해주세요.</p>
      </div>

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
          <div className="autocomplete-container">
            <input 
              type="text" 
              id="job" 
              placeholder="지원 직무를 입력하세요"
              value={job}
              onChange={handleJobChange}
              autoComplete="off"
            />
            <button className="search-button" onClick={() => fetchSuggestions(job)}>
              검색
            </button>
            {suggestions.length > 0 && (
              <ul className="suggestions-list">
                {suggestions.map((item) => (
                  <li key={item.ncsLclasCd} onClick={() => handleSelectSuggestion(item)}>
                    {item.ncsLclasCdNm}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* 확인 버튼 */}
          <button className="confirm-button" onClick={handleConfirm}>
            확인
          </button>
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
