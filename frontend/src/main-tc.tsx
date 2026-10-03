import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./trading-city/App";
import "./index.css";
import "./trading-city/theme.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
