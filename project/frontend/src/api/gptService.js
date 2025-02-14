import axios from "axios";

export const getInterviewResponse = async (userAnswer, companyname, subcategory) => {
  try {
    const response = await axios.post("http://localhost:8000/interview", {
      answer: String(userAnswer),
      companyname: String(companyname),
      subcategory: String(subcategory),
    });
    return response.data.response;
  } catch (error) {
    console.error("FastAPI 응답 받기 오류:", error);
    throw error;
  }
};
