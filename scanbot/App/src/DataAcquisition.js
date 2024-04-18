import { Footer, Card, GoBack } from './Components';
import "./styles/Scanbot.css";

const CardRow = () => (
	<div className="card-row-4">
		<Card className="survey-card card-4"      title="Survey" 	              content="Survey your sample"                      navigateTo="/survey" />
		<Card className="bias-dep-card card-4"    title="Bias Dependent Imaging"  content="Start a series of bias dependent images" navigateTo="/bias-dep" />
		<Card className="sts-grid-card card-4"    title="STS Grid" 			  	  content="Acquire a drift-corrected STS grid" 	    navigateTo="/sts-grid" />
		<Card className="stm-control-card card-4" title="Automation"     	      content="Tools to assist in STM operation"        navigateTo="/stm-control" />
	</div>
);

const DataAcquisition = () => {
  	return (
		<div className="scanbot-container">
			<div className="scanbot">
				<header className="scanbot-header">
					<h1>Data Acquisition</h1>
				</header>
				<div className="scanbot-body">
					<CardRow />
				</div>
			</div>
            <Footer />
            <GoBack
                cleanUp={() => {return true}}
                navigateTo={'/'}
            />
		</div>
	);
}

export default DataAcquisition;