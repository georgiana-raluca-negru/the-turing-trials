"use client";

interface CaseSummaryProps {
  matchId: string;
  caseSummary: string | null;
  playerRole: string;
  totalRounds: number;
  status: string;
  verdict: string;
}

function fmt(s: string) {
  return s.replace(/_/g, " ");
}

export default function CaseSummary({
  caseSummary,
  playerRole,
  totalRounds,
  status,
  verdict,
}: CaseSummaryProps) {
  const verdictColor =
    verdict === "Not Guilty"
      ? "text-emerald-700"
      : verdict === "Pending"
      ? "text-amber-700"
      : "text-red-700";

  return (
    <div className="h-full flex flex-col font-mono">
      <div className="border-b border-[#128C7E]/30 pb-3 mb-4">
        <h2 className="text-xs font-black uppercase tracking-widest text-[#075E54] flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-[#25D366] rounded-sm animate-pulse" />
          Case Parameters
        </h2>
      </div>

      <div className="flex-grow space-y-2.5 overflow-y-auto pr-1">

        <div className="bg-white border border-[#D1D7DB] p-3 rounded-lg text-xs">
          <p className="text-[#667781] uppercase mb-1 tracking-widest text-[10px]">Your Role</p>
          <p className="text-[#075E54] font-bold capitalize">{fmt(playerRole)}</p>
        </div>

        <div className="bg-white border border-[#D1D7DB] p-3 rounded-lg text-xs">
          <p className="text-[#667781] uppercase mb-1 tracking-widest text-[10px]">Max Rounds</p>
          <p className="text-[#111B21] font-bold">{totalRounds}</p>
        </div>

        <div className="bg-white border border-[#D1D7DB] p-3 rounded-lg text-xs">
          <p className="text-[#667781] uppercase mb-1 tracking-widest text-[10px]">Status</p>
          <p className="text-[#111B21] font-bold capitalize">{fmt(status)}</p>
        </div>

        <div className="bg-white border border-[#D1D7DB] p-3 rounded-lg text-xs">
          <p className="text-[#667781] uppercase mb-1 tracking-widest text-[10px]">Verdict</p>
          <p className={`font-bold capitalize ${verdictColor}`}>{verdict}</p>
        </div>

        {caseSummary && (
          <div className="bg-white border border-[#128C7E]/30 p-3 rounded-lg text-xs">
            <p className="text-[#667781] uppercase mb-2 tracking-widest text-[10px]">Case Summary</p>
            <p className="text-[#111B21] leading-relaxed">{caseSummary}</p>
          </div>
        )}

        {!caseSummary && (
          <div className="bg-[#F0F2F5] border border-[#D1D7DB] p-3 rounded-lg text-xs text-[#667781] italic text-center">
            AI Clerk generating case file…
          </div>
        )}
      </div>
    </div>
  );
}
