import React, { useState, useEffect } from "react";
import { useNavigate } from 'react-router-dom';
import { GoBack } from "./Components";
import "./styles/Configuration.css";

function Configuration() {
  let navigate = useNavigate();

	const [config, setConfig] = useState([]);
  const [configForm, setConfigForm] = useState([]);

	useEffect(() => {
		fetch("/scanbot_config").then((res) =>
			res.json().then((data) => {
        var loadedConfig = []
        for (const [key, value] of Object.entries(data.config)) {
          let newConfig = {parameter: key, value: value}
          loadedConfig = [...loadedConfig,newConfig]
        }
				setConfig(loadedConfig);
			})
		);
	}, []);

  useEffect(() => {
    setConfigForm(config.map((item,index) => (
      <div className="config-form" key={index}>
        <label className="config-label">{item.value[0]}</label>
        <input className="config-input"
          type="text"
          name="value"
          placeholder={item.value[0]}
          title={item.value[1]}
          value={item.value[3]}
          onChange={(e) => handleFormChange(index,e)}
        />
      </div>
    )));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config]);

  const handleFormChange = (index,event) => {
    let data = [...config]
    data[index][event.target.name][3] = event.target.value;
    setConfig(data);
  }

  const formSubmit = (event) => {
    event.preventDefault();
    fetch('/save_config', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({config: config}),
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        navigate('/');
    })
    .catch((error) => {
        console.error('Error:', error);
    });
  }

  const cleanUp = () => {
    const userResponse = window.confirm("Leave without saving changes?");
    if(userResponse){
        return true
    }
    return false
  }
  
	return (
		<div className="config-container">
			<header className="config-header">
				<h1>Scanbot Configuration</h1>
        <form onSubmit={formSubmit}>
            {configForm}
            <button type="submit">Accept Configuration</button>
        </form>
			</header>
      <GoBack
          cleanUp={cleanUp}
          navigateTo={'/'}
      />
		</div>
	);
}

export default Configuration;
