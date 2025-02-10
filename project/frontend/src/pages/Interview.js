import React from "react";
import { Link } from "react-router-dom";
import "./Interview.css"; // 아래 CSS 적용
// 이미지 경로는 실제 사용 환경에 맞게 조정하세요.

const Interview = () => {
  return (
    <div className="interview-container">
      {/* 헤더 영역: 면접 소개와 이용 안내를 컨테이너 안에 배치 */}
      <header className="interview-header">
        <div className="intro-section">

          
        </div>
        <div className="instructions-section">

          <Link to="/start-interview">
            <button className="start-button">AI 면접 바로가기</button>
          </Link>
        </div>
      </header>

      {/* 카드형 UI 섹션 (추가 정보 제공용) */}
      <div className="cards-container">
        <div className="card">
          <h3 className="category-title">AI 면접</h3>
          <img src="/images/ai.jpg" alt="AI 면접" />
          <div className="tags">
          </div>
        </div>

        <div className="card">
          <h3 className="category-title">이용방법 및 학습지원</h3>
          <div className="tags">
            <h4>1. 면접 시작 전에 마이크와 카메라 등의 사전 준비를 완료하시기 바랍니다.</h4>
<h4> 2. AI 면접은 면접 제목 입력, 지원 직무 선택 후 이어서 답변하는 방식으로 진행됩니다.</h4>
<h4> 3. 총 10개의 질문이 주어지며, 전체 면접 소요시간은 약 20분 정도입니다.</h4>
<h4> 4. 면접 종료 시에 사용자의 답변을 바탕으로 피드백이 제공됩니다.</h4>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Interview;
