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
      <div className="border-b border-[#128C7E]/30 pb-3 mb-4 flex items-center justify-between">
        <h2 className="text-xs font-black uppercase tracking-widest text-[#075E54] flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-[#25D366] rounded-sm" />
          Data_Vault
        </h2>
        <span className="text-[10px] text-[#667781] uppercase tracking-widest">
          {available.length}/{items.length} available
        </span>
      </div>

      {items.length === 0 && (
        <p className="text-[#667781] text-xs italic text-center mt-4">
          No evidence loaded yet.
        </p>
      )}

      <div className="flex-grow space-y-3 overflow-y-auto pr-1">
        {available.map((item) => (
          <div
            key={item.id}
            className="p-3 rounded-lg border bg-white border-[#128C7E]/40 hover:border-[#075E54] hover:shadow-[0_0_10px_rgba(7,94,84,0.12)] transition-all group"
          >
            <div className="flex justify-between items-start mb-1">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#075E54]">
                {item.title}
              </h4>
            </div>
            <p className="text-[10px] leading-relaxed mb-2 text-[#667781]">{item.desc}</p>
            {onAttach && (
              <button
                onClick={() => onAttach(item.id)}
                className="text-[10px] font-bold text-[#128C7E] group-hover:text-[#075E54] uppercase tracking-widest transition-colors flex items-center gap-1 cursor-pointer"
              >
                <span className="text-[#25D366]">+</span> Attach to buffer
              </button>
            )}
          </div>
        ))}

        {used.map((item) => (
          <div
            key={item.id}
            className="p-3 rounded-lg border bg-[#F0F2F5] border-[#D1D7DB] opacity-55"
          >
            <div className="flex justify-between items-start mb-1">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[#667781]">
                {item.title}
              </h4>
              <span className="text-[9px] bg-[#D1D7DB] text-[#667781] px-1.5 py-0.5 rounded shrink-0 ml-1">USED</span>
            </div>
            <p className="text-[10px] leading-relaxed text-[#667781]/70">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
