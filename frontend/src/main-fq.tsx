import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./funny-questions/App";
import "./index.css";
import "./funny-questions/theme.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
