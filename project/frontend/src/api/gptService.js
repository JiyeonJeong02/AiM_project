import axios from "axios";

export const getInterviewResponse = async (userAnswer) => {
  try {
    // FastAPI 서버가 로컬 8000 포트에서 실행 중일 경우
    const response = await axios.post("http://localhost:8000/interview", {
      answer: userAnswer,
    });
    return response.data.response;
  } catch (error) {
    console.error("FastAPI 응답 받기 오류:", error);
    throw error;
  }
};