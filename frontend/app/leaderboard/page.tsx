"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Spinner from "@/components/ui/Spinner";
import { apiJson } from "@/lib/api";

interface LeaderboardEntry {
  rank: number;
  username: string;
  total_matches: number;
  total_wins: number;
  win_rate: number;
  score: number;
}

interface LeaderboardData {
  entries: LeaderboardEntry[];
  total_players: number;
}

const RANK_STYLE: Record<number, string> = {
  1: "text-amber-600 font-black",
  2: "text-slate-500 font-bold",
  3: "text-amber-800 font-bold",
};

export default function LeaderboardPage() {
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiJson<LeaderboardData>("/api/users/leaderboard")
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load leaderboard."))
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="max-w-3xl mx-auto w-full px-4 sm:px-6 py-8 min-h-[calc(100vh-57px)] flex flex-col gap-6 bg-[rgb(var(--bg-page))]">

      {/* Header */}
      <div className="border-b border-[rgb(var(--border-sub))] pb-4 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-widest text-[rgb(var(--heading))]">
            Global Leaderboard
          </h2>
          <p className="text-xs font-mono text-[rgb(var(--text-muted))] mt-1 uppercase tracking-widest">
            Ranked by win score · volume + consistency required
          </p>
        </div>
        <Link
          href="/dashboard"
          className="self-start sm:self-auto text-xs font-mono text-[rgb(var(--text-muted))] hover:text-[rgb(var(--heading))] uppercase tracking-widest transition-colors border border-[rgb(var(--border-sub))] hover:border-[#128C7E] px-3 py-1.5 rounded-lg bg-[rgb(var(--bg-surface))]"
        >
          ← Archives
        </Link>
      </div>

      {/* Scoring note */}
      <div className="bg-[rgb(var(--bg-surface))] border border-[rgb(var(--border-sub))] rounded-xl px-4 py-3 font-mono text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest shadow-sm">
        Score = wins ÷ (matches + 5) · judges and spectators are excluded from ranking
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center flex-grow">
          <Spinner label="Loading rankings…" />
        </div>
      ) : error ? (
        <p className="text-red-600 font-mono text-sm text-center uppercase tracking-wider bg-red-50 border border-red-300 rounded-xl p-4">{error}</p>
      ) : !data || data.entries.length === 0 ? (
        <p className="text-[rgb(var(--text-muted))] font-mono text-xs text-center uppercase tracking-widest py-12">
          No ranked players yet. Play a match first.
        </p>
      ) : (
        <div className="bg-[rgb(var(--bg-surface))] rounded-2xl border border-[rgb(var(--border-sub))] overflow-hidden shadow-sm">
          {/* Desktop table */}
          <div className="hidden sm:block overflow-x-auto">
            <table className="w-full text-left border-collapse font-mono">
              <thead>
                <tr className="bg-[#075E54] text-white text-xs uppercase tracking-wider">
                  <th className="p-4 font-bold w-12">#</th>
                  <th className="p-4 font-bold">Agent</th>
                  <th className="p-4 font-bold text-right">Matches</th>
                  <th className="p-4 font-bold text-right">Wins</th>
                  <th className="p-4 font-bold text-right">Win %</th>
                  <th className="p-4 font-bold text-right">Score</th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((entry) => (
                  <tr
                    key={entry.username}
                    className="border-b border-[rgb(var(--bg-elevated))] hover:bg-[rgb(var(--bg-elevated))] transition-colors"
                  >
                    <td className={`p-4 text-sm ${RANK_STYLE[entry.rank] ?? "text-[rgb(var(--text-muted))]"}`}>
                      {entry.rank <= 3 ? ["", "🥇", "🥈", "🥉"][entry.rank] : entry.rank}
                    </td>
                    <td className="p-4 text-sm font-bold text-[rgb(var(--text-fg))] uppercase tracking-wide">
                      {entry.username}
                    </td>
                    <td className="p-4 text-sm text-[rgb(var(--text-muted))] text-right">{entry.total_matches}</td>
                    <td className="p-4 text-sm text-emerald-600 text-right font-bold">{entry.total_wins}</td>
                    <td className="p-4 text-sm text-[rgb(var(--text-fg))] text-right">
                      {Math.round(entry.win_rate * 100)}%
                    </td>
                    <td className="p-4 text-right">
                      <span className="text-xs font-bold text-[#075E54] bg-[#DCF8C6] border border-[#A8D9AC] px-2 py-0.5 rounded-md">
                        {(entry.score * 100).toFixed(1)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Mobile card list */}
          <div className="sm:hidden divide-y divide-[rgb(var(--bg-elevated))]">
            {data.entries.map((entry) => (
              <div key={entry.username} className="p-4 font-mono">
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${RANK_STYLE[entry.rank] ?? "text-[rgb(var(--text-muted))]"}`}>
                      {entry.rank <= 3 ? ["", "🥇", "🥈", "🥉"][entry.rank] : `#${entry.rank}`}
                    </span>
                    <span className="text-sm font-bold text-[rgb(var(--text-fg))] uppercase tracking-wide">
                      {entry.username}
                    </span>
                  </div>
                  <span className="text-xs font-bold text-[#075E54] bg-[#DCF8C6] border border-[#A8D9AC] px-2 py-0.5 rounded-md shrink-0">
                    {(entry.score * 100).toFixed(1)}
                  </span>
                </div>
                <div className="flex gap-4 text-[10px] text-[rgb(var(--text-muted))] uppercase tracking-widest">
                  <span>Matches: <span className="text-[rgb(var(--text-fg))] font-bold">{entry.total_matches}</span></span>
                  <span>Wins: <span className="text-emerald-600 font-bold">{entry.total_wins}</span></span>
                  <span>Win %: <span className="text-[rgb(var(--text-fg))] font-bold">{Math.round(entry.win_rate * 100)}%</span></span>
                </div>
              </div>
            ))}
          </div>

          <div className="bg-[rgb(var(--bg-elevated))] p-3 border-t border-[rgb(var(--border-sub))] text-right">
            <span className="text-[10px] text-[rgb(var(--text-muted))] uppercase font-mono tracking-widest">
              {data.total_players} ranked player{data.total_players !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
