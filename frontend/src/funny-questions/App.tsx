import { BrowserRouter, Routes, Route } from "react-router-dom";
import { FQProvider } from "./context/GameContext";
import HomePage from "./pages/HomePage";
import LobbyPage from "./pages/LobbyPage";
import VotePage from "./pages/VotePage";
import DashboardPage from "./pages/DashboardPage";
import ResultPage from "./pages/ResultPage";

export default function App() {
  return (
    <FQProvider>
      <BrowserRouter basename="/funny-questions">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lobby/:code" element={<LobbyPage />} />
          <Route path="/vote/:code" element={<VotePage />} />
          <Route path="/dashboard/:code" element={<DashboardPage />} />
          <Route path="/result/:code" element={<ResultPage />} />
        </Routes>
      </BrowserRouter>
    </FQProvider>
  );
}
