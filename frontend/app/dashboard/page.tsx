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
  match_result: "win" | "loss" | "n/a";
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
  not_guilty: "border-emerald-400 text-emerald-700 bg-emerald-50",
  pending:    "border-amber-400  text-amber-700  bg-amber-50",
  guilty:     "border-red-400   text-red-700   bg-red-50",
  abandoned:  "border-[rgb(var(--border-sub))]  text-[rgb(var(--text-muted))]  bg-[rgb(var(--bg-elevated))]",
};

const RESULT_STYLE: Record<string, string> = {
  win:  "border-emerald-400 text-emerald-700 bg-emerald-50",
  loss: "border-red-400    text-red-700    bg-red-50",
  "n/a":  "border-[rgb(var(--border-sub))]  text-[rgb(var(--text-muted))]  bg-transparent",
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
      <div className="flex items-center justify-center flex-grow min-h-[calc(100vh-57px)] bg-[rgb(var(--bg-page))]">
        <Spinner label="Decrypting Archives…" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col items-center justify-center flex-grow min-h-[calc(100vh-57px)] bg-[rgb(var(--bg-page))] gap-4">
        <p className="font-mono text-red-600 text-sm bg-red-50 border border-red-300 px-6 py-4 rounded-xl uppercase tracking-wider">
          Archive unavailable.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="text-xs font-mono text-[rgb(var(--text-muted))] hover:text-[rgb(var(--heading))] uppercase tracking-widest transition-colors cursor-pointer"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  const winRatePct = Math.round((data.win_rate ?? 0) * 100);

  return (
    <div className="max-w-5xl mx-auto w-full px-4 sm:px-6 py-8 min-h-[calc(100vh-57px)] flex flex-col gap-6 bg-[rgb(var(--bg-page))]">

      {/* Header */}
      <div className="border-b border-[rgb(var(--border-sub))] pb-4 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-widest text-[rgb(var(--heading))]">
            User Archives
          </h2>
          <p className="text-xs font-mono text-[rgb(var(--text-muted))] mt-1 uppercase tracking-widest flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-[#25D366] rounded-full animate-pulse" />
            Agent: {data.user.username} · Win Rate: {winRatePct}%
          </p>
        </div>
        <div className="flex gap-2 self-start sm:self-auto">
          <Link
            href="/leaderboard"
            className="text-xs font-mono text-amber-700 hover:text-amber-900 uppercase tracking-widest transition-colors border border-amber-400/60 hover:border-amber-600 px-3 py-1.5 rounded-lg bg-amber-50"
          >
            Leaderboard
          </Link>
          <Link
            href="/setup"
            className="text-xs font-mono text-[rgb(var(--heading))] hover:text-white uppercase tracking-widest transition-colors border border-[#25D366] hover:bg-[#25D366] px-3 py-1.5 rounded-lg"
          >
            + New Trial
          </Link>
        </div>
      </div>

      {/* Stats strip */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Matches", value: data.total_matches },
          { label: "Victories",     value: data.total_wins },
          { label: "Win Rate",      value: `${winRatePct}%` },
        ].map((s) => (
          <div key={s.label} className="bg-[rgb(var(--bg-surface))] border border-[rgb(var(--border-sub))] rounded-xl p-3 sm:p-4 text-center shadow-sm">
            <p className="text-xl sm:text-3xl font-black text-[rgb(var(--heading))]">{s.value}</p>
            <p className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest mt-1 font-mono">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Match list */}
      <div className="bg-[rgb(var(--bg-surface))] rounded-2xl border border-[rgb(var(--border-sub))] overflow-hidden shadow-sm flex-grow">

        {/* Desktop table */}
        <div className="hidden sm:block overflow-x-auto">
          <table className="w-full text-left border-collapse font-mono">
            <thead>
              <tr className="bg-[#075E54] text-white text-xs uppercase tracking-wider">
                <th className="p-4 font-bold">Timestamp</th>
                <th className="p-4 font-bold">Role</th>
                <th className="p-4 font-bold">Case Summary</th>
                <th className="p-4 font-bold">Verdict</th>
                <th className="p-4 font-bold">Result</th>
              </tr>
            </thead>
            <tbody>
              {data.recent_matches.length === 0 ? (
                <tr>
                  <td colSpan={5} className="p-8 text-center text-[rgb(var(--text-muted))] text-xs uppercase tracking-widest">
                    No records found. Initiate a new trial.
                  </td>
                </tr>
              ) : (
                data.recent_matches.map((match) => (
                  <tr
                    key={match.id}
                    onClick={() => router.push(`/courtroom/${match.id}`)}
                    className="border-b border-[rgb(var(--bg-elevated))] hover:bg-[rgb(var(--bg-elevated))] transition-colors cursor-pointer group"
                  >
                    <td className="p-4 text-sm text-[rgb(var(--text-muted))] whitespace-nowrap">
                      {new Date(match.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-sm font-bold text-[rgb(var(--text-fg))]">
                      <span className="border-l-2 border-[#25D366] pl-2 capitalize">{match.player_role.replace(/_/g, " ")}</span>
                    </td>
                    <td className="p-4 text-sm text-[rgb(var(--text-muted))] max-w-xs truncate">
                      {match.case_summary ?? "—"}
                    </td>
                    <td className="p-4">
                      {match.status === "quit" || match.status === "abandoned" ? (
                        <span className={`px-2 py-1 text-[10px] font-bold uppercase tracking-widest border rounded-md ${VERDICT_STYLE["abandoned"]}`}>
                          Abandoned
                        </span>
                      ) : (
                        <span className={`px-2 py-1 text-[10px] font-bold uppercase tracking-widest border rounded-md ${VERDICT_STYLE[match.verdict] ?? VERDICT_STYLE["pending"]}`}>
                          {match.verdict.replace(/_/g, " ")}
                        </span>
                      )}
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-1 text-[10px] font-bold uppercase tracking-widest border rounded-md ${RESULT_STYLE[match.match_result] ?? RESULT_STYLE["n/a"]}`}>
                        {match.match_result}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Mobile card list */}
        <div className="sm:hidden divide-y divide-[rgb(var(--bg-elevated))]">
          {data.recent_matches.length === 0 ? (
            <p className="p-6 text-center text-[rgb(var(--text-muted))] text-xs uppercase tracking-widest">
              No records found.
            </p>
          ) : (
            data.recent_matches.map((match) => (
              <button
                key={match.id}
                onClick={() => router.push(`/courtroom/${match.id}`)}
                className="w-full text-left p-4 hover:bg-[rgb(var(--bg-elevated))] transition-colors font-mono"
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest">
                    {new Date(match.created_at).toLocaleDateString()}
                  </span>
                  <div className="flex gap-1">
                    {match.status === "quit" || match.status === "abandoned" ? (
                      <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest border rounded-md ${VERDICT_STYLE["abandoned"]}`}>
                        Abandoned
                      </span>
                    ) : (
                      <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest border rounded-md ${VERDICT_STYLE[match.verdict] ?? VERDICT_STYLE["pending"]}`}>
                        {match.verdict.replace(/_/g, " ")}
                      </span>
                    )}
                    <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest border rounded-md ${RESULT_STYLE[match.match_result] ?? RESULT_STYLE["n/a"]}`}>
                      {match.match_result}
                    </span>
                  </div>
                </div>
                <p className="text-xs font-bold text-[rgb(var(--heading))] capitalize border-l-2 border-[#25D366] pl-2 mb-1">
                  {match.player_role.replace(/_/g, " ")}
                </p>
                <p className="text-xs text-[rgb(var(--text-muted))] line-clamp-2">
                  {match.case_summary ?? "No summary available."}
                </p>
              </button>
            ))
          )}
        </div>

        <div className="bg-[rgb(var(--bg-elevated))] p-3 border-t border-[rgb(var(--border-sub))] text-right">
          <span className="text-[10px] text-[rgb(var(--text-muted))] uppercase font-mono tracking-widest">
            Total Matches: {data.total_matches}
          </span>
        </div>
      </div>
    </div>
  );
}
