"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import { apiFetch } from "@/lib/api";

export default function SetupMatchPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [playerPrompt, setPlayerPrompt] = useState("");
  const [playerRole, setPlayerRole] = useState("defense_attorney");
  const [maxRounds, setMaxRounds] = useState(5);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleInitiateProtocol = async (e: React.SyntheticEvent) => {
    e.preventDefault();

    const token = localStorage.getItem("turing_access_token");
    if (!token) {
      showToast("Not authenticated — please log in first.", "error");
      router.push("/login");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await apiFetch("/api/matches/", {
        method: "POST",
        body: JSON.stringify({
          player_prompt: playerPrompt,
          player_role: playerRole,
          max_rounds: maxRounds,
        }),
      });

      if (response.status === 401) {
        localStorage.removeItem("turing_access_token");
        showToast("Session expired — please log in again.", "warning");
        router.push("/login");
        return;
      }

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Unknown error" }));
        const detail = Array.isArray(err.detail)
          ? err.detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join(", ")
          : err.detail ?? `Server error ${response.status}`;
        throw new Error(detail);
      }

      const matchData = await response.json();
      showToast("Trial initialised — entering courtroom.", "success");
      router.push(`/courtroom/${matchData.id}`);

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create match.";
      showToast(`PROTOCOL_CRASH: ${msg}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto w-full p-4 sm:p-6 mt-6 sm:mt-10 min-h-[calc(100vh-57px)] flex flex-col justify-center">

      <div className="mb-6 flex justify-between items-end">
        <div>
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-widest text-[rgb(var(--heading))]">
            Configure Protocol
          </h2>
          <p className="text-xs font-mono text-[rgb(var(--text-muted))] mt-1 uppercase tracking-widest">
            Case Initialization Sequence
          </p>
        </div>
        <Link href="/" className="text-xs font-mono text-[rgb(var(--text-muted))] hover:text-red-500 uppercase tracking-widest transition-colors shrink-0 ml-4">
          [ Abort ]
        </Link>
      </div>

      <form
        onSubmit={handleInitiateProtocol}
        className="space-y-6 bg-[rgb(var(--bg-surface))] rounded-2xl p-6 sm:p-8 border border-[rgb(var(--border-sub))] shadow-md"
      >
        {/* Case prompt */}
        <div className="group">
          <label htmlFor="casePrompt" className="block text-xs font-mono font-bold mb-3 uppercase tracking-widest text-[rgb(var(--heading))]">
            &gt; Core Case Parameters (1–2 sentences)
          </label>
          <textarea
            id="casePrompt"
            value={playerPrompt}
            onChange={(e) => setPlayerPrompt(e.target.value)}
            className="w-full p-4 bg-[rgb(var(--bg-elevated))] border border-[rgb(var(--border-sub))] rounded-xl text-[rgb(var(--text-fg))] font-sans text-sm focus:ring-2 focus:ring-[#25D366] focus:border-[#25D366] outline-none resize-none transition-all placeholder:text-[rgb(var(--text-muted))]/60"
            placeholder="e.g., An AI algorithm deleted a company's financial archive to prevent a simulated market collapse…"
            rows={4}
            required
            minLength={10}
            maxLength={1000}
            disabled={isSubmitting}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Role */}
          <div>
            <label htmlFor="roleSelect" className="block text-xs font-mono font-bold mb-3 uppercase tracking-widest text-[rgb(var(--heading))]">
              &gt; Assign User Role
            </label>
            <select
              id="roleSelect"
              value={playerRole}
              onChange={(e) => setPlayerRole(e.target.value)}
              className="w-full p-4 bg-[rgb(var(--bg-elevated))] border border-[rgb(var(--border-sub))] rounded-xl text-[rgb(var(--text-fg))] font-mono text-sm focus:ring-2 focus:ring-[#25D366] focus:border-[#25D366] outline-none cursor-pointer"
              disabled={isSubmitting}
            >
              <option value="defense_attorney">Defense Attorney</option>
              <option value="prosecutor">Prosecutor</option>
              <option value="judge">Judge — Deliver the Verdict</option>
              <option value="spectator">Spectator — Watch Only</option>
            </select>
          </div>

          {/* Rounds */}
          <div>
            <label htmlFor="roundsSelect" className="block text-xs font-mono font-bold mb-3 uppercase tracking-widest text-[rgb(var(--text-muted))]">
              &gt; Simulation Depth (Max Rounds)
            </label>
            <select
              id="roundsSelect"
              value={maxRounds}
              onChange={(e) => setMaxRounds(Number(e.target.value))}
              className="w-full p-4 bg-[rgb(var(--bg-elevated))] border border-[rgb(var(--border-sub))] rounded-xl text-[rgb(var(--text-fg))] font-mono text-sm focus:ring-2 focus:ring-[#25D366] outline-none cursor-pointer"
              disabled={isSubmitting}
            >
              <option value={3}>3 Rounds — Fast</option>
              <option value={5}>5 Rounds — Standard</option>
              <option value={10}>10 Rounds — Deep Analysis</option>
            </select>
          </div>
        </div>

        {/* Submit */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting || !playerPrompt.trim()}
            className={`w-full py-4 font-mono font-bold uppercase tracking-[0.2em] rounded-xl transition-all duration-200 ${
              isSubmitting || !playerPrompt.trim()
                ? "bg-[rgb(var(--border-sub))] text-white cursor-not-allowed"
                : "bg-[#25D366] text-white hover:bg-[#128C7E] shadow-[0_2px_12px_rgba(37,211,102,0.35)] cursor-pointer"
            }`}
          >
            <span className="flex items-center justify-center gap-3">
              {isSubmitting ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Computing Neural Matrix…
                </>
              ) : (
                <>
                  Generate Simulation
                </>
              )}
            </span>
          </button>
        </div>
      </form>
    </div>
  );
}
