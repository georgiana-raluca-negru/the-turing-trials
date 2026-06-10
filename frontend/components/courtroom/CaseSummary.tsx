"use client";

interface CaseSummaryProps {
  matchId: string;
  caseSummary: string | null;
  playerRole: string;
  totalRounds: number;
  status: string;
  verdict: string;
}

export default function CaseSummary({
  matchId,
  caseSummary,
  playerRole,
  totalRounds,
  status,
  verdict,
}: CaseSummaryProps) {
  const verdictColor =
    verdict === "NOT_GUILTY"
      ? "text-emerald-400"
      : verdict === "PENDING"
      ? "text-yellow-400"
      : "text-red-400";

  return (
    <div className="h-full flex flex-col font-mono">
      <div className="border-b border-cyan-500/20 pb-3 mb-4">
        <h2 className="text-xs font-black uppercase tracking-widest text-cyan-400 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-cyan-400 rounded-sm animate-pulse" />
          Case_Parameters
        </h2>
      </div>

      <div className="flex-grow space-y-3 overflow-y-auto pr-1">

        <div className="bg-black/40 border border-slate-800 p-3 rounded text-xs">
          <p className="text-slate-500 uppercase mb-1 tracking-widest text-[10px]">Trial_ID:</p>
          <p className="text-slate-300 font-bold break-all">{matchId.split("-")[0].toUpperCase()}…</p>
        </div>

        <div className="bg-black/40 border border-slate-800 p-3 rounded text-xs">
          <p className="text-slate-500 uppercase mb-1 tracking-widest text-[10px]">Your Role:</p>
          <p className="text-cyan-300 font-bold uppercase">{playerRole}</p>
        </div>

        <div className="bg-black/40 border border-slate-800 p-3 rounded text-xs">
          <p className="text-slate-500 uppercase mb-1 tracking-widest text-[10px]">Max Rounds:</p>
          <p className="text-slate-300 font-bold">{totalRounds}</p>
        </div>

        <div className="bg-black/40 border border-slate-800 p-3 rounded text-xs">
          <p className="text-slate-500 uppercase mb-1 tracking-widest text-[10px]">Status:</p>
          <p className="text-slate-300 font-bold uppercase">{status}</p>
        </div>

        <div className="bg-black/40 border border-slate-800 p-3 rounded text-xs">
          <p className="text-slate-500 uppercase mb-1 tracking-widest text-[10px]">Verdict:</p>
          <p className={`font-bold uppercase ${verdictColor}`}>{verdict}</p>
        </div>

        {caseSummary && (
          <div className="bg-black/40 border border-cyan-500/20 p-3 rounded text-xs">
            <p className="text-slate-500 uppercase mb-2 tracking-widest text-[10px]">Case Summary:</p>
            <p className="text-slate-300 leading-relaxed">{caseSummary}</p>
          </div>
        )}

        {!caseSummary && (
          <div className="bg-black/40 border border-slate-800 p-3 rounded text-xs text-slate-600 italic text-center">
            AI Clerk generating case file…
          </div>
        )}
      </div>
    </div>
  );
}
