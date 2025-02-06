import React, { useEffect, useRef } from "react";

const WebcamFeed = () => {
  const videoRef = useRef(null);

  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      .then((stream) => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch((err) => console.error("웹캠 접근 오류: ", err));
  }, []);

  return <video ref={videoRef} autoPlay playsInline />;
};

export default WebcamFeed;
