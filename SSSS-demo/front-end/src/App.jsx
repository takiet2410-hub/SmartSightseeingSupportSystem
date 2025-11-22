import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomePage from './pages/HomePage';
import ModuleBeforePage from './pages/modules/ModuleBeforePage';
import ResultsBeforePage from './pages/modules/ResultsBeforePage';
import ModuleDuringPage from './pages/modules/ModuleDuringPage';
import ResultsDuringPage from './pages/modules/ResultsDuringPage';
import ModuleAfterPage from './pages/modules/ModuleAfterPage';
import ResultsAfterPage from './pages/modules/ResultsAfterPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-bg"></div>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          
          {/* Module Before */}
          <Route path="/recommend" element={<ModuleBeforePage />} />
          <Route path="/recommend/results" element={<ResultsBeforePage />} />
          
          {/* Module During */}
          <Route path="/identify" element={<ModuleDuringPage />} />
          <Route path="/identify/results" element={<ResultsDuringPage />} />
          
          {/* Module After */}
          <Route path="/curate" element={<ModuleAfterPage />} />
          <Route path="/curate/results" element={<ResultsAfterPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;