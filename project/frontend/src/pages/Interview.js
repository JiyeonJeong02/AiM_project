import React from "react";
import { Link } from "react-router-dom";
import "./Interview.css"; // 스타일 적용

const Interview = () => {
  return (
    <div className="interview-container">
      {/* AI면접 소개 섹션 */}
      <div className="interview-header">
        <h1>AI면접</h1>
        <p>
          AI면접은 기본면접/AI게임/심층면접 등 총 6단계로 구성되며 대략 총 20분 ~ 30분 가량 소요됩니다.
          <br />
          시작하기 전에 앞서 마이크/캠장치 등의 사전준비를 끝낸 후 시작하시기 바랍니다.
        </p>
        <Link to="/start-interview">
  <button className="start-button">AI면접 바로가기</button></Link>
      </div>

      {/* 카드형 UI 섹션 */}
      <div className="cards-container">
        <div className="card">
          <h3 className="category-title">AI면접</h3>
          <img src="https://via.placeholder.com/300" alt="AI면접" />
          <div className="tags">
          </div>
        </div>

        <div className="card">
          <h3 className="category-title">이용방법 및 학습지원</h3>
          <img src="https://via.placeholder.com/300" />
          <div className="tags">

          </div>
        </div>

        
      </div>
    </div>
  );
};

export default Interview;
