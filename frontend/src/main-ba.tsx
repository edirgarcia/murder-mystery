import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./basta/App";
import "./index.css";
import "./basta/theme.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
