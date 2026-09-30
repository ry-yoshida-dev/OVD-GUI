import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { DialogHost } from "./components/DialogHost";
import "./styles.css";

const root = document.getElementById("root");
if (root === null) throw new Error("missing #root element");

createRoot(root).render(
  <StrictMode>
    <DialogHost>
      <App />
    </DialogHost>
  </StrictMode>,
);
