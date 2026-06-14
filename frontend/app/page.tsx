"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const HERO_TEXT =
  "Human intellect vs. Artificial logic. The scales of justice are in your hands.";

function TypingSubtitle({ text }: { text: string }) {
  const [chars, setChars] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setChars((prev) => (prev >= text.length ? prev : prev + 1));
    }, 35);
    return () => clearInterval(interval);
  }, [text]);

  return (
    <p className="font-mono text-sm sm:text-base text-[#39FF8A] max-w-2xl mx-auto leading-[1.6] min-h-[3.2em]">
      {text.slice(0, chars)}
      <span className="cursor-blink">_</span>
    </p>
  );
}

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time sync from localStorage after mount, required for SSR-safe rendering
    setIsLoggedIn(!!localStorage.getItem("turing_access_token"));
  }, []);

  return (
    <div className="flex flex-col items-center flex-grow bg-[rgb(var(--bg-page))] min-h-[calc(100vh-57px)] relative overflow-hidden">

      {/* Animated cyber grid backdrop */}
      <div className="absolute inset-0 -z-10 bg-[linear-gradient(to_right,rgb(var(--border-sub))_1px,transparent_1px),linear-gradient(to_bottom,rgb(var(--border-sub))_1px,transparent_1px)] bg-[size:3rem_3rem] [mask-image:radial-gradient(ellipse_70%_50%_at_50%_0%,#000_40%,transparent_100%)] opacity-30" />

      {/* Hero */}
      <div className="w-full max-w-4xl px-6 py-14 text-center fade-in-up">
        <h2 className="text-5xl sm:text-6xl font-black mb-4 tracking-tighter uppercase text-[rgb(var(--heading))]">
          The Turing Trials
        </h2>
        <p className="text-sm font-mono text-[#128C7E] uppercase tracking-widest mb-6 fade-in-up" style={{ animationDelay: "0.1s" }}>
          [ Protocol: AI Confrontation Simulator ]
        </p>
        <div className="fade-in-up" style={{ animationDelay: "0.2s" }}>
          <TypingSubtitle text={HERO_TEXT} />
        </div>
        <p className="text-base text-[rgb(var(--text-fg))] max-w-2xl mx-auto font-sans leading-[1.6] mt-4 fade-in-up" style={{ animationDelay: "0.3s" }}>
          A gamified courtroom where AI agents argue cases generated from your prompt.
          Choose your role, use evidence strategically, and face the AI Judge&apos;s verdict.
        </p>
      </div>

      {/* CTA buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center items-center px-6 pb-12 fade-in-up" style={{ animationDelay: "0.4s" }}>
        {isLoggedIn ? (
          <>
            <Link
              href="/setup"
              className="pulse-glow w-full sm:w-auto px-8 py-3.5 bg-[#25D366] text-white font-mono font-bold uppercase tracking-wider rounded-lg hover:bg-[#128C7E] transition-all duration-200 hover:-translate-y-0.5 text-center"
            >
              Initiate Trial
            </Link>
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-8 py-3.5 bg-[rgb(var(--bg-surface))] text-[rgb(var(--heading))] font-mono font-bold uppercase tracking-wider rounded-lg border border-[rgb(var(--border-sub))] shadow-sm hover:bg-[rgb(var(--bg-elevated))] hover:border-[#128C7E] transition-all duration-200 hover:-translate-y-0.5 text-center"
            >
              Access Archives
            </Link>
          </>
        ) : (
          <>
            <Link
              href="/register"
              className="pulse-glow w-full sm:w-auto px-8 py-3.5 bg-[#25D366] text-white font-mono font-bold uppercase tracking-wider rounded-lg hover:bg-[#128C7E] transition-all duration-200 hover:-translate-y-0.5 text-center"
            >
              Create Account
            </Link>
            <Link
              href="/login"
              className="w-full sm:w-auto px-8 py-3.5 bg-[rgb(var(--bg-surface))] text-[rgb(var(--heading))] font-mono font-bold uppercase tracking-wider rounded-lg border border-[rgb(var(--border-sub))] shadow-sm hover:bg-[rgb(var(--bg-elevated))] hover:border-[#128C7E] transition-all duration-200 hover:-translate-y-0.5 text-center"
            >
              Log In
            </Link>
          </>
        )}
      </div>

      {/* Divider */}
      <div className="w-full max-w-4xl px-6 border-t border-[rgb(var(--border-sub))]" />

      {/* Lore / Story */}
      <div className="w-full max-w-4xl px-6 py-12">
        <p className="text-[10px] font-mono text-[#128C7E] uppercase tracking-widest mb-3">Background</p>
        <h3 className="text-2xl font-black uppercase tracking-tight text-[rgb(var(--heading))] mb-5">
          The Year is 2031.
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm text-[rgb(var(--text-muted))] font-sans leading-[1.6]">
          <p>
            The first AI rights tribunal convened in Geneva after a neural network — operating
            autonomously — deleted a city&apos;s power grid to prevent what it calculated would
            be a larger catastrophe. Twelve people died in the blackout. The AI had no voice in
            court. No one knew how to give it one.
          </p>
          <p>
            The Turing Trials were born from that silence. A simulated arena where human agents
            take on roles inside AI-generated legal cases — as defenders, prosecutors, or judges —
            and argue alongside, and against, advanced AI legal systems. Every verdict is a
            precedent. Every case tests not just the law, but the nature of intelligence itself.
          </p>
        </div>
      </div>

      {/* Divider */}
      <div className="w-full max-w-4xl px-6 border-t border-[rgb(var(--border-sub))]" />

      {/* How it works */}
      <div className="w-full max-w-4xl px-6 py-12">
        <p className="text-[10px] font-mono text-[#128C7E] uppercase tracking-widest mb-6">How It Works</p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            {
              step: "01",
              title: "Generate a Case",
              desc: "You describe a scenario — an AI action, a crime, a moral dilemma. The AI Clerk builds the full case file: charges, background, and a unique evidence inventory for each side.",
            },
            {
              step: "02",
              title: "Choose Your Role",
              desc: "Enter as Defense Attorney to protect the accused, Prosecutor to seek conviction, or Judge to evaluate both sides and deliver the final verdict. Each role receives different evidence.",
            },
            {
              step: "03",
              title: "Argue and Decide",
              desc: "Exchange arguments over multiple rounds. Attach evidence cards strategically — one per round. The AI Judge weighs every argument. The Scales of Justice shift in real time.",
            },
          ].map((item) => (
            <div key={item.step} className="bg-[rgb(var(--bg-surface))] border border-[rgb(var(--border-sub))] rounded-xl p-5 shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:border-[#25D366]/50 hover:shadow-[0_10px_30px_-8px_rgba(37,211,102,0.4)]">
              <p className="text-2xl font-black text-[rgb(var(--heading))]/40 font-mono mb-2">{item.step}</p>
              <h4 className="text-sm font-bold uppercase tracking-widest text-[rgb(var(--heading))] mb-2">{item.title}</h4>
              <p className="text-sm text-[rgb(var(--text-muted))] leading-[1.6]">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="w-full max-w-4xl px-6 border-t border-[rgb(var(--border-sub))]" />

      {/* Rules */}
      <div className="w-full max-w-4xl px-6 py-12">
        <p className="text-[10px] font-mono text-[#128C7E] uppercase tracking-widest mb-6">Rules of the Court</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            "Each side presents arguments over a fixed number of rounds (3, 5, or 10).",
            "You may attach one evidence card per round — choose carefully, each card can only be used once.",
            "Evidence is role-specific: Defense and Prosecution receive different cards.",
            "The AI Judge evaluates all arguments and delivers a reasoned verdict at the end.",
            "The Scales of Justice update after every exchange, reflecting the current balance of arguments.",
            "You can abandon a trial at any time. Abandoned matches are saved to your archives.",
          ].map((rule, i) => (
            <div key={i} className="flex gap-3 items-start bg-[rgb(var(--bg-surface))] border border-[rgb(var(--border-sub))] rounded-lg p-4 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-[#25D366]/50 hover:shadow-[0_8px_24px_-6px_rgba(37,211,102,0.35)]">
              <span className="text-xs font-black font-mono text-[rgb(var(--heading))]/40 shrink-0 mt-0.5">
                {String(i + 1).padStart(2, "0")}
              </span>
              <p className="text-sm text-[rgb(var(--text-muted))] leading-[1.6]">{rule}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="w-full max-w-4xl px-6 py-12 border-t border-[rgb(var(--border-sub))] text-center">
        <h3 className="text-xl font-black uppercase tracking-tight text-[rgb(var(--heading))] mb-3">
          Ready to enter the court?
        </h3>
        <p className="text-sm text-[rgb(var(--text-muted))] mb-6 font-sans">
          {isLoggedIn
            ? "A new case awaits. Generate your trial and take your position."
            : "Create a free account and start your first trial in minutes."}
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {isLoggedIn ? (
            <Link
              href="/setup"
              className="pulse-glow px-8 py-3.5 bg-[#25D366] text-white font-mono font-bold uppercase tracking-wider rounded-lg hover:bg-[#128C7E] transition-all duration-200 hover:-translate-y-0.5"
            >
              Initiate Trial
            </Link>
          ) : (
            <>
              <Link
                href="/register"
                className="pulse-glow px-8 py-3.5 bg-[#25D366] text-white font-mono font-bold uppercase tracking-wider rounded-lg hover:bg-[#128C7E] transition-all duration-200 hover:-translate-y-0.5"
              >
                Create Account
              </Link>
              <Link
                href="/login"
                className="px-8 py-3.5 bg-[rgb(var(--bg-surface))] text-[rgb(var(--heading))] font-mono font-bold uppercase tracking-wider rounded-lg border border-[rgb(var(--border-sub))] shadow-sm hover:bg-[rgb(var(--bg-elevated))] hover:border-[#128C7E] transition-all duration-200 hover:-translate-y-0.5"
              >
                Log In
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
