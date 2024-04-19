import React, { useEffect, useState, useRef } from 'react';
import { Sidebar, usePersistedState, GoBack } from './Components';
import { positiveInt, number, positiveNumber } from './Validations';
import emptyFrameIcon from './img/frame.png';
import './styles/Survey.css'

function STSGrid() {
    const initialAllFormData = {
        0: {Vset: '-0.5', Iset: '50', Vmov: '0', Imov: '0' },
        1: {NDC: '5', VDC: '-1', IDC: '10', pxdc: '128', tdc: '0', tbdc: '1'  },
        2: {path: '', s: 'scanbot-sts-grid' }
    }
    const [allFormData, setAllFormData] = usePersistedState('sts-grid-allFormData', initialAllFormData)
    const [running, setRunning] = useState(false)
    const [lastImage,  setLastImage]  = useState({ src: emptyFrameIcon, alt: "blank image", width: 300, height: 300} );
    const [gridGif, setGridGif] = useState([{ src: emptyFrameIcon, alt: "blank image", width: 300, height: 300}] );
    const [lastTimestamp, setLastTimestamp] = useState(0);
    const timerIdRef = useRef(null);
    
    const handleInputChange = (formIndex, name, value, index) => {
        var goahead = true

        // Validations
        const positiveNumbers = ['Imov','Iset','IDC','tdc','tbdc']
        const positiveInts = ['NDC','pxdc']
        const numbers = ['Vset','Vmov', 'VDC']
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
            startSTSGrid()
        }
    };
    
    const stop = () => {
        fetch("/stop")
    }

    const startSTSGrid = () => {
        const userArgs = unpackArgs()

        fetch('/run_stsGrid', {
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
                    URL.revokeObjectURL(gridGif[0]);
                }
        
                setLastImage(image)
                setGridGif([image])
                
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
            title: "Grid Settings",
            inputs: [
                { label: "STS Setpoint Current (pA)",       type: "text", id: "Iset", name: "Iset", value: allFormData[0]['Iset'], description: "(float) Setpoint current applied before acquiring each STS (pA). 0 = leave setting in Nanonis"},
                { label: "STS Setpoint Voltage (V)",        type: "text", id: "Vset", name: "Vset", value: allFormData[0]['Vset'], description: "(float) Bias at which the setpoint is taken (V). 0 = leave setting in Nanonis"},
                { label: "Tip Move Setpoint Current (pA)",  type: "text", id: "Imov", name: "Imov", value: allFormData[0]['Imov'], description: "(float) Change the setpoint current to this value when the tip moves between grid points (pA). 0 = do not change"},
                { label: "Tip Move Setpoint Voltage (V)",   type: "text", id: "Vmov", name: "Vmov", value: allFormData[0]['Vmov'], description: "(float) Change the bias to this value when the tip moves between grid points (V). 0 = do not change"},
            ]
        },
        {
            title: "Drift Correction Settings",
            inputs: [
                { label: "Drift correction after N points", type: "text", id: "NDC",  name: "NDC",  value: allFormData[1]['NDC'],  description: "(int) Perform drift correction after this many points in the grid have been acquired" },
                { label: "Setpoint currect (pA)",           type: "text", id: "IDC",  name: "IDC",  value: allFormData[1]['IDC'],  description: "(float) Change the setpoint current to this value when acquiring images for drift correction (pA). 0 = do not change"},
                { label: "Image bias (V)",                  type: "text", id: "VDC",  name: "VDC",  value: allFormData[1]['VDC'],  description: "(float) Change the bias to this value when acquiring images for drift correction (V). 0 = do not change"},
                { label: "Number of pixels",                type: "text", id: "pxdc", name: "pxdc", value: allFormData[1]['pxdc'], description: "(int) Number of pixels in the drift correction images. 0 = nanonis current setting" },
                { label: "Fwd speed (s/line)",              type: "text", id: "tdc",  name: "tdc",  value: allFormData[1]['tdc'],  description: "(float) Drift correction image speed - Time per line (forward direction) (s). 0 = nanonis current setting" },
                { label: "Bwd speed multiplier",            type: "text", id: "tbdc", name: "tbdc", value: allFormData[1]['tbdc'], description: "(float) Drift correction image speed - Backward direction speed multiplier. E.g. 1=same speed, 2=twice as fast, 0.5=half speed" },
            ]
        },
        {
            title: "Drift correction",
            inputs: [
                { label: "Save path",   type: "text", id: "path", name: "path", value: allFormData[2]['path'], description: "(str) Full path of the desired save location of grid data. Leave blank to save in the current Nanonis Path"},
                { label: "Save suffix", type: "text", id: "s",    name: "s",    value: allFormData[2]['s'],    description: "(str) Filename suffix for the saved grid data"},
            ]
        },
        {
            title: "Actions",
            inputs: [
                { label: `${!running ? 'Start' : 'Stop'} Scanning`, type: "submit", id: "submit", name: "submit", description: "Start/stop the Scanbot STS Grid acquisition", click: handleFormSubmit}
            ]
        }
    ];

    async function fetchGif(){
        if(running){
            const gifResponse = await fetch('/get_gif')
            if(gifResponse.ok){
                const gifBlob = await gifResponse.blob()
                const gifUrl = URL.createObjectURL(gifBlob)
                URL.revokeObjectURL(gridGif);
                var gif = gridGif.slice()
                URL.revokeObjectURL(gif);
                gif['src'] = gifUrl
                setGridGif([gif])
            }
        }
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
                setLastImage(image)
                setLastTimestamp(Date.now())
                
                fetchGif();
            }

            const actionResponse = await fetch('/get_state')
            const actionData     = await actionResponse.json()
            const action = actionData['action']
            const isRunning = actionData['running']

            if(!isRunning || !(action === "stsgrid")) {
                setRunning(false)
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
    }, [running]);
      
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
                <img className="bias-dep-image gif" src={gridGif[0]['src']} alt={gridGif['alt'] }/>
            </div>
            
            <GoBack
                cleanUp={cleanUp}
                navigateTo={'/data-acquisition'}
            />
        </div>
        );
}

export default STSGrid