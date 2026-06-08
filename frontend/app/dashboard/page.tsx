"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Spinner from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import { apiJson } from "@/lib/api";

interface MatchSummary {
  id: string;
  player_role: string;
  case_summary: string | null;
  status: string;
  verdict: string;
  created_at: string;
}

interface DashboardData {
  user: { username: string; email: string };
  total_matches: number;
  total_wins: number;
  win_rate: number;
  recent_matches: MatchSummary[];
}

const VERDICT_STYLE: Record<string, string> = {
  NOT_GUILTY: "border-emerald-500/50 text-emerald-400 bg-emerald-500/10",
  PENDING:    "border-yellow-500/50 text-yellow-400 bg-yellow-500/10",
  GUILTY:     "border-red-500/50 text-red-400 bg-red-500/10",
};

export default function DashboardPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      const token = localStorage.getItem("turing_access_token");
      if (!token) { router.push("/login"); return; }

      try {
        const dashboard = await apiJson<DashboardData>("/api/users/me/dashboard");
        setData(dashboard);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load archive.";
        // Token likely expired if 401 — apiJson throws with the detail message
        if (msg.toLowerCase().includes("401") || msg.toLowerCase().includes("unauthorized")) {
          localStorage.removeItem("turing_access_token");
          router.push("/login");
          return;
        }
        showToast(msg, "error");
      } finally {
        setIsLoading(false);
      }
    };
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center flex-grow min-h-[calc(100vh-120px)]">
        <Spinner label="Decrypting Archives…" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center flex-grow min-h-[calc(100vh-120px)] gap-4">
        <p className="font-mono text-red-400 text-sm bg-red-950/30 border border-red-500/40 px-6 py-4 rounded uppercase tracking-wider">
          Archive unavailable.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="text-xs font-mono text-slate-400 hover:text-cyan-400 uppercase tracking-widest transition-colors cursor-pointer"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const winRatePct = Math.round((data.win_rate ?? 0) * 100);

  return (
    <div className="max-w-5xl mx-auto w-full px-4 sm:px-6 py-8 min-h-[calc(100vh-120px)] flex flex-col gap-6">

      {/* Header */}
      <div className="border-b border-purple-500/20 pb-4 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-cyan-400">
            User Archives
          </h2>
          <p className="text-xs font-mono text-purple-500/60 mt-1 uppercase tracking-widest flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
            Agent: {data.user.username} · Win Rate: {winRatePct}%
          </p>
        </div>
        <Link
          href="/setup"
          className="self-start sm:self-auto text-xs font-mono text-cyan-500 hover:text-cyan-300 uppercase tracking-widest transition-colors border border-cyan-500/30 hover:border-cyan-400 px-3 py-1.5 rounded"
        >
          + New Trial
        </Link>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Matches", value: data.total_matches },
          { label: "Victories", value: data.total_wins },
          { label: "Win Rate", value: `${winRatePct}%` },
        ].map((s) => (
          <div key={s.label} className="bg-slate-900/60 border border-slate-800 rounded-lg p-3 sm:p-4 text-center font-mono">
            <p className="text-xl sm:text-3xl font-black text-transparent bg-clip-text bg-gradient-to-b from-purple-400 to-cyan-400">
              {s.value}
            </p>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Match list */}
      <div className="bg-slate-900/40 backdrop-blur-sm rounded-lg border border-purple-500/20 overflow-hidden shadow-[0_0_20px_rgba(168,85,247,0.05)] flex-grow">

        {/* Desktop table */}
        <div className="hidden sm:block overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono">
            <thead>
              <tr className="bg-black/60 border-b border-purple-500/30 text-xs text-purple-300 uppercase tracking-wider">
                <th className="p-4 font-bold">Timestamp</th>
                <th className="p-4 font-bold">Role</th>
                <th className="p-4 font-bold">Case Summary</th>
                <th className="p-4 font-bold">Status</th>
                <th className="p-4 font-bold">Verdict</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_matches.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-slate-500 text-xs uppercase tracking-widest">
                    NO_RECORDS_FOUND. Initiate a new trial.
                  </td>
                </tr>
              ) : (
                data.recent_matches.map((match) => (
                  <tr
                    key={match.id}
                    onClick={() => router.push(`/courtroom/${match.id}`)}
                    className="border-b border-slate-800/50 hover:bg-purple-500/10 transition-colors cursor-pointer group"
                  >
                    <td className="p-4 text-sm text-slate-500 group-hover:text-cyan-400/70 transition-colors whitespace-nowrap">
                      {new Date(match.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-sm font-bold text-slate-300">
                      <span className="border-l-2 border-cyan-500 pl-2 uppercase">{match.player_role}</span>
                    </td>
                    <td className="p-4 text-sm text-slate-400 max-w-xs truncate">
                      {match.case_summary ?? "—"}
                    </td>
                    <td className="p-4 text-xs text-slate-500 uppercase">{match.status}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 text-[10px] font-bold uppercase tracking-widest border rounded ${VERDICT_STYLE[match.verdict] ?? VERDICT_STYLE.PENDING}`}>
                        {match.verdict}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Mobile card list */}
        <div className="sm:hidden divide-y divide-slate-800/50">
          {data.recent_matches.length === 0 ? (
            <p className="p-6 text-center text-slate-500 text-xs uppercase tracking-widest">
              No records found.
            </p>
          ) : (
            data.recent_matches.map((match) => (
              <button
                key={match.id}
                onClick={() => router.push(`/courtroom/${match.id}`)}
                className="w-full text-left p-4 hover:bg-purple-500/10 transition-colors font-mono"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] text-slate-500 uppercase tracking-widest">
                    {new Date(match.created_at).toLocaleDateString()}
                  </span>
                  <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest border rounded ${VERDICT_STYLE[match.verdict] ?? VERDICT_STYLE.PENDING}`}>
                    {match.verdict}
                  </span>
                </div>
                <p className="text-xs font-bold text-cyan-300 uppercase border-l-2 border-cyan-500 pl-2 mb-1">
                  {match.player_role}
                </p>
                <p className="text-xs text-slate-400 line-clamp-2">
                  {match.case_summary ?? "No summary available."}
                </p>
              </button>
            ))
          )}
        </div>

        <div className="bg-black/80 p-3 border-t border-purple-500/30 text-right">
          <span className="text-[10px] text-slate-600 uppercase font-mono tracking-widest">
            Total Matches: {data.total_matches}
          </span>
        </div>
      </div>
    </div>
  );
}
