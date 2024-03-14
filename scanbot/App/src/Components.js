import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import collapseIcon from './img/up.png';
import backIcon from './img/back-button.png';
import './styles/Components.css';

export function usePersistedState(key, initialState) {
    const [state, setState] = useState(() => {
        const savedState = localStorage.getItem(key);
        return savedState ? JSON.parse(savedState) : initialState;
    });

    useEffect(() => {
        localStorage.setItem(key, JSON.stringify(state));
    }, [key, state]);

    return [state, setState];
}

export const GoBack = ({cleanUp,navigateTo}) => {
    let navigate = useNavigate();

    const handleClick = () => {
        if(cleanUp()) {
            navigate(navigateTo)
        }
    };

    return (
        <button className="back-button" onClick={handleClick}>
            <img src={backIcon} alt="Go back" />
        </button>
    );
}

export const Card = ({ title, content, navigateTo, className, url}) => {
	let navigate = useNavigate();

	const handleClick = () => {
        if(url) {window.open(url, '_blank', 'noopener,noreferrer')}
        if(navigateTo){navigate(navigateTo)}
        
    };
	
	return (
		<div className={"card " + className} onClick={handleClick}>
			<h3>{title}</h3>
			<p>{content}</p>
		</div>
	)
};

export const Form1 = ({ title, inputs, onInputChange, formIndex, showSubmitButton, onSubmit, submitText }) => {
    const [isCollapsed, setIsCollapsed] = useState(false);

    const toggleCollapse = () => {
        setIsCollapsed(!isCollapsed);
    };

    return (
        <div className="sidebar-form">
            <div className="sidebar-form-header" onClick={toggleCollapse}>
                <h3>{title}</h3>
                {<img src={collapseIcon} alt="Collapse" className="form-collapse-icon" style={{ transform: isCollapsed ? 'rotate(0deg)' : 'rotate(180deg)' }} />}
            </div>
            {(!isCollapsed) && (
                <div className="sidebar-form-body">
                    {inputs.map((input, index) => (
                        <div key={index} className="sidebar-input-group">
                            {(() => {
                                switch (input.type) {
                                    case "select":
                                        return (
                                            <div>
                                                <label htmlFor={input.id}>{input.label}</label>
                                                <select
                                                    id={input.id}
                                                    name={input.name}
                                                    title={input.description}
                                                    value={input.value}
                                                    onChange={(e) => onInputChange(formIndex, input.name, e.target.value, index)}
                                                >
                                                {input.options.map((option, idx) => (
                                                    <option key={idx} value={option.value}>{option.label}</option>
                                                ))}
                                                </select>
                                            </div>
                                        );
                                    
                                    case "submit":
                                        return (
                                            <div>
                                                <br></br>
                                                <button
                                                    className = "sidebar-form-submit"
                                                    type="button"
                                                    onClick={input.click}>{input.label}
                                                </button>
                                            </div>
                                        );

                                    default:
                                        return (
                                            <div>
                                                <label htmlFor={input.id}>{input.label}</label>
                                                <input
                                                    type={input.type} 
                                                    id={input.id} 
                                                    name={input.name}
                                                    title={input.description}
                                                    value={input.value}
                                                    onChange={(e) => onInputChange(formIndex, input.name, e.target.value, index)}
                                                />
                                            </div>
                                        );
                                }
                            })()}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export const Sidebar = ({ formData, onInputChange, onSubmit, submitText }) => {
    return (
        <aside className='sidebar'>
            {formData.map((form, index) => (
                <Form1 
                    key={index}
                    title={form.title}
                    inputs={form.inputs}
                    onInputChange={onInputChange}
                    formIndex={index}
                />
            ))}
        </aside>
    );
};

export const Footer = () => {
    return (
        <footer className="footer">
            <div className="footer-section footer-contact">
                <h3>Contact</h3>
                <p>
                    Julian Ceddia<br/>
                    julian.ceddia@monash.edu<br/>
                    Monash University, Melbourne, Australia
                </p>
            </div>
            <div className="footer-section footer-projects">
                <h3>Projects</h3>
                <ul>
                    <li><a href="https://github.com/New-Horizons-SPM/G80SXM" target="_blank" rel="noopener noreferrer">G80SXM</a></li>
                    <li><a href="https://github.com/New-Horizons-SPM/nanonisTCP" target="_blank" rel="noopener noreferrer">nanonisTCP</a></li>
                    <li><a href="https://github.com/ceds92/Central-Equation-Solver" target="_blank" rel="noopener noreferrer">2D TISE Solver</a></li>
                    {/* Add more links as needed */}
                </ul>
            </div>
        </footer>
    );
};