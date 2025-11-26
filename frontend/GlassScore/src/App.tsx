import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Onboarding } from './pages/Onboarding';
import { DataFill } from './pages/DataFill';
import { Evaluation } from './pages/Evaluation';
import './App.css';

function App() {
  console.log('App component rendering');
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Onboarding />} />
        <Route path="/data-fill" element={<DataFill />} />
        <Route path="/evaluation" element={<Evaluation />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
