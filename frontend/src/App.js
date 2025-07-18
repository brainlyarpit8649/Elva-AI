import React from "react";
import "./App.css";
import ChatInterface from "./components/ChatInterface";
import { Toaster } from "./components/ui/toaster";

function App() {
  return (
    <div className="App">
      <ChatInterface />
      <Toaster />
    </div>
  );
}