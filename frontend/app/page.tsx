"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [systemData, setSystemData] = useState({
    message: "Initializing...",
    backend_status: "Checking...",
    database_status: "Checking..."
  });

  useEffect(() => {
    // Let's explicitly log the URL we are trying to hit
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
    console.log("Trying to fetch from:", apiUrl);
    
    fetch(`${apiUrl}/api/system-check`)
      .then((res) => {
        if (!res.ok) {
           throw new Error(`HTTP Error! Status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => setSystemData(data))
      .catch((error) => {
        console.error("The exact fetch error is:", error);
        setSystemData({
          message: `Network Error: ${error.message}`,
          backend_status: "Offline 🔴",
          database_status: "Unknown ⚪"
        });
      });
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