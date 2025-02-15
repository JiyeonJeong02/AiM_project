import React, { useState } from "react";
import axios from "axios";
import "./CompanyInfo.css";

const CompanyInfo = () => {
  const [companyName, setCompanyName] = useState("");
  const [overview, setOverview] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(
        `http://localhost:8000/business_overview?company_name=${encodeURIComponent(
          companyName
        )}`
      );
      // 예시로 첫번째 결과의 개요를 표시합니다.
      const data = response.data;
      if (data && data.length > 0) {
        setOverview(data[0]._source.business_overview_summary);
      } else {
        setOverview("기업 정보를 찾을 수 없습니다.");
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
      {overview && (
        <div className="overview-card">
          <h2>{companyName}</h2>
          <p>{overview}</p>
        </div>
      )}
    </div>
  );
};

export default CompanyInfo;
