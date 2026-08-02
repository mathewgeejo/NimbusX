import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";
import "./minimal.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("NimbusX could not find the application root.");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
