import React, { useEffect, useRef } from 'react';

const Webcam = ({ onCoordinatesSelected, showWebcam }) => {
    const videoRef = useRef(null);
    const mediaStream = useRef(null);
    const canvasRef = useRef(null);

    useEffect(() => {
        if (showWebcam && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ video: true })
                .then((stream) => {
                    mediaStream.current = stream;
                    if (videoRef.current) {
                        videoRef.current.srcObject = stream;
                    }
                })
                .catch((err) => {
                    console.log("Error accessing the webcam:", err);
                });
        }

        // Cleanup function to stop the media stream
        return () => {
            releaseWebcam();
        };
    }, [showWebcam]);

    const captureFrame = () => {
        const canvas = canvasRef.current;
        const video = videoRef.current;
        if (canvas && video) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            const context = canvas.getContext('2d');
            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            return canvas.toDataURL('image/png');
        }
    };

    const releaseWebcam = () => {
        if (mediaStream.current) {
            mediaStream.current.getTracks().forEach(track => track.stop());
            mediaStream.current = null;
        }
    }

    const handleClick = (event) => {
        const { offsetX, offsetY } = event.nativeEvent;
        const frameData = captureFrame();
        onCoordinatesSelected(offsetX, offsetY, frameData);
    };

    return (
        <div className='webcam'>
            <video ref={videoRef} onClick={handleClick} autoPlay />
            <canvas ref={canvasRef} style={{ display: 'none' }} />
        </div>
    );
};

export default Webcam;
