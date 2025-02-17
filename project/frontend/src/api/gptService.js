import axios from "axios";

const HOST_IP = process.env.REACT_APP_HOST_IP;

export const getInterviewResponse = async (userAnswer, companyname, subcategory) => {
  try {
    const response = await axios.post(`http://${HOST_IP}:8000/interview`, {
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


export const getInterviewFeedback = async (conversationText) => {
  try {
    const response = await axios.post(`http://${HOST_IP}:8000/interview-feedback`, {
      conversation: conversationText,
    });
    return response.data.feedback;
  } catch (error) {
    console.error("FastAPI 피드백 받기 오류:", error);
    throw error;
  }
};