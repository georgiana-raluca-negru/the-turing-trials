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
  1: "text-yellow-400 font-black",
  2: "text-slate-300 font-bold",
  3: "text-amber-600 font-bold",
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
    <div className="max-w-3xl mx-auto w-full px-4 sm:px-6 py-8 min-h-[calc(100vh-120px)] flex flex-col gap-6">

      {/* Header */}
      <div className="border-b border-yellow-500/20 pb-4 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-cyan-400">
            Global Leaderboard
          </h2>
          <p className="text-xs font-mono text-yellow-500/60 mt-1 uppercase tracking-widest">
            Ranked by win score · volume + consistency required
          </p>
        </div>
        <Link
          href="/dashboard"
          className="self-start sm:self-auto text-xs font-mono text-slate-500 hover:text-cyan-400 uppercase tracking-widest transition-colors border border-slate-700 hover:border-cyan-500/40 px-3 py-1.5 rounded"
        >
          ← Archives
        </Link>
      </div>

      {/* Scoring note */}
      <div className="bg-slate-900/40 border border-yellow-500/10 rounded-lg px-4 py-3 font-mono text-[10px] text-slate-500 uppercase tracking-widest">
        Score = wins ÷ (matches + 5) · judges and spectators are excluded from ranking
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center flex-grow">
          <Spinner label="Loading rankings…" />
        </div>
      ) : error ? (
        <p className="text-red-400 font-mono text-sm text-center uppercase tracking-wider">{error}</p>
      ) : !data || data.entries.length === 0 ? (
        <p className="text-slate-500 font-mono text-xs text-center uppercase tracking-widest py-12">
          No ranked players yet. Play a match first.
        </p>
      ) : (
        <div className="bg-slate-900/40 backdrop-blur-sm rounded-lg border border-yellow-500/20 overflow-hidden">
          <table className="w-full text-left border-collapse font-mono">
            <thead>
              <tr className="bg-black/60 border-b border-yellow-500/20 text-[10px] text-yellow-300/70 uppercase tracking-wider">
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
                  className="border-b border-slate-800/50 hover:bg-yellow-500/5 transition-colors"
                >
                  <td className={`p-4 text-sm ${RANK_STYLE[entry.rank] ?? "text-slate-600"}`}>
                    {entry.rank <= 3 ? ["", "🥇", "🥈", "🥉"][entry.rank] : entry.rank}
                  </td>
                  <td className="p-4 text-sm font-bold text-slate-200 uppercase tracking-wide">
                    {entry.username}
                  </td>
                  <td className="p-4 text-sm text-slate-400 text-right">{entry.total_matches}</td>
                  <td className="p-4 text-sm text-emerald-400 text-right font-bold">{entry.total_wins}</td>
                  <td className="p-4 text-sm text-slate-300 text-right">
                    {Math.round(entry.win_rate * 100)}%
                  </td>
                  <td className="p-4 text-right">
                    <span className="text-xs font-bold text-yellow-400 bg-yellow-500/10 border border-yellow-500/30 px-2 py-0.5 rounded">
                      {(entry.score * 100).toFixed(1)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="bg-black/80 p-3 border-t border-yellow-500/20 text-right">
            <span className="text-[10px] text-slate-600 uppercase font-mono tracking-widest">
              {data.total_players} ranked player{data.total_players !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
