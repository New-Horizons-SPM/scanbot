import { Card, Footer } from './Components';
import "./styles/Scanbot.css";

const CardRow = () => (
	<div className="card-row">
		<Card className="configuration-card"    title="Configuration" 	 content="Update Scanbot's configuration" navigateTo="/configuration" />
		<Card className="data-acquisition-card" title="Data Acquisition" content="Proceed to data acquisition" 	  navigateTo="/data-acquisition" />
		<Card className="documentation-card"    title="Documentation" 	 content="Read Scanbot's documentation"   url="https://new-horizons-spm.github.io/scanbot/"/>
	</div>
);

const Scanbot = () => {
  	return (
		<div className="scanbot-container">
			<div className="scanbot">
				<header className="scanbot-header">
					<h1>Scanbot</h1>
				</header>
				<div className="scanbot-body">
					<CardRow />
				</div>
			</div>
			<Footer />
		</div>
	);
}

export default Scanbot;
