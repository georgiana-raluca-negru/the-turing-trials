"use client";

export interface EvidenceItem {
  id: string | number;
  title: string;
  desc: string;
  used?: boolean;
}

interface EvidenceFolderProps {
  items: EvidenceItem[];
  onAttach?: (id: string | number) => void;
}

export default function EvidenceFolder({ items, onAttach }: EvidenceFolderProps) {
  const available = items.filter((e) => !e.used);
  const used = items.filter((e) => e.used);

  return (
    <div className="h-full flex flex-col font-mono">
      <div className="border-b border-purple-500/20 pb-3 mb-4 flex items-center justify-between">
        <h2 className="text-xs font-black uppercase tracking-widest text-purple-400 flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-purple-400 rounded-sm" />
          Data_Vault
        </h2>
        <span className="text-[10px] text-slate-600 uppercase tracking-widest">
          {available.length}/{items.length} available
        </span>
      </div>

      {items.length === 0 && (
        <p className="text-slate-600 text-xs italic text-center mt-4">
          No evidence loaded yet.
        </p>
      )}

      <div className="flex-grow space-y-3 overflow-y-auto pr-1">
        {available.map((item) => (
          <div
            key={item.id}
            className="p-3 rounded border bg-black/60 border-purple-500/30 hover:border-purple-400 hover:shadow-[0_0_10px_rgba(168,85,247,0.15)] transition-all group"
          >
            <div className="flex justify-between items-start mb-1">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                {item.title}
              </h4>
            </div>
            <p className="text-[10px] leading-relaxed mb-2 text-slate-400">{item.desc}</p>
            {onAttach && (
              <button
                onClick={() => onAttach(item.id)}
                className="text-[10px] font-bold text-purple-400/70 group-hover:text-purple-300 uppercase tracking-widest transition-colors flex items-center gap-1 cursor-pointer"
              >
                <span className="text-purple-500">+</span> Attach to buffer
              </button>
            )}
          </div>
        ))}

        {used.map((item) => (
          <div
            key={item.id}
            className="p-3 rounded border bg-slate-900/30 border-slate-800/50 opacity-50"
          >
            <div className="flex justify-between items-start mb-1">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                {item.title}
              </h4>
              <span className="text-[9px] bg-slate-800 text-slate-500 px-1 rounded shrink-0">USED</span>
            </div>
            <p className="text-[10px] leading-relaxed text-slate-700">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
