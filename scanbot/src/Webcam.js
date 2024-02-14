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
        const context = canvas.getContext('2d');
        var frames = []

        if (canvas && video) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            context.drawImage(video, 0, 0, canvas.width, canvas.height);
            frames.push(context.getImageData(0, 0, canvas.width, canvas.height));
            averageFrames(frames);

            return canvasRef.current.toDataURL('image/png');
        }
    };

    const averageFrames = (frames) => {
        const width = frames[0].width;
        const height = frames[0].height;
        let avgData = new Uint8ClampedArray(width * height * 4); // 4 for RGBA
    
        // Average the frames
        for (let i = 0; i < avgData.length; i += 4) {
            let [r, g, b, a] = [0, 0, 0, 0];
    
            frames.forEach(frame => {
                r += frame.data[i];
                g += frame.data[i + 1];
                b += frame.data[i + 2];
                a += frame.data[i + 3];
            });
    
            avgData[i] = r / frames.length;
            avgData[i + 1] = g / frames.length;
            avgData[i + 2] = b / frames.length;
            avgData[i + 3] = a / frames.length;
        }
    
        let avgFrame = new ImageData(avgData, width, height);
        canvasRef.current.getContext('2d').putImageData(avgFrame, 0, 0);
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
