import axios from "axios";

export const getInterviewResponse = async (userAnswer, subcategory) => {
  try {
    const response = await axios.post("http://localhost:8000/interview", {
      answer: userAnswer,
      subcategory: subcategory,  // 두 번째 인자 추가
    });
    return response.data.response;
  } catch (error) {
    console.error("FastAPI 응답 받기 오류:", error);
    throw error;
  }
};