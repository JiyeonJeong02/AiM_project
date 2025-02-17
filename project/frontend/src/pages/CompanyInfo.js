import React, { useState } from "react";
import axios from "axios";
import "./CompanyInfo.css";

const CompanyInfo = () => {
  const [companyName, setCompanyName] = useState("");
  const [overviewSections, setOverviewSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 개요 문자열을 파싱하여 섹션별로 분리하는 함수
  const parseOverviewText = (text) => {
    let rawSections = text
      .split(/(?=\d+\.\s)/) // "0. ", "1. ", "2. " 앞에서 분리
      .map((section) => section.trim())
      .filter(Boolean);

    return rawSections.map((section) => {
      const match = section.match(/^(\d+)\.\s+([^-]+)-\s*(.*)$/);
      if (match) {
        // match[3]는 '내용'인데, 앞에 점이 있다면 제거
        let content = match[3].trim();
        if (content.startsWith(".")) {
          content = content.slice(1).trim();
        }
        return {
          number: match[1],
          title: match[2].trim(),
          content: content,
        };
      } else {
        // 형식이 맞지 않을 경우에도 앞의 점 제거 시도
        let content = section;
        if (content.startsWith(".")) {
          content = content.slice(1).trim();
        }
        return { content };
      }
    });
  };

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    setOverviewSections([]); // 초기화
    try {
      const response = await axios.get(
        `http://host.docker.internal:8000/business_overview?company_name=${encodeURIComponent(
          companyName
        )}`
      );
      const data = response.data;
      if (data && data.length > 0) {
        const bigText = data[0]._source.business_overview_summary || "";
        const parsed = parseOverviewText(bigText);
        if (parsed.length === 0) {
          setError("해당 기업의 정보를 구분할 수 없습니다.");
        } else {
          setOverviewSections(parsed);
        }
      } else {
        setError("기업 정보를 찾을 수 없습니다.");
      }
    } catch (err) {
      setError("기업 정보를 불러오는 중 오류가 발생했습니다.");
      console.error(err);
    }
    setLoading(false);
  };

  return (
    <div className="company-info-container">
      <h1 className="company-info-title">기업 정보 검색</h1>
      <div className="search-box">
        <input
          type="text"
          placeholder="기업명을 입력하세요..."
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSearch();
            }
          }}
        />
        <button onClick={handleSearch}>검색</button>
      </div>
      {loading && <div className="loading">로딩 중...</div>}
      {error && <div className="error">{error}</div>}
      {overviewSections.length > 0 && (
        <div className="overview-card">
          <h2 className="overview-card-title">{companyName}</h2>
          {overviewSections.map((item, idx) => (
            <div key={idx} className="overview-section">
              {item.number && item.title ? (
                <>
                  <h3 className="overview-section-heading">
                    {item.number}. {item.title}
                  </h3>
                  <p className="overview-section-content">{item.content}</p>
                </>
              ) : (
                <p className="overview-section-content">{item.content}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CompanyInfo;
