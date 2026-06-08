"use client";

import { useEffect, useState, useRef, use } from "react";
import { useRouter } from "next/navigation";
import ScalesOfJustice from "@/components/courtroom/ScalesOfJustice";
import CaseSummary from "@/components/courtroom/CaseSummary";
import EvidenceFolder, { EvidenceItem } from "@/components/courtroom/EvidenceFolder";
import Spinner from "@/components/ui/Spinner";
import { useToast } from "@/components/ui/Toast";
import { apiJson, apiFetch } from "@/lib/api";

/* ── Backend types ────────────────────────────────────────────────────────── */
interface MatchOut {
  id: string;
  player_prompt: string;
  case_summary: string | null;
  player_role: string;
  status: string;
  total_rounds: number;
  verdict: string | null;
  verdict_reasoning: string | null;
}

interface TranscriptEntry {
  turn_index: number;
  cycle: number;
  actor: string;       // "prosecution" | "defense" | "judge"
  controller: string;  // "human" | "ai"
  text: string;
  evidence_ids: string[];
  skipped: boolean;
  system_note: string | null;
}

interface VerdictData {
  guilty: boolean | null;
  reasoning: string;
  prosecution_score: number | null;
  defense_score: number | null;
  verdict_text: string | null;
}

interface GameState {
  match_id: string;
  status: string;
  player_role: string;
  current_round: number;
  max_rounds: number;
  scales_value: number;
  case_summary: { crime: string; charges: string[]; background_story: string } | null;
  transcript: TranscriptEntry[];
  verdict: VerdictData | null;
  waiting_for: string | null;
}

interface EvidenceCard {
  id: string;
  title: string;
  description: string;
  assigned_role: string;
  is_used: boolean;
  used_in_round: number | null;
  card_order: number;
}

interface ChatMessage {
  id: string;
  role: "prosecutor" | "defense" | "judge" | "user";
  content: string;
  round: number;
  attachments?: string[];
}

/* ── Constants & helpers ──────────────────────────────────────────────────── */
const ACTOR_TO_MSG_ROLE: Record<string, ChatMessage["role"]> = {
  prosecution: "prosecutor",
  defense: "defense",
  judge: "judge",
};

const PLAYER_ACTOR: Record<string, string> = {
  defense_attorney: "defense",
  prosecutor: "prosecution",
  judge: "judge",
};

// backend scales_value: -1.0 (defense) → +1.0 (prosecution)
// ScalesOfJustice: 0 (defense) → 100 (prosecution), 50 = tie
const toDisplayScore = (v: number) => Math.round((v + 1) * 50);

function transcriptToMessages(
  entries: TranscriptEntry[],
  playerRole: string,
): ChatMessage[] {
  const playerActor = PLAYER_ACTOR[playerRole];
  return entries
    .filter((t) => !t.skipped && t.text.trim().length > 0)
    .map((t) => ({
      id: `t-${t.turn_index}`,
      role:
        t.controller === "human" && t.actor === playerActor
          ? "user"
          : (ACTOR_TO_MSG_ROLE[t.actor] ?? "judge"),
      content: t.text,
      round: t.cycle,
    }));
}

function evidenceToItems(cards: EvidenceCard[]): EvidenceItem[] {
  return cards.map((c) => ({
    id: c.id,
    title: c.title,
    desc: c.description,
    used: c.is_used,
  }));
}

