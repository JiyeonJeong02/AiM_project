import React from "react";
import { Link } from "react-router-dom"; // ✅ 추가
import "./Home.css"; // 스타일 적용

const Home = () => {
  const sections = [
    {
      title: "기업 알아보기",
      description:
        "자기소개서 작성에 필요한 기업 정보를 확인 할 수 있습니다.",
      buttonText: "기업 정보",
      bgColor: "teal",
      imgSrc: "https://via.placeholder.com/300",
      link: "#", // 링크 없음
    },
    {
      title: "AI 면접",
      description:
        "AI 면접관이 진행하게 됩니다.",
      buttonText: "AI 면접 보기",
      bgColor: "indigo",
      imgSrc: "https://via.placeholder.com/300",
      link: "/interview", // ✅ 인터뷰 페이지로 이동
    },
  ];

  return (
    <div className="home-container">
      <div className="cards-container">
        {sections.map((section, index) => (
          <div key={index} className="card">
            {/* 헤더 */}
            <div className="card-header" style={{ backgroundColor: section.bgColor }}>
              {section.title}
            </div>

            {/* 본문 */}
            <div className="card-body">
              <p>{section.description}</p>
            </div>

            {/* 이미지 */}
            <div className="card-image">
              <img src={section.imgSrc} alt={section.title} />
            </div>

            {/* 버튼 */}
            <div className="card-footer">
              {section.link !== "#" ? (
                <Link to={section.link}>
                  <button className="action-button" style={{ backgroundColor: section.bgColor }}>
                    {section.buttonText}
                  </button>
                </Link>
              ) : (
                <button className="action-button" style={{ backgroundColor: section.bgColor }}>
                  {section.buttonText}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Home;
