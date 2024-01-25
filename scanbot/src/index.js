import React                            from 'react';
import ReactDOM                         from 'react-dom/client';
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Scanbot                          from './Scanbot';
import Configuration                    from './Configuration';
import DataAcquisition                  from './DataAcquisition';
import Survey                           from './Survey';
import BiasDep                          from './BiasDep';
import STMControl                       from './STMControl';
import './styles/index.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <BrowserRouter>
    <Routes>
        <Route path="/"                 element={<Scanbot />} />
        <Route path="/configuration"    element={<Configuration />} />
        <Route path="/data-acquisition" element={<DataAcquisition />} />
        <Route path="/survey"           element={<Survey />} />
        <Route path="/bias-dep"         element={<BiasDep />} />
        <Route path="/stm-control"      element={<STMControl />} />
    </Routes>
  </BrowserRouter>
);
