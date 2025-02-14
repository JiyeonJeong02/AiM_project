import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./StartInterview.css";

const StartInterview = () => {
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [job, setJob] = useState("");
  const [selectedJob, setSelectedJob] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const navigate = useNavigate();

  // API 호출: 검색어(query)를 포함하여 ncs_code에서 ncsSubdCdNm 검색
  const fetchSuggestions = async (query) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/ncs-codes?search=${encodeURIComponent(query)}`
      );
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

  // 직무 입력 변경 시, 선택된 직무 초기화하고 추천 목록 숨기기
  const handleJobChange = (e) => {
    setJob(e.target.value);
    setSelectedJob("");
    setShowSuggestions(false);
  };

  // 엔터키 입력 시 검색
  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      fetchSuggestions(job);
      setShowSuggestions(true);
    }
  };

  // 추천 항목 클릭 시 처리 (ncsSubdCdNm 사용)
  const handleSelectSuggestion = (suggestion) => {
    setJob(suggestion.ncsSubdCdNm);
    setSelectedJob(suggestion.ncsSubdCdNm);
    setSuggestions([]);
    setShowSuggestions(false);
  };

  const handleConfirm = () => {
    if (!title.trim() || !job.trim() || !selectedJob.trim()) {
      alert("제목과 직무를 올바르게 입력해주세요.");
      return;
    }
    navigate("/interview-start", { state: { title, company, job: selectedJob } });
  };

  // 글자 수 2자 이상일 때 자동 검색 (원하는 경우 유지)
  useEffect(() => {
    if (job.trim().length > 1) {
      fetchSuggestions(job);
    } else {
      setSuggestions([]);
    }
  }, [job]);

  return (
    <div className="start-interview-container">
      <div className="info-header">
        <h1>제목과 직무를 입력해 주세요.</h1>
        <p>사용자의 기본 정보를 입력하는 단계입니다. 제목, 회사명(선택), 직무를 입력해주세요.</p>
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
          {/*기업명 입력력*/}
          <label htmlFor="company">기업명</label>
          <input
            type="text"
            id="company"
            placeholder="기업명을 입력하세요 (선택)"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
          />
          {/* 직무 선택 (소분류) */}
          <label htmlFor="job">직무 선택 (소분류)</label>
          <div className="autocomplete-container">
            <input
              type="text"
              id="job"
              placeholder="지원 직무 (소분류)를 입력하세요"
              value={job}
              onChange={handleJobChange}
              onKeyDown={handleKeyDown}
              autoComplete="off"
            />
            <button
              className="search-button"
              onClick={() => {
                fetchSuggestions(job);
                setShowSuggestions(true);
              }}
            >
              검색
            </button>
            {showSuggestions && suggestions.length > 0 && (
              <ul className="suggestions-list">
                {suggestions.map((item, index) => (
                  <li
                    key={`${item.ncsSubdCd}-${index}`}
                    onClick={() => handleSelectSuggestion(item)}
                  >
                    {item.ncsSubdCdNm}
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
