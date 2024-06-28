import { useState, useEffect } from 'react';
import { Card, Footer } from './Components';
import { getResponse } from './Validations';
import "./styles/Scanbot.css";

function Scanbot() {
	const [configFound, setConfigFound] = useState(true)
	const [isConnected, setIsConnected] = useState(true)
	const [is2Update,    setIsUp2date]  = useState(true)

	const CardRow = () => (
		<div className="card-row">
			<Card className="configuration-card"    title="Configuration" 	 content="Update Scanbot's configuration" navigateTo="/configuration" />
			<Card className="data-acquisition-card" title="Data Acquisition" content="Proceed to data acquisition" 	  navigateTo="/data-acquisition" />
			<Card className="documentation-card"    title="Documentation" 	 content="Read Scanbot's documentation"   url="https://new-horizons-spm.github.io/scanbot/"/>
		</div>
	);

	const checkConfig = async () => {
		const hasConfig = await getResponse('/has_config')
		setConfigFound(hasConfig)
	}

	const testConnection = async () => {
		const hasConnection = await getResponse('/test_connection')
		setIsConnected(hasConnection)
	}
	
	const checkUpdates = async () => {
		const isUpdated = await getResponse('/check_updates')
		setIsUp2date(isUpdated)
	}

	useEffect(() => {
		checkConfig()
		testConnection()
		checkUpdates()
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	return (
		<div className="scanbot-container">
			<div className="scanbot">
				<header className="scanbot-header">
					<h1>Scanbot</h1>
				</header>
				{isConnected ? <div/> : <p className='config-warning'><strong>Warning:</strong> Could not connect to Nanonis. Please check configured IP and ports and make sure Nanonis V5 is running.</p>}
				{configFound ? <div/> : <p className='config-warning'><strong>Warning:</strong> A configuration file has not been found - using default parameters. Accept configuration to remove this warning.</p>}
				{is2Update   ? <div/> : <p className='config-warning'>A newer version of Scanbot is available.</p>}
				<div className="scanbot-body">
					<CardRow />
				</div>
			</div>
			<Footer />
		</div>
	);
}
export default Scanbot;
