import React, { useEffect, useState, useRef } from 'react';
import { is_auto_init, positiveNumber, positiveInt, number, checkHook } from './Validations';
import { Sidebar, GoBack, usePersistedState } from './Components';
import Webcam from './Webcam';
import emptyFrameIcon from './img/frame.png';
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
    const [ viewMode, setViewMode] = usePersistedState("control-viewMode","autotipshape")
    const [ autoInitData, setAutoInitData ] = useState(resetState);
    const [ autoTipRunning,  setAutoTipRunning] = useState(false);
    const [lastImage,  setLastImage]  = useState({ src: emptyFrameIcon, alt: "blank image", width: 300, height: 300} );
    const [imprintGif, setImprintGif] = useState([{ src: emptyFrameIcon, alt: "blank image", width: 300, height: 300}] );
    const [ imprintScore, setImprintScore ] = useState({size: 0, sym: 0})
    const [lastTimestamp, setLastTimestamp] = useState(0);
    const timerIdRef = useRef(null);

    // const [allFormData, setAllFormData] = usePersistedState('stm-control-allFormData', {
    const [allFormData, setAllFormData] = usePersistedState("control-allFormData", {
        0: {n: '10', wh: '30',sym: 0.7, size: 2.0, zQA: -0.9, ztip: -5, rng: 1, st: 3, demo: 0, hk_tipShape: 0},
        1: {demo: 0, light: 0, cameraPort: 0}
    });
    
    const startStopAutotipshaping = () => {
        if(initialiseState['inProgress']) {
            console.log("Initialisation is in progress. Cannot tip shape until that process has stopped or completed.")
            return
        }
        setViewMode("autotipshaping")
        console.log("All Form Data Submitted:", allFormData);
        if(autoTipRunning){
            setAutoTipRunning(false)
            stop()
        }else{
            startAutoTipShape()
            console.log("Starting tip shape")
        }
    };

    const handleInputChange = async (formIndex, name, value, index) => {
        var goahead = true

        // Validations
        const positiveNumbers = ['st','wh','sym','size','ztip']
        const negativeNumbers = ['zQA', 'ztip']
        const positiveInts = ['n']
        if(positiveInts.includes(name)) {
            goahead = positiveInt(value)
        }
        
        if(positiveNumbers.includes(name)) {
            goahead = positiveNumber(value)
        }

        if(negativeNumbers.includes(name)) {
            goahead = number(value)
            if(goahead && !value.startsWith('-') && value) {
                value = '-' + value
            }
        }

        var temp = allFormData
        if(goahead) {
            temp = ({
                ...temp,
                [formIndex]: {
                    ...temp[formIndex],
                    [name]: value
                }
            });
        }

        const hooks = ['hk_tipShape']
        if(hooks.includes(name)) {
            temp = await validateDropDowns(temp)
        }

        if(goahead) {
            setAllFormData(temp);
        }
    };

    async function validateDropDowns(temp) {
        const formIndex = 0
        const hookName = 'hk_tipShape'
        const hookIsValid = await checkHook(hookName)
        if(!hookIsValid) {
            temp = {
                ...temp,
                [formIndex]: {
                    ...temp[formIndex],
                    [hookName]: 0
                }
            };
        }

        setAllFormData(temp)

        return temp
    }

    useEffect(() => {
        var temp = allFormData
        validateDropDowns(temp)
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const startAutoTipShape = () => {
        const userArgs = unpackArgs(0)

        fetch('/run_autotipshape', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({userArgs: userArgs}),
        })
        .then(response => response.json())
        .then(data => {
            if(data['status'] === "success"){
                var image = lastImage
                image['src'] = emptyFrameIcon
                if(lastImage){
                    URL.revokeObjectURL(lastImage);
                    URL.revokeObjectURL(imprintGif[0]);
                }
        
                setLastImage(image)
                setImprintGif([image])
                setAutoTipRunning(true)
                console.log('Success:', data);
            }else{
                console.log('Fail', data)
            }
            
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }

    const unpackArgs = (index) => {
        var unpackedArgs = []
        const form = allFormData[index]
        const keys = Object.keys(form)
        for (let index = 0; index < keys.length; index++) {
            const key = '-' + keys[index]
            var param = key + '=' + form[keys[index]]
            unpackedArgs = [...unpackedArgs, param]
        }
        return unpackedArgs
    }

    const stop = () => {
        fetch("/stop")
    }

    useEffect(() => {
        const pollingCallback = async () => {
            const timestamp = lastTimestamp
            const response = await fetch('/image_updates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({timestamp: timestamp}),
            })
            
            if(response.ok){
                const blob = await response.blob()
                const url = URL.createObjectURL(blob);
                
                var image = lastImage
                image['src'] = url
                console.log(url)
                setLastImage(image)
                setLastTimestamp(Date.now())
                
                fetchGif();

                await getImprintScore()
                // const n = parseInt(allFormData[0]['n'])
                // if(index + 2 > n) {
                //     setRunning(false);
                //     stopPolling();
                // }
            }
        };
    
        const startPolling = () => {
          timerIdRef.current = setInterval(pollingCallback, 3000);
        };
    
        const stopPolling = () => {
          clearInterval(timerIdRef.current);
        };
    
        if (autoTipRunning) {
          startPolling();
        }
    
        return () => {
          stopPolling();
        };

        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoTipRunning]);
    
    async function getImprintScore() {
        const response = await fetch('/get_imprint_score')
        const data = await response.json()
        const isRunning = data['running']
        const size = data['size']
        const sym = data['sym']
        setImprintScore({size: size, sym: sym})
        if(!isRunning && autoTipRunning) {
            startStopAutotipshaping()
        }
    }

    async function fetchGif(){
        if(autoTipRunning){
            const gifResponse = await fetch('/get_gif')
            if(gifResponse.ok){
                const gifBlob = await gifResponse.blob()
                const gifUrl = URL.createObjectURL(gifBlob)
                URL.revokeObjectURL(imprintGif);
                var gif = imprintGif.slice()
                URL.revokeObjectURL(gif);
                gif['src'] = gifUrl
                setImprintGif([gif])
            }
        }
    }

    useEffect(() => {
        const handleBeforeUnload = (event) => {
            if (autoTipRunning) {
                // Standard for most browsers
                event.preventDefault();
                // Required for some browsers (e.g., Chrome)
                event.returnValue = '';
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);

        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    }, [autoTipRunning]);

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

    const cancelInit = () => {
        fetch('/reset_init')
        setInitialiseState({step: 0, inProgress: false, complete: false})
        setAutoInitData(resetState);
        setShowWebcam(false)
    }

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
        if(autoTipRunning) {
            console.log("Cannot initialise positions while Automatic Tip Shaping is running.")
            return
        }
        setViewMode("autoinit")
        if(allFormData[1]['demo']) {
            console.log("Starting in demo mode")
            fetch('/demo_init')
            return
        }
        fetch('/reset_init')
        setInitialiseState({step: 0, inProgress: true, complete: false})
        setAutoInitData(resetState);
        setShowWebcam(true)
        setCurrentInstruction("Move the tip outside the view of the camera then click on the video feed")
    }

    useEffect(() => {
        checkAutoInit()
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const checkAutoInit = async () => {
        const isInit = await is_auto_init()
        if(isInit) {
            const imageResponse = await fetch('/get_initialised_frame')
            const blob = await imageResponse.blob()
            const url = URL.createObjectURL(blob);
            setInitialisationImage(url)

            var state = initialiseState
            state['step'] += 0
            state['inProgress'] = false
            state['complete'] = true
            setInitialiseState(state)
        }
    }

    const yesNo       = [{label: 'Yes', value: 1},{label: 'No', value: 0}]
    // const cameraPorts = [{label: '0',   value: 0},{label: '1',  value: 1},{label: '2',  value: 2},{label: '3',  value: 3}]
    const formData = [
        {
            title: "Automatic Tip Shaping",
            inputs: [
                { label: "Tip shaping grid size (NxN)",      type: "number", id: "n",    name: "n",    value: allFormData[0]['n'],    description: "(int) Size of the nxn grid tip tip shape within. The maximum number of attempts will be NxN"},
                { label: "Tip shaping area size (nm x nm)",  type: "number", id: "wh",   name: "wh",   value: allFormData[0]['wh'],   description: "(float) Size of the square scan frame when imaging the clean surface and tip imprint (nm)"},
                { label: "Desired imprint symmetry score",   type: "number", id: "sym",  name: "sym",  value: allFormData[0]['sym'],  description: "(float) Minimum circularity requirement. 0=don't care, 1=perfectly circle"},
                { label: "Desired imprint size score (nm2)", type: "number", id: "size", name: "size", value: allFormData[0]['size'], description: "(float) Max size of the desired tip imprint in units of nm2"},
                { label: "Drift compensation time (s)",      type: "number", id: "st",   name: "st",   value: allFormData[0]['st'],   description: "(int) Time to wait before restarting a scan at a new location (to wait for drift to settle) (s) "},
                { label: "Imprint z-lift (nm)",              type: "number", id: "zQA",  name: "zQA",  value: allFormData[0]['zQA'],  description: "(float) z-lift when performing a light tip shape to asses quality of tip (nm)"},
                { label: "Reshape z-lift (nm)",              type: "number", id: "ztip", name: "ztip", value: allFormData[0]['ztip'], description: "(float) z-lift when performing a tip shape to alter the tip (nm)"},
                { label: "Randomise z-lift?",                type: "select", id: "rng",  name: "rng",  value: allFormData[0]['rng'],  description: "(int) Flag to randomise tip-reshaping z-lift from 1 nm to above value.", options: yesNo},
                { label: "Call hook hk_tipShape?",           type: "select", id: "hk_tipShape", name: "hk_tipShape", value: allFormData[0]['hk_tipShape'], description: "(int) Flag to call the hook hk_tipShape. Use this hook to adjust the tip shaping parameters based on size/symmetry scores, or based on the image of the tip imprint itself. 0=Don't call, 1=Call", options: yesNo},
                { label: "Run in demo mode?",                type: "select", id: "demo", name: "demo", value: allFormData[0]['demo'], description: "(int) Flag to call in demo mode. In demo mode, acquired data will be replaced with preloaded data", options: yesNo},
                { label: `${!autoTipRunning ? 'Start' : 'Stop'} `,  type: "submit", id: "autoSubmit", name: "autoSubmit", description: "Start/Stop the automatic tip-shaping routine", click: startStopAutotipshaping},
            ]
        },
        {
            title: "Initialise Tip and Sample Positions",
            inputs: [
                // { label: "Camera Port", type: "select", id: "cameraPort", name: "cameraPort", value: allFormData[1]['cameraPort'], description: "(int) STM camera port number. Usually 0; 1 for laptops with a inbuilt webcam", options: cameraPorts},
                // { label: "Use hk_light.py to control light?", type: "select", id: "light", name: "light", value: allFormData[1]['light'], description: "(int) Flag to call the hk_light.py hook when controlling the STM light", options: yesNo},
                { label: "Run in demo mode?", type: "select", id: "demo", name: "demo", value: allFormData[1]['demo'], description: "(int) Flag to call in demo mode. In demo mode, the camerafeed will be replaced with a pre-recorded video", options: yesNo},
                { label: "Initialise",        type: "submit", id: "initSubmit", name: "initSubmit", description: "Reinitialise the tip, sample, and metal locations using the camera feed", click: initialise},
            ]
        },
    ];

    useEffect(() => {
        const handleBeforeUnload = (event) => {
            if (autoTipRunning || initialiseState['inProgress']) {
                // Standard for most browsers
                event.preventDefault();
                // Required for some browsers (e.g., Chrome)
                event.returnValue = '';
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);

        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
    }, [autoTipRunning,initialiseState]);

    const cleanUp = () => {
        if(autoTipRunning || initialiseState['inProgress']) {
            const userResponse = window.confirm("Automatic Tip Shaping in progress. If you proceed, the scan will be stopped.");
            if(userResponse){
                stop()
                return true
            }
            return false
        }
        return true
    }

    return (
        <div className="control-container">
            <div className='control-sidebar-container'>
                <Sidebar
                    formData={formData}
                    onInputChange={handleInputChange}
                />
            </div>
            <div className='control-main-content'>
                {viewMode==="autoinit"
                    ?
                    <div className='autoinit-content'>
                        {initialiseState['complete']
                            ? <img src={ initialisationImage } alt="Inisialisation complete" />
                            : <Webcam
                                onCoordinatesSelected={handleVideoClick}
                                showWebcam={showWebcam}
                            />
                        }
                        {!initialiseState['inProgress']
                            ? <p/>
                            : <div>
                                <p>{currentInstruction}</p>
                                <button className='init-button' onClick={cancelInit}>Cancel</button>
                            </div>
                        }
                    </div>
                    :
                    <div>
                        <div className='autotipshape-content'>
                            <img className="autotipshape-image autotipshape-last-image" src={lastImage['src']} alt={lastImage['alt'] }/>
                            <img className="autotipshape-image autotipshape-gif" src={imprintGif[0]['src']} alt={imprintGif['alt'] }/>
                        </div>
                        <p className="imprint-score">Last imprint size: {imprintScore['size']} nm<sup>2</sup>, symmetry: {imprintScore['sym']}</p>
                    </div>
                }
            </div>
            <GoBack
                cleanUp={cleanUp}
                navigateTo={'/data-acquisition'}
            />
        </div>
    );
}

export default STMControl