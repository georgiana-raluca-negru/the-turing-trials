"use client";

export default function ScalesOfJustice({ score }: { score: number }) {
  // score: 0 (Defense wins) → 100 (Prosecution wins). 50 = tie.
  return (
    <div className="flex flex-col items-center w-full max-w-4xl mx-auto py-1">
      <div className="flex justify-between w-full text-[10px] font-mono font-bold uppercase tracking-widest mb-1.5 px-1">
        <span className={`transition-colors duration-700 ${score < 50 ? "text-[#075E54]" : "text-[#B2DFDB]"}`}>
          Defense
        </span>
        <span className="text-[#667781] font-normal text-[9px] tracking-widest">
          Balance
        </span>
        <span className={`transition-colors duration-700 ${score > 50 ? "text-red-600" : "text-[#B2DFDB]"}`}>
          Prosecution
        </span>
      </div>

      <div className="relative w-full h-2.5 bg-[#D1D7DB] rounded-full overflow-hidden">
        <div className="absolute top-0 bottom-0 left-1/2 w-px bg-[#111B21]/25 z-10" />
        <div className="flex h-full w-full">
          <div
            className="h-full bg-[#25D366] transition-all duration-700 ease-out"
            style={{ width: `${100 - score}%` }}
          />
          <div
            className="h-full bg-[#EF5350] transition-all duration-700 ease-out"
            style={{ width: `${score}%` }}
          />
        </div>
      </div>
    </div>
  );
}
