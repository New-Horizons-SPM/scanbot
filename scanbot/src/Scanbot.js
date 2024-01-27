import { useState, useEffect } from 'react';
import { Card, Footer } from './Components';
import { getResponse } from './Validations';
import "./styles/Scanbot.css";

function Scanbot() {
	const [configFound, setConfigFound] = useState(true)

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
	useEffect(() => {
		checkConfig()
	// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	return (
		<div className="scanbot-container">
			<div className="scanbot">
				<header className="scanbot-header">
					<h1>Scanbot</h1>
				</header>
				{configFound ? <div/> : <p className='config-warning'><strong>Warning:</strong> A configuration file has not been found - using default parameters. Accept configuration to remove this warning.</p>}
				<div className="scanbot-body">
					<CardRow />
				</div>
			</div>
			<Footer />
		</div>
	);
}
export default Scanbot;
