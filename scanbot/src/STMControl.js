import React, { useState } from 'react';
import { GoBack } from './Components';
import Webcam from './Webcam';
import './styles/STMControl.css'

function STMControl () {
    const [initialiseState, setInitialiseState] = useState({step: 0, inProgress: false, complete: false})
    const [showWebcam, setShowWebcam]       = useState(false);
    const [initialisationImage, setInitialisationImage] = useState(null)
    const [currentInstruction, setCurrentInstruction] = useState(null)
    const resetState = {
        initialFrame: null,
        tipInFrame: null,
        tipLocation: null,
        metalLocation: null,
        sampleLocation: null
    }
    const [ autoInitData, setAutoInitData ] = useState(resetState);
    
    const handleVideoClick = (x, y, frameData) => {
        var state = initialiseState
        if(!state['inProgress']) {
            return;
        }

        var data = autoInitData
        if(state['step'] === 0){
            //Move the tip out of the frame then click
            state['step'] += 1
            setInitialiseState(state)

            data['initialFrame'] = frameData
            setAutoInitData(data)
            
            setCurrentInstruction("Move the tip into view and in close proximity to the sample, then click anywhere in the video feed.")
            return;
        }
        if(state['step'] === 1){
            //Move the tip close to the sample
            state['step'] += 1
            setInitialiseState(state)

            data['tipInFrame'] = frameData
            setAutoInitData(data)
            
            setCurrentInstruction("Click on the apex of the tip to mark its location.")
            return;
        }
        if(state['step'] === 2){
            //Mark the tip location
            state['step'] += 1
            setInitialiseState(state)

            data['tipLocation'] = [x,y]
            setAutoInitData(data)
            
            setCurrentInstruction("Click at a safe distance above the clean reference metal")
            return;
        }
        if(state['step'] === 3){
            //Mark the clean metal location
            state['step'] += 1
            setInitialiseState(state)

            data['metalLocation'] = [x,y]
            setAutoInitData(data)
            
            setCurrentInstruction("Click at a safe distance above the sample")
            return;
        }
        if(state['step'] === 4){
            //Mark the sample location
            state['step'] += 1
            state['inProgress'] = false
            state['complete'] = true
            setInitialiseState(state)

            data['sampleLocation'] = [x,y]
            setAutoInitData(data)

            scanbotAutoInit()
            setShowWebcam(false)
            return;
        }
        
    };

    const scanbotAutoInit = async () => {
        const response = await fetch('/auto_init_frames', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(autoInitData),
        });

        const data = await response.json()
        if(data['status'] === "success"){
            const imageResponse = await fetch('/get_initialised_frame')
            const blob = await imageResponse.blob()
            const url = URL.createObjectURL(blob);
            setInitialisationImage(url)
        }
    }

    const initialise = () => {
        fetch('/reset_init')
        setInitialiseState({step: 0, inProgress: true, complete: false})
        setAutoInitData(resetState);
        setShowWebcam(true)
        setCurrentInstruction("Move the tip outside the view of the camera then click on the video feed")
    }

    return (
        <div className="control-container">
            <div className='control-content'>
                {initialiseState['complete']
                    ? <img src={ initialisationImage } alt="Inisialisation complete" />
                    : <Webcam
                        onCoordinatesSelected={handleVideoClick}
                        showWebcam={showWebcam}
                    />
                }
                {!initialiseState['inProgress']
                    ? <button className='init-button' onClick={initialise}>Initialise</button>
                    : <p>{currentInstruction}</p>
                }
            </div>
            <GoBack
                cleanUp={() => {return true}}
                navigateTo={'/data-acquisition'}
            />
        </div>
    );
}

export default STMControl