"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function Home() {
  const [systemData, setSystemData] = useState({
    message: "Initializing quantum core...",
    backend_status: "Checking...",
    database_status: "Checking..."
  });

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
    fetch(`${apiUrl}/api/system-check`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP Error! Status: ${res.status}`);
        return res.json();
      })
      .then((data) => setSystemData(data))
      .catch((error) => {
        setSystemData({
          message: `CRITICAL_ERROR: ${error.message}`,
          backend_status: "OFFLINE 🔴",
          database_status: "UNKNOWN ⚪"
        });
      });
  }, []);

  return (
    // Fundal profund întunecat (Slate-950) cu un efect subtil de gradient radial spre centru
    <div className="relative flex flex-col items-center justify-center flex-grow p-8 text-center bg-slate-950 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black min-h-[calc(100vh-73px)] overflow-hidden">
      
      {/* Elemente decorative Cyberpunk (linii de fundal) */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30" />

      {/* Secțiunea Principală */}
      <div className="relative z-10 max-w-3xl">
        <h2 className="text-6xl font-black mb-6 tracking-tighter uppercase text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-200 to-purple-500 drop-shadow-[0_5px_5px_rgba(34,211,238,0.2)]">
          The Turing Trials
        </h2>
        
        <p className="text-base font-mono text-cyan-500/80 uppercase tracking-widest mb-4">
          [ Protocol: AI Confrontation Simulator ]
        </p>

        <p className="text-lg text-slate-400 max-w-xl mx-auto mb-12 font-sans leading-relaxed">
          Pășește în arena juridică a viitorului. Generează cazuri unice prin rețele neurale, 
          asumă-ți rolul și pledează în fața unui magistrat sintetic.
        </p>
        
        {/* Butoane stilizate cu margini neon luminoase */}
        <div className="flex flex-col sm:flex-row gap-6 justify-center items-center">
          <Link 
            href="/setup" 
            className="w-full sm:w-auto px-8 py-3.5 bg-gradient-to-r from-cyan-500 to-teal-500 text-slate-950 font-mono font-bold uppercase tracking-wider rounded-md shadow-[0_0_20px_rgba(34,211,238,0.4)] hover:shadow-[0_0_30px_rgba(34,211,238,0.6)] border border-cyan-300 transition-all duration-300 hover:-translate-y-0.5"
          >
            Initiate Trial
          </Link>
          <Link 
            href="/dashboard" 
            className="w-full sm:w-auto px-8 py-3.5 bg-transparent text-purple-400 hover:text-purple-300 font-mono font-bold uppercase tracking-wider rounded-md border border-purple-500/40 hover:border-purple-400 shadow-[inset_0_0_12px_rgba(168,85,247,0.1)] hover:shadow-[0_0_20px_rgba(168,85,247,0.3)] transition-all duration-300 hover:-translate-y-0.5"
          >
            Access Archives
          </Link>
        </div>
      </div>

      {/* Widget Diagnostics - Stilizat ca o consolă de securitate din viitor */}
      <div className="absolute bottom-6 right-6 bg-slate-900/80 backdrop-blur-md border border-cyan-500/30 rounded-lg p-4 w-80 shadow-[0_0_25px_rgba(0,0,0,0.5),_inset_0_0_15px_rgba(34,211,238,0.05)] text-left z-50 font-mono text-xs">
        <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2 mb-3">
          <span className="font-bold text-cyan-400 tracking-wider uppercase flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
            Core_Diagnostics.log
          </span>
          <span className="text-slate-500 text-[10px]">v1.0.4</span>
        </div>
        
        <div className="space-y-2.5 text-slate-300">
          <div className="flex justify-between items-center bg-black/40 p-2 rounded border border-slate-800">
            <span className="text-slate-400">HOST_FRONTEND:</span>
            <span className="text-emerald-400 font-bold">ONLINE [//3000]</span>
          </div>

          <div className="flex justify-between items-center bg-black/40 p-2 rounded border border-slate-800">
            <span className="text-slate-400">API_CORE_LINK:</span>
            <span className="text-cyan-400 font-bold uppercase">{systemData.backend_status}</span>
          </div>

          <div className="flex justify-between items-center bg-black/40 p-2 rounded border border-slate-800">
            <span className="text-slate-400">DB_RELATIONAL:</span>
            <span className="text-purple-400 font-bold uppercase">{systemData.database_status}</span>
          </div>
        </div>
        
        {/* Terminal Text Message status down row */}
        <div className="mt-3 pt-2 border-t border-cyan-500/10 text-[10px] text-cyan-500/60 truncate uppercase">
          &gt; {systemData.message}
        </div>
      </div>
      
    </div>
  );
}