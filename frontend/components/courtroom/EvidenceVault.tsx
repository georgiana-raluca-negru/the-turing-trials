"use client";

import { useState } from "react";

export interface EvidenceItem {
  id: string | number;
  title: string;
  desc: string;
  used?: boolean;
}

interface EvidenceVaultProps {
  items: EvidenceItem[];
  onAttach?: (id: string | number) => void;
  attachedId?: string | number | null;
}

export default function EvidenceVault({ items, onAttach, attachedId }: EvidenceVaultProps) {
  const [open, setOpen] = useState(false);
  const available = items.filter((e) => !e.used);

  return (
    <div className="h-full flex flex-col items-center font-mono">
      <div className="w-full border-b border-[#128C7E]/30 pb-3 mb-4 flex items-center justify-between">
        <h2 className="text-xs font-black uppercase tracking-widest text-[rgb(var(--heading))] flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-[#25D366] rounded-sm" />
          Data_Vault
        </h2>
        <span className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest">
          {available.length}/{items.length}
        </span>
      </div>

      {items.length === 0 ? (
        <p className="text-[rgb(var(--text-muted))] text-xs italic text-center mt-4">
          No evidence loaded yet.
        </p>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="relative w-36 h-48 mt-8 group cursor-pointer"
          title="Open evidence vault"
        >
          {items.slice(0, 4).map((item, i) => (
            <div
              key={item.id}
              className={`absolute inset-0 rounded-xl border-2 bg-[rgb(var(--bg-surface))] shadow-lg transition-all duration-300 group-hover:shadow-[0_4px_24px_rgba(37,211,102,0.3)] group-hover:-translate-y-1 ${
                item.used ? "border-[rgb(var(--border-sub))]" : "border-[#128C7E]/50"
              }`}
              style={{
                transform: `rotate(${(i - 1.5) * 4}deg) translate(${(i - 1.5) * 3}px, ${-i * 2}px)`,
                zIndex: i,
              }}
            />
          ))}
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 z-10">
            <span className="text-[10px] font-black uppercase tracking-widest text-[rgb(var(--heading))]">
              Case Files
            </span>
            <span className="text-3xl font-black text-[rgb(var(--heading))]">{available.length}</span>
            <span className="text-[9px] uppercase tracking-widest text-[rgb(var(--text-muted))] group-hover:text-[#25D366] transition-colors">
              Click to open
            </span>
          </div>
        </button>
      )}

      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4 vault-overlay-in"
          onClick={() => setOpen(false)}
        >
          <button
            onClick={() => setOpen(false)}
            className="absolute top-4 right-4 sm:top-6 sm:right-6 text-white/60 hover:text-white text-2xl leading-none cursor-pointer transition-colors z-20"
            title="Close vault"
          >
            ✕
          </button>

          <p className="absolute top-4 sm:top-6 left-1/2 -translate-x-1/2 text-[10px] sm:text-xs font-mono uppercase tracking-[0.3em] text-[#39FF8A]">
            {onAttach ? "Select a case file to attach" : "Evidence inventory"}
          </p>

          <div
            className="w-full max-w-6xl overflow-x-auto px-4 sm:px-12 py-10 snap-x snap-mandatory flex gap-6 sm:gap-10 items-center"
            onClick={(e) => e.stopPropagation()}
          >
            {items.map((item, i) => {
              const selectable = !!onAttach && !item.used;
              const isAttached = attachedId !== undefined && String(attachedId) === String(item.id);

              return (
                <div key={item.id} className="snap-center shrink-0 first:ml-auto last:mr-auto">
                  <div className="card-fan-in" style={{ animationDelay: `${i * 0.06}s` }}>
                    <div className="float-card" style={{ animationDelay: `${i * 0.18}s` }}>
                      <div
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!selectable) return;
                          onAttach?.(item.id);
                          setOpen(false);
                        }}
                        className={`w-64 sm:w-80 h-80 sm:h-96 rounded-xl border-2 p-5 sm:p-6 flex flex-col shadow-2xl transition-all duration-200 ${
                          item.used
                            ? "bg-[rgb(var(--bg-elevated))] border-[rgb(var(--border-sub))] opacity-50"
                            : isAttached
                            ? "bg-[rgb(var(--bg-surface))] border-[#25D366] shadow-[0_0_30px_rgba(37,211,102,0.5)]"
                            : "bg-[rgb(var(--bg-surface))] border-[#128C7E]/50 hover:border-[#25D366] hover:shadow-[0_0_30px_rgba(37,211,102,0.4)] hover:-translate-y-2"
                        } ${selectable ? "cursor-pointer" : "cursor-default"}`}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-[10px] sm:text-xs font-black uppercase tracking-widest text-[rgb(var(--heading))]/50">
                            Exhibit {String(i + 1).padStart(2, "0")}
                          </span>
                          {item.used && (
                            <span className="text-[9px] bg-[rgb(var(--border-sub))] text-[rgb(var(--text-muted))] px-2 py-0.5 rounded uppercase">
                              Used
                            </span>
                          )}
                          {isAttached && (
                            <span className="text-[9px] bg-[#25D366] text-white px-2 py-0.5 rounded uppercase">
                              Attached
                            </span>
                          )}
                        </div>
                        <h4 className="text-sm sm:text-base font-bold uppercase tracking-wider text-[rgb(var(--heading))] mb-3">
                          {item.title}
                        </h4>
                        <p className="text-xs sm:text-sm leading-[1.6] text-[rgb(var(--text-muted))] overflow-y-auto flex-grow">
                          {item.desc}
                        </p>
                        {selectable && (
                          <p className="text-[10px] font-bold text-[#128C7E] uppercase tracking-widest mt-3 flex items-center gap-1">
                            <span className="text-[#25D366]">+</span> Tap to attach
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <p className="absolute bottom-4 sm:bottom-6 left-1/2 -translate-x-1/2 text-[9px] sm:text-[10px] font-mono uppercase tracking-[0.3em] text-[rgb(var(--text-muted))]">
            {items.length > 1 ? "← Scroll to browse exhibits →" : ""}
          </p>
        </div>
      )}
    </div>
  );
}
