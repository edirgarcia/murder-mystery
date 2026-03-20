import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { WWProvider } from "./context/GameContext";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";
import LobbyPage from "./pages/LobbyPage";
import PlayerPage from "./pages/PlayerPage";
import ResultPage from "./pages/ResultPage";

export default function App() {
  return (
    <WWProvider>
      <BrowserRouter basename="/werewolf">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lobby/:code" element={<LobbyPage />} />
          <Route path="/play/:code" element={<PlayerPage />} />
          <Route path="/dashboard/:code" element={<DashboardPage />} />
          <Route path="/result/:code" element={<ResultPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </WWProvider>
  );
}

