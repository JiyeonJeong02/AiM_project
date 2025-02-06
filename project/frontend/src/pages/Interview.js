import React, { useState } from "react";

const Interview = () => {
  const [question, setQuestion] = useState("AI가 면접 질문을 생성합니다...");
  const [answer, setAnswer] = useState("");

  const fetchQuestion = async () => {
    const res = await fetch("http://localhost:5000/api/interview");
    const data = await res.json();
    setQuestion(data.question);
  };

  const submitAnswer = async () => {
    await fetch("http://localhost:5000/api/interview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer }),
    });
    alert("답변이 제출되었습니다!");
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow-md">
      <h1 className="text-xl font-bold mb-4">{question}</h1>
      <textarea
        className="w-full border rounded p-2"
        rows="4"
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="답변을 입력하세요..."
      />
      <div className="mt-4">
        <button onClick={fetchQuestion} className="bg-blue-500 text-white px-4 py-2 rounded mr-2">새 질문</button>
        <button onClick={submitAnswer} className="bg-green-500 text-white px-4 py-2 rounded">제출</button>
      </div>
    </div>
  );
};

export default Interview;
