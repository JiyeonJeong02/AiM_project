import React from "react";
import { Link } from "react-router-dom";
import "../App.css"; // 스타일 적용

const Navbar = () => {
  return (
    <nav className="navbar">
      {/* ✅ I.M.S 클릭 시 홈으로 이동 */}
      <h1>
        <Link to="/" className="home-link">I.M.S</Link>
      </h1>
      <ul>
        <li><Link to="/">홈</Link></li>
        <li><Link to="/Company-info">기업 분석</Link></li>
        <li><Link to="/interview">면접 시작</Link></li>
      </ul>
    </nav>
  );
};

export default Navbar;
