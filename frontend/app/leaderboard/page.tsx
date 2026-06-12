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
    <div className="max-w-3xl mx-auto w-full px-4 sm:px-6 py-8 min-h-[calc(100vh-57px)] flex flex-col gap-6 bg-[#ECE5DD]">

      {/* Header */}
      <div className="border-b border-[#D1D7DB] pb-4 flex flex-col sm:flex-row sm:justify-between sm:items-end gap-3">
        <div>
          <h2 className="text-2xl sm:text-3xl font-black uppercase tracking-widest text-[#075E54]">
            Global Leaderboard
          </h2>
          <p className="text-xs font-mono text-[#667781] mt-1 uppercase tracking-widest">
            Ranked by win score · volume + consistency required
          </p>
        </div>
        <Link
          href="/dashboard"
          className="self-start sm:self-auto text-xs font-mono text-[#667781] hover:text-[#075E54] uppercase tracking-widest transition-colors border border-[#D1D7DB] hover:border-[#128C7E] px-3 py-1.5 rounded-lg bg-white"
        >
          ← Archives
        </Link>
      </div>

      {/* Scoring note */}
      <div className="bg-white border border-[#D1D7DB] rounded-xl px-4 py-3 font-mono text-[10px] text-[#667781] uppercase tracking-widest shadow-sm">
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
        <p className="text-[#667781] font-mono text-xs text-center uppercase tracking-widest py-12">
          No ranked players yet. Play a match first.
        </p>
      ) : (
        <div className="bg-white rounded-2xl border border-[#D1D7DB] overflow-hidden shadow-sm">
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
                  className="border-b border-[#F0F2F5] hover:bg-[#F0F2F5] transition-colors"
                >
                  <td className={`p-4 text-sm ${RANK_STYLE[entry.rank] ?? "text-[#667781]"}`}>
                    {entry.rank <= 3 ? ["", "🥇", "🥈", "🥉"][entry.rank] : entry.rank}
                  </td>
                  <td className="p-4 text-sm font-bold text-[#111B21] uppercase tracking-wide">
                    {entry.username}
                  </td>
                  <td className="p-4 text-sm text-[#667781] text-right">{entry.total_matches}</td>
                  <td className="p-4 text-sm text-emerald-600 text-right font-bold">{entry.total_wins}</td>
                  <td className="p-4 text-sm text-[#111B21] text-right">
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
          <div className="bg-[#F0F2F5] p-3 border-t border-[#D1D7DB] text-right">
            <span className="text-[10px] text-[#667781] uppercase font-mono tracking-widest">
              {data.total_players} ranked player{data.total_players !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
