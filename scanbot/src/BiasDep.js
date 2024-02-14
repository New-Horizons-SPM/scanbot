import React, { useEffect, useState, useRef } from 'react';
import { Sidebar, usePersistedState, GoBack } from './Components';
import { positiveInt, number, positiveNumber } from './Validations';
import emptyFrameIcon from './img/frame.png';
import './styles/Survey.css'

function BiasDep() {
    const initialAllFormData = {
        0: {n: '3', bi: '-1', bf: '1', s: 'scanbot-biasdep' },
        1: {px: '0', lx: '0', tlf: '0', tb: '1' },
        2: {bdc: '0.5', pxdc: '128', lxdc: '0', tdc: '0', tbdc: '1'  }
    }
    const [allFormData, setAllFormData] = usePersistedState('bias-dep-allFormData', initialAllFormData)
    const [running, setRunning] = useState(false)
    const [lastImage,  setLastImage]  = useState({ src: emptyFrameIcon, alt: "blank image", width: 300, height: 300} );
    const [biasDepGif, setBiasDepGif] = useState([{ src: emptyFrameIcon, alt: "blank image", width: 300, height: 300}] );
    const [imageIndex, setImageIndex] = useState(0);
    const [lastTimestamp, setLastTimestamp] = useState(0);
    const timerIdRef = useRef(null);
    
    const handleInputChange = (formIndex, name, value, index) => {
        var goahead = true

        // Validations
        const positiveNumbers = ['tlf','tb','pxdc','lxdc','tdc','tbdc']
        const positiveInts = ['n', 'px', 'lx']
        const numbers = ['bi','bf', 'bdc']
        if(positiveInts.includes(name)) {
            goahead = positiveInt(value)
        }
        if(numbers.includes(name)) {
            goahead = number(value)
        }
        if(positiveNumbers.includes(name)) {
            goahead = positiveNumber(value)
        }

        if(goahead) {
            setAllFormData({
                ...allFormData,
                [formIndex]: {
                    ...allFormData[formIndex],
                    [name]: value
                }
            });
        }
    };
    
    const handleFormSubmit = () => {
        if(running){
            setRunning(false)
            stop()
        }else{
            startBiasDep()
        }
    };
    
    const stop = () => {
        fetch("/stop")
    }

    const startBiasDep = () => {
        const userArgs = unpackArgs()

        fetch('/run_biasdep', {
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
                    URL.revokeObjectURL(biasDepGif[0]);
                }
        
                setLastImage(image)
                setBiasDepGif([image])
                setImageIndex(0)
                setRunning(true)
                console.log('Success:', data);
            }else{
                console.log('Fail', data)
            }
            
        })
        .catch((error) => {
            console.error('Error:', error);
        });
    }
    
    const unpackArgs = () => {
        var unpackedArgs = []
        const formIdx = Object.keys(allFormData)
        for (let idx = 0; idx < formIdx.length; idx++) {
            const form = allFormData[formIdx[idx]]
            const keys = Object.keys(form)
            for (let index = 0; index < keys.length; index++) {
                const key = '-' + keys[index]
                var param = key + '=' + form[keys[index]]
                unpackedArgs = [...unpackedArgs, param]
            }
        }
        console.log("unpacked")
        console.log(unpackedArgs)
        return unpackedArgs
    }
    
    const formData = [
        {
            title: "Settings",
            inputs: [
                { label: "Number of images",  type: "text", id: "n",  name: "n",  value: allFormData[0]['n'],  description: "(int) Number of images to take b/w initial and final bias"},
                { label: "Initial Bias (V)",  type: "text", id: "bi", name: "bi", value: allFormData[0]['bi'], description: "(float) Initial Bias (V)"},
                { label: "Final Bias (V)",    type: "text", id: "bf", name: "bf", value: allFormData[0]['bf'], description: "(float) Final Bias (V)"},
                { label: "Filename suffix",   type: "text",   id: "s",  name: "s",  value: allFormData[0]['s'],  description: "(str) Suffix for the set of bias dependent sxm files"},
            ]
        },
        {
            title: "Scan parameters",
            inputs: [
                { label: "Pixels", type: "text",  id: "px", name: "px", value: allFormData[1]['px'], description: "(int) Number of pixels in each scan. 0 = nanonis current setting" },
                { label: "Lines",  type: "text",  id: "lx", name: "lx", value: allFormData[1]['lx'], description: "(int) Number of lines in images. 0 = same as number of pixels or nanonis current setting" },
                { label: "Fwd speed (s/line)",   type: "text",  id: "tlf", name: "tlf", value: allFormData[1]['tlf'], description: "(float) Time per line (forward direction) (s). 0 = nanonis current setting" },
                { label: "Bwd speed multiplier", type: "text",  id: "tb",  name: "tb",  value: allFormData[1]['tb'], description: "(float) Backward direction speed multiplier. E.g. 1=same speed, 2=twice as fast, 0.5=half speed" },
            ]
        },
        {
            title: "Drift correction",
            inputs: [
                { label: "Bias (V) (0=off)",     type: "text", id: "bdc",  name: "bdc",  value: allFormData[2]['bdc'],  description: "(float) Bias of the drift correction images (V). 0 = dc off"},
                { label: "Pixels",               type: "text", id: "pxdc", name: "pxdc", value: allFormData[2]['pxdc'], description: "(int) Number of pixels in drift correct images."},
                { label: "Lines",                type: "text", id: "lxdc", name: "lxdc", value: allFormData[2]['lxdc'], description: "(int) Number of lines in drift correct image. 0=keep same ratio as px:lx"},
                { label: "Fwd speed (s/line)",   type: "text", id: "tdc",  name: "tdc",  value: allFormData[2]['tdc'],  description: "(float) Time per line (forward direction) (s)"},
                { label: "Bwd speed multiplier", type: "text", id: "tbdc", name: "tbdc", value: allFormData[2]['tbdc'], description: "(float) Backward direction speed multiplier. E.g. 1=same speed, 2=twice as fast, 0.5=half speed" },
            ]
        },
        {
            title: "Actions",
            inputs: [
                { label: `${!running ? 'Start' : 'Stop'} Scanning`, type: "submit", id: "submit", name: "submit", description: "Start/stop the Scanbot bias-dependent image series", click: handleFormSubmit}
            ]
        }
    ];

    async function fetchGif(){
        if(running){
            console.log("step 1")
            const gifResponse = await fetch('/get_gif')
            if(gifResponse.ok){
                console.log("Step 2")
                const gifBlob = await gifResponse.blob()
                const gifUrl = URL.createObjectURL(gifBlob)
                URL.revokeObjectURL(biasDepGif);
                var gif = biasDepGif.slice()
                URL.revokeObjectURL(gif);
                gif['src'] = gifUrl
                setBiasDepGif([gif])
                console.log(gifUrl)
            }
        }
    }

    useEffect(() => {
        const pollingCallback = async () => {
            const timestamp = lastTimestamp
            const index = imageIndex
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
                setLastImage(image)
                setImageIndex(index + 1)
                setLastTimestamp(Date.now())
                
                fetchGif();

                const n = parseInt(allFormData[0]['n'])
                if(index + 2 > n) {
                    setRunning(false);
                    stopPolling();
                }
            }
        };
    
        const startPolling = () => {
          timerIdRef.current = setInterval(pollingCallback, 3000);
        };
    
        const stopPolling = () => {
          clearInterval(timerIdRef.current);
        };
    
        if (running) {
          startPolling();
        }
    
        return () => {
          stopPolling();
        };

        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [running, imageIndex]);
      
    useEffect(() => {
        const handleBeforeUnload = (event) => {
            if (running) {
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
    }, [running]);

    const cleanUp = () => {
        if(running) {
            const userResponse = window.confirm("There is a scan in progress. If you proceed, the scan will be stopped.");
            if(userResponse){
                stop()
                return true
            }
            return false
        }
        return true
    }

    return (
        <div className="survey-container">
            <div className='sidebar-container'>
                <Sidebar
                    formData={formData}
                    onInputChange={handleInputChange}
                />
            </div>
            <div className='bias-dep-main-content'>
                <img className="bias-dep-image last-image" src={lastImage['src']} alt={lastImage['alt'] }/>
                <img className="bias-dep-image gif" src={biasDepGif[0]['src']} alt={biasDepGif['alt'] }/>
            </div>
            
            <GoBack
                cleanUp={cleanUp}
                navigateTo={'/data-acquisition'}
            />
        </div>
        );
}

export default BiasDep