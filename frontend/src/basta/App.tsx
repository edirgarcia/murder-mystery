import { BrowserRouter, Route, Routes } from "react-router-dom";
import { BastaProvider } from "./context/GameContext";
import DashboardPage from "./pages/DashboardPage";
import HomePage from "./pages/HomePage";
import LobbyPage from "./pages/LobbyPage";
import PlayPage from "./pages/PlayPage";
import ResultPage from "./pages/ResultPage";

export default function App() {
  return (
    <BastaProvider>
      <BrowserRouter basename="/basta">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/lobby/:code" element={<LobbyPage />} />
          <Route path="/play/:code" element={<PlayPage />} />
          <Route path="/dashboard/:code" element={<DashboardPage />} />
          <Route path="/result/:code" element={<ResultPage />} />
        </Routes>
      </BrowserRouter>
    </BastaProvider>
  );
}
