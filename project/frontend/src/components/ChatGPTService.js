import axios from "axios";

const OPENAI_API_KEY = process.env.REACT_APP_OPENAI_API_KEY;

if (!OPENAI_API_KEY) {
  console.error("🚨 OpenAI API 키가 설정되지 않았습니다. .env 파일을 확인하세요.");
}


export const getInterviewResponse = async (userAnswer) => {
  const response = await axios.post(
    "https://api.openai.com/v1/chat/completions",
    {
      model: "gpt-4-turbo",
      messages: [
        { role: "system", content: "당신은 면접관입니다. 면접 질문을 해주세요." },
        { role: "user", content: userAnswer },
      ],
    },
    {
      headers: {
        Authorization: `Bearer ${OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
    }
  );

  return response.data.choices[0].message.content;
};
