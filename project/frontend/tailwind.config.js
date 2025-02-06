/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
      extend: {
        colors: {
          primary: "#2563EB", // 모던한 블루 톤
          secondary: "#1E293B", // 다크 모드 지원
          accent: "#FACC15", // 포인트 컬러 (옐로우)
        },
      },
    },
    plugins: [],
  };
  