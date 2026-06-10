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
    <div className="max-w-3xl mx-auto w-full p-4 sm:p-6 mt-6 sm:mt-10 min-h-[calc(100vh-120px)] flex flex-col justify-center relative">

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3/4 h-3/4 bg-cyan-900/10 blur-[100px] -z-10 rounded-full" />

      <div className="mb-8 border-b border-cyan-500/20 pb-4 flex justify-between items-end">
        <div>
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-200">
            Configure Protocol
          </h2>
          <p className="text-xs font-mono text-cyan-500/60 mt-1 uppercase tracking-widest">
            Module: Case_Initialization_Sequence
          </p>
        </div>
        <Link href="/" className="text-xs font-mono text-slate-500 hover:text-red-400 uppercase tracking-widest transition-colors shrink-0 ml-4">
          [ Abort ]
        </Link>
      </div>

      <form
        onSubmit={handleInitiateProtocol}
        className="space-y-6 bg-slate-900/60 backdrop-blur-md p-6 sm:p-8 rounded-lg border border-cyan-500/30 shadow-[0_0_30px_rgba(0,0,0,0.8)]"
      >
        {/* Case prompt */}
        <div className="relative group">
          <label htmlFor="casePrompt" className="block text-xs font-mono font-bold mb-3 uppercase tracking-widest text-cyan-300">
            &gt; Core Case Parameters (1–2 sentences)
          </label>
          <div className="absolute left-0 top-9 bottom-7 w-1 bg-cyan-500/20 group-focus-within:bg-cyan-400 transition-colors" />
          <textarea
            id="casePrompt"
            value={playerPrompt}
            onChange={(e) => setPlayerPrompt(e.target.value)}
            className="w-full pl-6 p-4 bg-black/50 border border-slate-700/50 rounded-r-md text-slate-200 font-sans text-sm focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none resize-none shadow-inner placeholder:text-slate-600 transition-all"
            placeholder="e.g., An AI algorithm deleted a company's financial archive to prevent a simulated market collapse…"
            rows={4}
            required
            minLength={10}
            maxLength={1000}
            disabled={isSubmitting}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Role */}
          <div className="relative group">
            <label htmlFor="roleSelect" className="block text-xs font-mono font-bold mb-3 uppercase tracking-widest text-purple-300">
              &gt; Assign User Role
            </label>
            <select
              id="roleSelect"
              value={playerRole}
              onChange={(e) => setPlayerRole(e.target.value)}
              className="w-full p-4 bg-black/50 border border-slate-700/50 rounded-md text-slate-200 font-mono text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500 outline-none cursor-pointer"
              disabled={isSubmitting}
            >
              <option value="defense_attorney">DEFENSE_ATTORNEY</option>
              <option value="prosecutor">PROSECUTOR</option>
              <option value="judge">JUDGE (AI_SPECTATOR)</option>
            </select>
          </div>

          {/* Rounds */}
          <div>
            <label htmlFor="roundsSelect" className="block text-xs font-mono font-bold mb-3 uppercase tracking-widest text-slate-400">
              &gt; Simulation Depth (Max Rounds)
            </label>
            <select
              id="roundsSelect"
              value={maxRounds}
              onChange={(e) => setMaxRounds(Number(e.target.value))}
              className="w-full p-4 bg-black/50 border border-slate-700/50 rounded-md text-slate-200 font-mono text-sm focus:ring-1 focus:ring-slate-500 outline-none cursor-pointer"
              disabled={isSubmitting}
            >
              <option value={3}>3 ROUNDS (FAST_MODE)</option>
              <option value={5}>5 ROUNDS (STANDARD)</option>
              <option value={10}>10 ROUNDS (DEEP_ANALYSIS)</option>
            </select>
          </div>
        </div>

        {/* Submit */}
        <div className="pt-4">
          <button
            type="submit"
            disabled={isSubmitting || !playerPrompt.trim()}
            className={`w-full py-4 font-mono font-bold uppercase tracking-[0.2em] border rounded-md transition-all duration-300 relative overflow-hidden cursor-pointer ${
              isSubmitting || !playerPrompt.trim()
                ? "border-slate-800 text-slate-600 bg-transparent cursor-not-allowed"
                : "bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border-cyan-500/50 hover:border-cyan-400 hover:shadow-[0_0_20px_rgba(34,211,238,0.2)]"
            }`}
          >
            <span className="flex items-center justify-center gap-3">
              {isSubmitting ? (
                <>
                  <span className="w-4 h-4 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin" />
                  Computing Neural Matrix…
                </>
              ) : (
                <>
                  Generate Simulation
                  <span className="text-xs bg-cyan-500 text-slate-950 px-2 py-0.5 rounded-sm">INIT_PROT</span>
                </>
              )}
            </span>
          </button>
        </div>
      </form>
    </div>
  );
}
