"use client";

export default function ScalesOfJustice({ score }: { score: number }) {
  // score este între 0 (Defense câștigă total) și 100 (Prosecutor câștigă total).
  // 50 = Egalitate.
  
  return (
    <div className="flex flex-col items-center w-full max-w-4xl mx-auto py-2">
      <div className="flex justify-between w-full text-[10px] font-mono font-bold uppercase tracking-widest mb-2 px-1">
        <span className={`transition-colors ${score < 50 ? 'text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]' : 'text-slate-600'}`}>
          [ DEFENSE ]
        </span>
        
        <span className="text-slate-500 font-normal">
          NEURAL_BALANCE_INDICATOR
        </span>
        
        <span className={`transition-colors ${score > 50 ? 'text-purple-400 drop-shadow-[0_0_5px_rgba(168,85,247,0.8)]' : 'text-slate-600'}`}>
          [ PROSECUTION ]
        </span>
      </div>
      
      {/* Bara de progres (Cyberpunk Style) */}
      <div className="relative w-full h-3 bg-black/80 rounded-sm border border-slate-700/50 overflow-hidden shadow-[inset_0_0_10px_rgba(0,0,0,1)]">
        
        {/* Marcajul central (Egalitate) */}
        <div className="absolute top-0 bottom-0 left-1/2 w-0.5 bg-slate-500/50 z-10" />
        
        {/* Fill pentru Apărare (Stânga - Cyan) */}
        <div 
          className="absolute top-0 bottom-0 left-0 bg-cyan-500 shadow-[0_0_15px_rgba(34,211,238,0.8)] transition-all duration-1000 ease-out" 
          style={{ width: `${50 - Math.max(0, score - 50) * 0}%`, right: `${Math.max(50, score)}%` }} // Logica vizuală simplificată mai jos
        />
        
        {/* O implementare mai simplă și eficientă a barei de scor: */}
        <div className="flex h-full w-full">
            <div 
                className="h-full bg-cyan-500/80 transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(34,211,238,0.5)] border-r border-cyan-300"
                style={{ width: `${100 - score}%` }}
            />
             <div 
                className="h-full bg-purple-500/80 transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(168,85,247,0.5)] border-l border-purple-300"
                style={{ width: `${score}%` }}
            />
        </div>

      </div>
    </div>
  );
}