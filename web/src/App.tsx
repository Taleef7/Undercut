import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ScenarioSelect from './pages/ScenarioSelect';
import ScenarioPlay from './pages/ScenarioPlay';
import DecisionResult from './pages/DecisionResult';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background text-foreground">
        <Routes>
          <Route path="/" element={<ScenarioSelect />} />
          <Route path="/scenario/:id" element={<ScenarioPlay />} />
          <Route path="/result" element={<DecisionResult />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App
