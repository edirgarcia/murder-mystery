import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./murder-mystery/App";
import "./index.css";
import "./murder-mystery/theme.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
