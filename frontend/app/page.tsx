"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [systemData, setSystemData] = useState({
    message: "Initializing...",
    backend_status: "Checking...",
    database_status: "Checking..."
  });

  useEffect(() => {
    // The Waiter walking over to the Kitchen (Port 8000)
    fetch("http://127.0.0.1:8000/api/system-check")
      .then((res) => res.json())
      .then((data) => setSystemData(data))
      .catch(() => setSystemData({
        message: "Failed to connect to backend.",
        backend_status: "Offline 🔴",
        database_status: "Unknown ⚪"
      }));
  }, []);

  return (
    <main className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center p-8 font-sans">
      
      {/* Title Section */}
      <div className="text-center mb-12">
        <h1 className="text-5xl font-extrabold text-white tracking-tight mb-4">
          The Turing Trials
        </h1>
        <p className="text-xl text-neutral-400 font-mono">
          {systemData.message}
        </p>
      </div>

      {/* Status Dashboard */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-8 w-full max-w-md shadow-2xl">
        <h2 className="text-sm font-bold text-neutral-500 uppercase tracking-widest mb-6 border-b border-neutral-800 pb-4">
          System Diagnostics
        </h2>
        
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-neutral-950 p-4 rounded-lg border border-neutral-800/50">
            <span className="text-neutral-300 font-medium">Next.js Frontend</span>
            <span className="text-green-400 font-mono text-sm">Active 🟢</span>
          </div>

          <div className="flex justify-between items-center bg-neutral-950 p-4 rounded-lg border border-neutral-800/50">
            <span className="text-neutral-300 font-medium">FastAPI Backend</span>
            <span className="font-mono text-sm text-neutral-100">{systemData.backend_status}</span>
          </div>

          <div className="flex justify-between items-center bg-neutral-950 p-4 rounded-lg border border-neutral-800/50">
            <span className="text-neutral-300 font-medium">PostgreSQL Database</span>
            <span className="font-mono text-sm text-neutral-100">{systemData.database_status}</span>
          </div>
        </div>
      </div>

    </main>
  );
}