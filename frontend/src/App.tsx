import { BrowserRouter, Routes, Route } from "react-router-dom";
import { GameProvider } from "./context/GameContext";
import HomePage from "./pages/HomePage";
import LobbyPage from "./pages/LobbyPage";
import GamePage from "./pages/GamePage";
import GuessPage from "./pages/GuessPage";
import ResultPage from "./pages/ResultPage";
import DashboardPage from "./pages/DashboardPage";

export default function App() {
  return (
    <GameProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lobby/:code" element={<LobbyPage />} />
          <Route path="/game/:code" element={<GamePage />} />
          <Route path="/guess/:code" element={<GuessPage />} />
          <Route path="/result/:code" element={<ResultPage />} />
          <Route path="/dashboard/:code" element={<DashboardPage />} />
        </Routes>
      </BrowserRouter>
    </GameProvider>
  );
}
