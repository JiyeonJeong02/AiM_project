import React from "react";
import { Link } from "react-router-dom";

const Navbar = () => {
  return (
    <nav className="bg-blue-600 text-white p-4">
      <div className="container mx-auto flex justify-between items-center">
        <h1 className="text-xl font-bold">AI 면접 도우미</h1>
        <ul className="flex space-x-4">
          <li><Link to="/" className="hover:underline">홈</Link></li>
          <li><Link to="/interview" className="hover:underline">면접 시작</Link></li>
          <li><Link to="/results" className="hover:underline">면접 결과</Link></li>
          <li><Link to="/settings" className="hover:underline">설정</Link></li>
        </ul>
      </div>
    </nav>
  );
};

export default Navbar;
