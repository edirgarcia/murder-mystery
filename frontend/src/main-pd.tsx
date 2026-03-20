import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./prisoners-dilemma/App";
import "./index.css";
import "./prisoners-dilemma/theme.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
