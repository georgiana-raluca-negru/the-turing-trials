import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center flex-grow text-center px-4 relative overflow-hidden min-h-[calc(100vh-73px)]">
      
      {/* Background Warning Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-red-900/10 blur-[100px] -z-10 rounded-full animate-pulse" />

      {/* Decorative Warning Grid Lines */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#450a0a_1px,transparent_1px),linear-gradient(to_bottom,#450a0a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-20" />

      {/* Glitch Effect 404 Container */}
      <div className="relative mb-6">
        <h2 className="text-8xl font-black text-transparent bg-clip-text bg-gradient-to-b from-red-500 to-red-900 drop-shadow-[0_0_15px_rgba(239,68,68,0.5)] z-10 relative select-none">
          404
        </h2>
        {/* Fake glitch shadows */}
        <h2 className="text-8xl font-black text-red-500/30 absolute -top-1 -left-2 z-0 select-none blur-[1px]">404</h2>
        <h2 className="text-8xl font-black text-cyan-500/20 absolute top-1 left-2 z-0 select-none blur-[1px]">404</h2>
      </div>
      
      <h3 className="text-2xl font-mono font-bold mb-3 text-red-400 tracking-widest uppercase flex items-center gap-3">
        <span className="w-3 h-3 bg-red-500 rounded-sm animate-ping" />
        OBJECTION! Data_Not_Found
      </h3>
      
      <p className="text-slate-400 mb-8 max-w-md font-mono text-sm border-l-2 border-red-500/50 pl-4 text-left leading-relaxed">
        <span className="text-red-500/80 block mb-1">ERR_CODE_NULL_POINTER</span>
        Fișierul cu probe nu există în arhiva curentă. Accesul la acest sector este interzis sau memoria a fost ștearsă.
      </p>
      
      <Link 
        href="/" 
        className="px-8 py-3.5 bg-transparent text-slate-300 font-mono font-bold uppercase tracking-widest rounded-md border border-slate-700 hover:border-red-500 hover:text-red-400 shadow-[inset_0_0_10px_rgba(0,0,0,0.5)] hover:shadow-[0_0_20px_rgba(239,68,68,0.2),_inset_0_0_15px_rgba(239,68,68,0.1)] transition-all duration-300 group"
      >
        <span className="text-slate-600 group-hover:text-red-500 mr-2">&lt;</span>
        Return to Secure Lobby
      </Link>
      
    </div>
  );
}