/* ── Component ────────────────────────────────────────────────────────────── */
export default function CourtroomPage({
  params,
}: {
  params: Promise<{ matchID: string }>;
}) {
  const { matchID } = use(params);
  const router = useRouter();
  const { showToast } = useToast();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [match, setMatch] = useState<MatchOut | null>(null);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [attachedEvidence, setAttachedEvidence] = useState<string | null>(null);
  const [displayScore, setDisplayScore] = useState(50);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [argumentBuffer, setArgumentBuffer] = useState("");
  const [mobilePanelTab, setMobilePanelTab] = useState<"chat" | "case" | "evidence">("chat");

  const chatEndRef = useRef<HTMLDivElement>(null);

  /* ── Load match + start/resume session ────────────────────────────────── */
  useEffect(() => {
    const load = async () => {
      if (!localStorage.getItem("turing_access_token")) {
        router.push("/login");
        return;
      }

      try {
        // 1. Get match metadata
        const matchData = await apiJson<MatchOut>(`/api/matches/${matchID}`);
        setMatch(matchData);

        let state: GameState;

        if (matchData.status === "lobby") {
          // 2a. Start session — triggers AI Clerk case generation
          const res = await apiFetch("/api/sessions/", {
            method: "POST",
            body: JSON.stringify({ match_id: matchID }),
          });

          if (res.ok) {
            state = await res.json();
          } else if (res.status === 409) {
            // Session already exists (page reload after start)
            state = await apiJson<GameState>(`/api/sessions/${matchID}`);
          } else {
            const err = await res.json().catch(() => ({}));
            const detail = Array.isArray(err.detail)
              ? err.detail.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join(", ")
              : err.detail ?? `Server error ${res.status}`;
            throw new Error(detail);
          }
        } else {
          // 2b. Resume existing session
          state = await apiJson<GameState>(`/api/sessions/${matchID}`);
        }

        setGameState(state);
        setDisplayScore(toDisplayScore(state.scales_value ?? 0));
        setMessages(transcriptToMessages(state.transcript, matchData.player_role));

        // 3. Fetch role-specific evidence
        const cards = await apiJson<EvidenceCard[]>(`/api/evidence/${matchID}`);
        setEvidence(evidenceToItems(cards));
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to load courtroom.";
        setError(msg);
        showToast(msg, "error");
      } finally {
        setIsLoading(false);
      }
    };
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matchID]);

  /* ── Auto-scroll ──────────────────────────────────────────────────────── */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ── Apply updated game state from API response ───────────────────────── */
  function applyGameState(state: GameState, playerRole: string) {
    setGameState(state);
    setDisplayScore(toDisplayScore(state.scales_value ?? 0));
    setMessages(transcriptToMessages(state.transcript, playerRole));
    // Sync evidence used-status from transcript
    setEvidence((prev) =>
      prev.map((e) => {
        const usedInTranscript = state.transcript.some((t) =>
          t.evidence_ids.includes(String(e.id)),
        );
        return usedInTranscript ? { ...e, used: true } : e;
      }),
    );
  }

  /* ── Attach evidence ──────────────────────────────────────────────────── */
  function handleAttach(id: string | number) {
    const strId = String(id);
    if (attachedEvidence === strId) {
      setAttachedEvidence(null);
      return;
    }
    setAttachedEvidence(strId);
    const item = evidence.find((e) => String(e.id) === strId);
    if (item) showToast(`Attached: ${item.title}`, "info");
  }

  /* ── Submit argument ──────────────────────────────────────────────────── */
  async function handleSubmitArgument() {
    if (!argumentBuffer.trim() || isSubmitting || !match) return;
    setIsSubmitting(true);

    try {
      const state = await apiJson<GameState>(`/api/sessions/${matchID}/turn`, {
        method: "POST",
        body: JSON.stringify({
          argument_text: argumentBuffer.trim(),
          attached_evidence_id: attachedEvidence ?? null,
        }),
      });

      setArgumentBuffer("");
      setAttachedEvidence(null);
      applyGameState(state, match.player_role);

      if (state.verdict) {
        const label =
          state.verdict.guilty === true
            ? "GUILTY"
            : state.verdict.guilty === false
            ? "NOT GUILTY"
            : "PENDING";
        showToast(`Trial concluded. Verdict: ${label}`, "info");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit argument.";
      showToast(`Transmission error: ${msg}`, "error");
    } finally {
      setIsSubmitting(false);
    }
  }

  /* ── Loading ──────────────────────────────────────────────────────────── */
  if (isLoading) {
    return (
      <div className="flex items-center justify-center flex-grow min-h-[calc(100vh-73px)] bg-slate-950">
        <Spinner label="Initializing Courtroom..." size="lg" />
      </div>
    );
  }

  if (error || !match || !gameState) {
    return (
      <div className="flex flex-col items-center justify-center flex-grow min-h-[calc(100vh-73px)] bg-slate-950 gap-4">
        <p className="font-mono text-red-400 text-sm border border-red-500/40 bg-red-950/30 px-6 py-4 rounded uppercase tracking-wider">
          ERR: {error || "Match not found"}
        </p>
        <button
          onClick={() => router.push("/dashboard")}
          className="text-xs font-mono text-slate-400 hover:text-cyan-400 uppercase tracking-widest transition-colors cursor-pointer"
        >
          Return to Archives
        </button>
      </div>
    );
  }

  /* ── Derived state ────────────────────────────────────────────────────── */
  const playerActor = PLAYER_ACTOR[match.player_role] ?? null;
  const isMyTurn = gameState.waiting_for === playerActor;
  const isCompleted = gameState.status === "completed" || gameState.status === "quit";

  const roleLabel: Record<string, string> = {
    defense_attorney: "DEFENSE_COUNSEL",
    prosecutor: "PROSECUTOR",
    judge: "JUDGE",
    spectator: "SPECTATOR",
  };

  const aiRoleLabel =
    match.player_role === "defense_attorney"
      ? "PROSECUTOR_AGENT"
      : match.player_role === "prosecutor"
      ? "DEFENSE_AGENT"
      : "AI_AGENT";

  const caseSummaryText = gameState.case_summary
    ? `${gameState.case_summary.crime}: ${gameState.case_summary.charges.join(", ")}`
    : match.case_summary;

  const verdictLabel =
    gameState.verdict?.guilty === true
      ? "GUILTY"
      : gameState.verdict?.guilty === false
      ? "NOT_GUILTY"
      : match.verdict === "guilty"
      ? "GUILTY"
      : match.verdict === "not_guilty"
      ? "NOT_GUILTY"
      : "PENDING";

  /* ── Message bubble ───────────────────────────────────────────────────── */
  function MessageBubble({
    msg,
    playerRole,
    maxRounds,
  }: {
    msg: ChatMessage;
    playerRole: string;
    maxRounds: number;
  }) {
    const isUser = msg.role === "user";
    const isJudge = msg.role === "judge";

    const bubbleClass = isJudge
      ? "bg-yellow-950/20 border border-yellow-500/20 max-w-full"
      : isUser
      ? "bg-cyan-950/20 border border-cyan-500/20 max-w-[92%] ml-auto"
      : "bg-purple-950/20 border border-purple-500/20 max-w-[92%]";

    const labelColor = isJudge
      ? "text-yellow-400"
      : isUser
      ? "text-cyan-400"
      : "text-purple-400";

    const label = isJudge
      ? "[ AI_JUDGE ]"
      : isUser
      ? `[ ${roleLabel[playerRole] ?? "COUNSEL"} (YOU) ]`
      : `[ ${aiRoleLabel} ]`;

    return (
      <div className={`p-3 sm:p-4 rounded-lg font-mono text-xs ${bubbleClass}`}>
        <div className="flex justify-between items-center mb-1.5 border-b border-current/10 pb-1">
          <span className={`font-bold uppercase tracking-widest text-[10px] sm:text-xs ${labelColor}`}>
            {label}
          </span>
          {msg.round > 0 && (
            <span className="text-[10px] text-slate-500 shrink-0 ml-2">
              Cycle {msg.round}/{maxRounds}
            </span>
          )}
        </div>
        <p className="text-slate-300 font-sans leading-relaxed text-xs sm:text-sm">
          {msg.content}
        </p>
        {msg.attachments && msg.attachments.length > 0 && (
          <div className="mt-2 pt-2 border-t border-cyan-500/10 flex flex-wrap gap-1">
            {msg.attachments.map((a) => (
              <span
                key={a}
                className="text-[9px] font-mono bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-1.5 py-0.5 rounded uppercase"
              >
                Exhibit: {a}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  }

  /* ── Render ───────────────────────────────────────────────────────────── */
  return (
    <div className="flex flex-col h-[calc(100vh-56px)] sm:h-[calc(100vh-65px)] bg-slate-950 overflow-hidden relative">

      {/* Scales of Justice bar */}
      <div className="w-full px-4 py-2 border-b border-cyan-500/10 bg-black/40 backdrop-blur-sm shrink-0 z-10">
        <ScalesOfJustice score={displayScore} />
      </div>

      {/* Mobile tab switcher */}
      <div className="md:hidden flex border-b border-slate-800 bg-black/60 shrink-0">
        {(["chat", "case", "evidence"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setMobilePanelTab(tab)}
            className={`flex-1 py-2 text-[10px] font-mono font-bold uppercase tracking-widest transition-colors cursor-pointer ${
              mobilePanelTab === tab
                ? "text-cyan-400 border-b-2 border-cyan-500"
                : "text-slate-600 hover:text-slate-400"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 3-column layout */}
      <div className="flex flex-grow overflow-hidden relative z-10">

        {/* Left: Case Summary */}
        <aside
          className={`w-full md:w-1/4 p-4 border-r border-slate-900 bg-black/20 overflow-y-auto ${
            mobilePanelTab === "case" ? "block" : "hidden md:block"
          }`}
        >
          <CaseSummary
            matchId={match.id}
            caseSummary={caseSummaryText}
            playerRole={match.player_role}
            totalRounds={gameState.max_rounds}
            status={gameState.status}
            verdict={verdictLabel}
          />
        </aside>

        {/* Centre: Chat + input */}
        <section
          className={`w-full md:w-2/4 flex flex-col bg-slate-950/40 relative border-r border-l border-slate-900/50 ${
            mobilePanelTab === "chat" ? "flex" : "hidden md:flex"
          }`}
        >
          {/* Chat log */}
          <div className="flex-grow p-3 sm:p-4 overflow-y-auto space-y-3">
            {messages.length === 0 && (
              <div className="flex items-center justify-center h-full">
                <p className="font-mono text-slate-600 text-xs uppercase tracking-widest text-center">
                  Trial initializing… submit your opening argument.
                </p>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                playerRole={match.player_role}
                maxRounds={gameState.max_rounds}
              />
            ))}

            {/* AI computing indicator (while submit in flight) */}
            {isSubmitting && (
              <div className="p-3 bg-purple-950/20 border border-purple-500/20 rounded-lg max-w-[60%] font-mono text-xs">
                <span className="text-purple-400 text-[10px] uppercase tracking-widest">
                  {aiRoleLabel} is deliberating
                </span>
                <div className="flex gap-1 mt-2">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Verdict block */}
            {isCompleted && gameState.verdict && (
              <div
                className={`p-4 rounded-lg border font-mono text-xs mt-4 ${
                  gameState.verdict.guilty === true
                    ? "bg-red-950/30 border-red-500/40"
                    : gameState.verdict.guilty === false
                    ? "bg-emerald-950/30 border-emerald-500/40"
                    : "bg-yellow-950/30 border-yellow-500/40"
                }`}
              >
                <div
                  className={`text-sm font-bold uppercase tracking-widest mb-2 ${
                    gameState.verdict.guilty === true
                      ? "text-red-400"
                      : gameState.verdict.guilty === false
                      ? "text-emerald-400"
                      : "text-yellow-400"
                  }`}
                >
                  [ VERDICT:{" "}
                  {gameState.verdict.guilty === true
                    ? "GUILTY"
                    : gameState.verdict.guilty === false
                    ? "NOT GUILTY"
                    : "PENDING"}{" "}
                  ]
                </div>
                <p className="leading-relaxed text-slate-300">{gameState.verdict.reasoning}</p>
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Objection button (visible when AI has just replied and it's your turn) */}
          {isMyTurn && !isSubmitting && !isCompleted && (
            <div className="absolute bottom-32 right-4 sm:right-6 z-20">
              <button
                onClick={() => showToast("Objection noted — recorded for this round.", "warning")}
                className="bg-red-950/80 hover:bg-red-900/90 text-red-400 font-mono font-bold text-xs py-2 px-4 sm:py-3 sm:px-6 rounded border border-red-500 shadow-[0_0_20px_rgba(239,68,68,0.3)] hover:shadow-[0_0_35px_rgba(239,68,68,0.5)] transition-all duration-300 animate-pulse uppercase tracking-[0.15em] flex items-center gap-2 cursor-pointer"
              >
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                Objection!
              </button>
            </div>
          )}

          {/* Attached evidence chip */}
          {attachedEvidence && (
            <div className="px-4 pb-1 pt-1 flex gap-1 border-t border-slate-900">
              {(() => {
                const item = evidence.find((e) => String(e.id) === attachedEvidence);
                return item ? (
                  <span className="text-[9px] font-mono bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 px-1.5 py-0.5 rounded uppercase flex items-center gap-1">
                    {item.title}
                    <button
                      onClick={() => setAttachedEvidence(null)}
                      className="ml-0.5 opacity-60 hover:opacity-100 cursor-pointer"
                    >
                      ×
                    </button>
                  </span>
                ) : null;
              })()}
            </div>
          )}

          {/* Input area */}
          <div className="p-3 sm:p-4 border-t border-slate-900 bg-black/30 backdrop-blur-sm shrink-0">
            <div className="relative">
              <div className="absolute left-3 top-3 font-mono text-xs text-cyan-500/40 select-none">
                &gt;
              </div>
              <textarea
                value={argumentBuffer}
                onChange={(e) => setArgumentBuffer(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey))
                    handleSubmitArgument();
                }}
                className="w-full pl-7 p-3 bg-black/60 border border-slate-800 rounded text-slate-300 font-mono text-xs focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none resize-none shadow-inner placeholder:text-slate-700"
                placeholder={
                  isCompleted
                    ? "Trial concluded."
                    : isSubmitting
                    ? "Transmitting…"
                    : isMyTurn
                    ? "Draft legal argument… (Ctrl+Enter to submit)"
                    : "Awaiting opponent's argument…"
                }
                rows={3}
                disabled={isSubmitting || isCompleted || !isMyTurn}
              />
            </div>

            <div className="mt-2 flex justify-between items-center gap-2">
              <span className="text-[10px] font-mono text-slate-600 uppercase shrink-0">
                {isCompleted
                  ? "TRIAL_COMPLETE"
                  : isSubmitting
                  ? "TRANSMITTING…"
                  : isMyTurn
                  ? "Mode: BROADCAST_READY"
                  : "Mode: READ_ONLY"}
              </span>
              <button
                onClick={handleSubmitArgument}
                disabled={
                  isSubmitting || isCompleted || !argumentBuffer.trim() || !isMyTurn
                }
                className={`px-4 sm:px-6 py-2 font-mono text-xs font-bold uppercase tracking-wider rounded border transition-all cursor-pointer ${
                  isSubmitting || isCompleted || !argumentBuffer.trim() || !isMyTurn
                    ? "border-slate-800 text-slate-600 bg-transparent cursor-not-allowed"
                    : "border-cyan-500 text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20 shadow-[0_0_15px_rgba(34,211,238,0.1)]"
                }`}
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-2">
                    <span className="w-3 h-3 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin" />
                    Transmitting
                  </span>
                ) : (
                  "Transmit"
                )}
              </button>
            </div>
          </div>
        </section>

        {/* Right: Evidence Folder */}
        <aside
          className={`w-full md:w-1/4 p-4 border-l border-slate-900 bg-black/20 overflow-y-auto ${
            mobilePanelTab === "evidence" ? "block" : "hidden md:block"
          }`}
        >
          <EvidenceFolder
            items={evidence}
            onAttach={isMyTurn && !isSubmitting ? handleAttach : undefined}
          />
        </aside>
      </div>
    </div>
  );
}
