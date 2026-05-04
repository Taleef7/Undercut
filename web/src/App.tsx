import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ScenarioSelect from './pages/ScenarioSelect';
import ScenarioPlay from './pages/ScenarioPlay';
import DecisionResult from './pages/DecisionResult';
import Disclaimer from './pages/Disclaimer';
import Methodology from './pages/Methodology';
import Footer from './components/Footer';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-background text-foreground flex flex-col">
        <div className="flex-1">
          <Routes>
            <Route path="/" element={<ScenarioSelect />} />
            <Route path="/scenario/:id" element={<ScenarioPlay />} />
            <Route path="/result" element={<DecisionResult />} />
            <Route path="/disclaimer" element={<Disclaimer />} />
            <Route path="/methodology" element={<Methodology />} />
          </Routes>
        </div>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

export default App
