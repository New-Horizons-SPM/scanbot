import React, { useEffect, useState, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Sidebar, usePersistedState, GoBack } from './Components';
import { checkHook, is_auto_init, positiveInt, integer, positiveNumber } from './Validations';
import { Gallery } from "react-grid-gallery";
import emptyFrameIcon from './img/frame.png';
import './styles/Survey.css'

function useQuery() {
    return new URLSearchParams(useLocation().search);
}

function Survey() {
    const [allFormData, setAllFormData] = usePersistedState('survey-allFormData', {
        0: {n: '3', dx: '30'},
        1: {nx: '1', ny: '1', zStep: '50', xStep: '100', yStep: '100', zV: '180', zF: '2000', xyV: '150', xyF: '2200'},
        2: {px: '256', bias: '1', xy: '30', s: 'scanbot_survey', st: '2'},
        3: {autotip: 0, hk_survey: 0, hk_classifier: 0}
    });
    const [surveyRunning, setSurveyRunning] = useState(false);
    const [surveyImages,  setSurveyImages]  = useState([
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
        { src: emptyFrameIcon, alt: "blank image", width: 300, height: 300},
    ]);
    const [surveyIndex, setSurveyIndex]             = useState(0);
    // const [surveyFinalIndex, setSurveyFinalIndex]   = useState(1);
    const [surveyTimestamp, setSurveyTimestamp]     = useState(0);
    const [galleryRowHeight, setGalleryRowHeight]   = useState(300);
    const timerIdRef = useRef(null);
    const navigate = useNavigate();
    let query = useQuery();
    const location = useLocation();
    const { action } = location.state || {}

    const handleInputChange = async (formIndex, name, value, index) => {
        var goahead = true

        // Validations
        const positiveNumbers = ['zV','xyV','zF','xyF','dx','xy']
        const positiveInts = ['n','nx','ny','zStep', 'px', 'st']
        const integers = ['xStep','yStep']
        if(positiveInts.includes(name)) {
            goahead = positiveInt(value)
        }
        if(integers.includes(name)) {
            goahead = integer(value)
        }
        if(positiveNumbers.includes(name)) {
            goahead = positiveNumber(value)
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

        if(formIndex === 3) {
            temp = await validateDropDowns(temp)
        }

        if(goahead) {
            setAllFormData(temp);
        }
    };

    useEffect(() => {
        startAction()
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [action]);

    async function startAction() {
        if(!action) { return }
        const response = await fetch('/get_state')
        const data = await response.json()
        const isRunning = data['running']
        
        if(!isRunning) {
            navigate('/survey');
        }

        if(action === 'survey') {
            await fetch('/remove_temp')
            setUpSurvey()
        }
    }

    async function validateDropDowns(temp) {
        const formIndex = 3
        const name = 'autotip'
        const isInit = await is_auto_init("/is_auto_init")
        if(!isInit) {
            temp = {
                ...temp,
                [formIndex]: {
                    ...temp[formIndex],
                    [name]: 0
                }
            };
        }

        var hookName = 'hk_classifier'
        var hookIsValid = await checkHook(hookName)
        if(!hookIsValid) {
            temp = {
                ...temp,
                [formIndex]: {
                    ...temp[formIndex],
                    [hookName]: 0
                }
            };
        }

        hookName = 'hk_survey'
        hookIsValid = await checkHook(hookName)
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

    const handleFormSubmit = () => {
        console.log("All Form Data Submitted:", allFormData);
        if(surveyRunning){
            setSurveyRunning(false)
            stop()
        }else{
            startSurvey()
        }
    };

    const startSurvey = () => {
        const userArgs = unpackArgs()
        
        fetch('/run_survey', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({userArgs: userArgs}),
        })
        .then(response => response.json())
        .then(data => {
            if(data['status'] === "success"){
                setUpSurvey()
                console.log('Success:', data);
            }else{
                console.log('Fail', data)
            }
        })
        .catch((error) => {
            alert("Scanbot Error: " + error);
            console.error('Error:', error);
        });
    }
    const setUpSurvey = () => {
        const n = parseInt(allFormData[0]['n'])
        const newRowHeight = Math.floor(900/n)
        // const newRowHeight = Math.floor(0.9*window.innerHeight/n)
        setGalleryRowHeight(newRowHeight)
        var images = []
        for (let i = 0; i < n**2; i++) {
            images.push({src: emptyFrameIcon, alt: 'Survey Image', width: newRowHeight , height: newRowHeight})
        }
        
        if(surveyImages){
            for (let i = 0; i < surveyImages.length; i++) {
                URL.revokeObjectURL(surveyImages[i]);
            }
        }
        setSurveyImages(images)
        setSurveyIndex(0)

        setSurveyRunning(true)
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
        return unpackedArgs
    }

    const stop = () => {
        fetch("/stop")
    }

    const yesNo = [{label: 'Yes', value: 1},{label: 'No', value: 0}]
    const formData = [
        {
            title: "Fine Grid Parameters",
            inputs: [
                { label: "Fine grid size",  type: "text", id: "n",  name: "n",  value: allFormData[0]['n'],  description: "(int) Size of the nxn grid of scans"},
                { label: "Scan centre-centre spacing (nm)",  type: "number", id: "dx",  name: "dx",  value: allFormData[0]['dx'],  description: "(float) Distance to move the scan frame after each image (nm)"},
            ]
        },
        {
            title: "Coarse Grid Parameters",
            inputs: [
                { label: "Coarse grid x size",      type: "text", id: "nx",    name: "nx", value: allFormData[1]['nx'], description: "(int) Size of the nx x ny grid of surveys. This sets up nx x ny surveys each taken after moving the course piezo in x/y", min: 1, max: 100},
                { label: "Coarse grid y size",      type: "text", id: "ny",    name: "ny", value: allFormData[1]['ny'], description: "(int) Size of the nx x ny grid of surveys. This sets up nx x ny surveys each taken after moving the course piezo in x/y", min: 1, max: 100},
                { label: "Motor steps Z",           type: "text", id: "zStep", name: "zStep", value: allFormData[1]['zStep'], description: "(int) Number of motor steps between surveys in the X direction. Negative value snakes course grid in opposite direction"},
                { label: "Motor steps X",           type: "text", id: "xStep", name: "xStep", value: allFormData[1]['xStep'], description: "(int) Number of motor steps between surveys in the X direction. Negative value snakes course grid in opposite direction"},
                { label: "Motor steps Y",           type: "text", id: "yStep", name: "yStep", value: allFormData[1]['yStep'], description: "(int) Number of motor steps between surveys in the Y direction. Negative value snakes course grid in opposite direction"},
                { label: "Piezo voltage Z (V)",     type: "text", id: "zV",    name: "zV", value: allFormData[1]['zV'], description: "(float) Piezo voltage when moving motor steps in the Z direction"},
                { label: "Piezo Frequency Z (Hz)",  type: "text", id: "zF",    name: "zF", value: allFormData[1]['zF'], description: "(float) Piezo frequency when moving motor steps in the Z direction"},
                { label: "Piezo voltage XY (V)",    type: "text", id: "xyV",   name: "xyV", value: allFormData[1]['xyV'], description: "(float) Piezo voltage when moving motor steps in the X/Y directions"},
                { label: "Piezo Frequency XY (Hz)", type: "text", id: "xyF",   name: "xyF", value: allFormData[1]['xyF'], description: "(float) Piezo frequency when moving motor steps in the X/Y direction"},
            ]
        },
        {
            title: "Scan Parameters",
            inputs: [
                { label: "Pixels",          type: "number",  id: "px",   name: "px",   value: allFormData[2]['px'],   description: "(int) Number of pixels in each scan" },
                { label: "Bias (V)",        type: "number",  id: "bias", name: "bias", value: allFormData[2]['bias'], description: "(float) Scan bias (V). 0 = current setting in nanonis." },
                { label: "Scan size (nm)",  type: "number",  id: "xy",   name: "xy",   value: allFormData[2]['xy'],   description: "(float) Length and width of the scan frame (nm)"},
                { label: "Filename suffix", type: "text",    id: "s",    name: "s",    value: allFormData[2]['s'],    description: "(str) Suffix at the end of autosaved sxm files"},
                { label: "Settle drift wait time (s)", type: "number", id: "st", name: "st", value: allFormData[2]['st'],    description: "(float) Each scan will restart after waiting this much time for the drift to settle"},
            ]
        },
        {
            title: "Misc",
            inputs: [
                { label: "Automated Tip Shaping?", type: "select",  id: "autotip",       name: "autotip",       options: yesNo, value: allFormData[3]['autotip'],       description: "(boolean) Flag to initiate automated tip shaping when a series of 'bad' images is detected in a row. You must first run auto initialisation for this to work." },
                { label: "Call hk_classifier.py?", type: "select",  id: "hk_classifier", name: "hk_classifier", options: yesNo, value: allFormData[3]['hk_classifier'], description: "(boolean) When auto tip shaping is on, call the custom image classifier to determine if the tip is good or bad?" },
                { label: "Call hk_survey.py?",     type: "select",  id: "hk_survey",     name: "hk_survey",     options: yesNo, value: allFormData[3]['hk_survey'],     description: "(boolean) Call the hook hk_survey.py after each image in the survey completes?" },
            ]
        },
        {
            title: "Actions",
            inputs: [
                { label: `${!surveyRunning ? 'Start' : 'Stop'} Survey`, type: "submit", id: "submit", name: "submit", description: "Start/stop the Scanbot survey", click: handleFormSubmit}
            ]
        }
    ];

    useEffect(() => {
        const pollingCallback = async () => {
            const timestamp = surveyTimestamp
            const index = surveyIndex
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
                
                var images = surveyImages
                images[index]['src'] = url
                setSurveyImages(images)
                setSurveyIndex(index + 1)
                setSurveyTimestamp(Date.now())
            }

            const actionResponse = await fetch('/get_state')
            const actionData     = await actionResponse.json()
            const action = actionData['action']
            const isRunning = actionData['running']

            if(!isRunning || !(action === "survey")) {
                setSurveyRunning(false)
            }

            if(action === "movetip") {
                // navigate('/stm-control?action=movetip'); // Redirect to the AutoTipShape page
                navigate('/stm-control', {state: { action: 'movetip' }})
            }
        };
    
        const startPolling = () => {
          timerIdRef.current = setInterval(pollingCallback, 3000);
        };
    
        const stopPolling = () => {
          clearInterval(timerIdRef.current);
        };
    
        if (surveyRunning) {
          startPolling();
        }
    
        return () => {
          stopPolling();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, [surveyRunning, surveyIndex]);
    
      useEffect(() => {
        const handleBeforeUnload = (event) => {
            if (surveyRunning) {
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
    }, [surveyRunning]);

    const cleanUp = () => {
        if(surveyRunning) {
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
        <div className='survey-main-content'>
            <div className='survey-image-grid'>
                <Gallery
                    images={surveyImages}
                    rowHeight={galleryRowHeight}
                />
            </div>
        </div>
        <GoBack
            cleanUp={cleanUp}
            navigateTo={'/data-acquisition'}
        />
    </div>
    );
}

export default Survey;