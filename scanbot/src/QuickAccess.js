export const QuickForm = ({ title, inputs, onInputChange, formIndex, showSubmitButton, onSubmit, submitText, type }) => {
    const [isCollapsed, setIsCollapsed] = useState(false);

    const toggleCollapse = () => {
        setIsCollapsed(!isCollapsed);
    };

    return (
        <div className={type + "-form"}>
            <div className={type + "-form-header"} onClick={toggleCollapse}>
                <h3>{title}</h3>
                {type === "sidebar" && <img src={collapseIcon} alt="Collapse" className="form-collapse-icon" style={{ transform: isCollapsed ? 'rotate(0deg)' : 'rotate(180deg)' }} />}
            </div>
            {(!isCollapsed || type === "panel") && (
                <div className={type + "-form-body"}>
                    {inputs.map((input, index) => (
                        <div key={index} className={type + "-input-group"}>
                            <label htmlFor={input.id}>{input.label}</label>
                            {input.type === "select" ? (
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
                            ) : (
                                <input
                                type={input.type} 
                                id={input.id} 
                                name={input.name}
                                title={input.description}
                                value={input.value}
                                onChange={(e) => onInputChange(formIndex, input.name, e.target.value, index)}
                            />
                            )}
                        </div>
                    ))}
                    {showSubmitButton && <button className = {type + "-form-submit"} type="button" onClick={onSubmit}>{submitText}</button>}
                </div>
            )}
        </div>
    );
};

export const Sidebar = ({ formData, onInputChange, onSubmit, submitText }) => {
    return (
        <aside className='quick-access'>
            {formData.map((form, index) => (
                <QuickForm 
                    key={index}
                    title={form.title}
                    inputs={form.inputs}
                    onInputChange={onInputChange}
                    formIndex={index}
                    onSubmit={onSubmit}
                    submitText={submitText}
                    showSubmitButton={index === formData.length - 1}
                    type="panel"
                />
            ))}
        </aside>
    );
};