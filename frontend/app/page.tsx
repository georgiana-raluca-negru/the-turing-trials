"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(!!localStorage.getItem("turing_access_token"));
  }, []);

  return (
    <div className="flex flex-col items-center flex-grow bg-[#ECE5DD] min-h-[calc(100vh-57px)]">

      {/* Hero */}
      <div className="w-full max-w-4xl px-6 py-14 text-center">
        <h2 className="text-5xl sm:text-6xl font-black mb-4 tracking-tighter uppercase text-[#075E54]">
          The Turing Trials
        </h2>
        <p className="text-sm font-mono text-[#128C7E] uppercase tracking-widest mb-6">
          [ Protocol: AI Confrontation Simulator ]
        </p>
        <p className="text-base text-[#667781] max-w-2xl mx-auto font-sans leading-relaxed">
          A gamified courtroom where AI agents argue cases generated from your prompt.
          Choose your role, use evidence strategically, and face the AI Judge&apos;s verdict.
        </p>
      </div>

      {/* CTA buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center items-center px-6 pb-12">
        {isLoggedIn ? (
          <>
            <Link
              href="/setup"
              className="w-full sm:w-auto px-8 py-3.5 bg-[#25D366] text-white font-mono font-bold uppercase tracking-wider rounded-lg shadow-[0_2px_8px_rgba(37,211,102,0.35)] hover:bg-[#128C7E] transition-all duration-200 hover:-translate-y-0.5 text-center"
            >
              Initiate Trial
            </Link>
            <Link
              href="/dashboard"
              className="w-full sm:w-auto px-8 py-3.5 bg-white text-[#075E54] font-mono font-bold uppercase tracking-wider rounded-lg border border-[#D1D7DB] shadow-sm hover:bg-[#F0F2F5] hover:border-[#128C7E] transition-all duration-200 hover:-translate-y-0.5 text-center"
            >
              Access Archives
            </Link>
          </>
        ) : (
          <>
            <Link
              href="/register"
              className="w-full sm:w-auto px-8 py-3.5 bg-[#25D366] text-white font-mono font-bold uppercase tracking-wider rounded-lg shadow-[0_2px_8px_rgba(37,211,102,0.35)] hover:bg-[#128C7E] transition-all duration-200 hover:-translate-y-0.5 text-center"
            >
              Create Account
            </Link>
            <Link
              href="/login"
              className="w-full sm:w-auto px-8 py-3.5 bg-white text-[#075E54] font-mono font-bold uppercase tracking-wider rounded-lg border border-[#D1D7DB] shadow-sm hover:bg-[#F0F2F5] hover:border-[#128C7E] transition-all duration-200 hover:-translate-y-0.5 text-center"
            >
              Log In
            </Link>
          </>
        )}
      </div>

      {/* Divider */}
      <div className="w-full max-w-4xl px-6 border-t border-[#D1D7DB]" />

      {/* Lore / Story */}
      <div className="w-full max-w-4xl px-6 py-12">
        <p className="text-[10px] font-mono text-[#128C7E] uppercase tracking-widest mb-3">Background</p>
        <h3 className="text-2xl font-black uppercase tracking-tight text-[#075E54] mb-5">
          The Year is 2031.
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm text-[#667781] font-sans leading-relaxed">
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
      <div className="w-full max-w-4xl px-6 border-t border-[#D1D7DB]" />

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
            <div key={item.step} className="bg-white border border-[#D1D7DB] rounded-xl p-5 shadow-sm">
              <p className="text-2xl font-black text-[#B2DFDB] font-mono mb-2">{item.step}</p>
              <h4 className="text-xs font-bold uppercase tracking-widest text-[#075E54] mb-2">{item.title}</h4>
              <p className="text-[11px] text-[#667781] leading-relaxed">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="w-full max-w-4xl px-6 border-t border-[#D1D7DB]" />

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
            <div key={i} className="flex gap-3 items-start bg-white border border-[#D1D7DB] rounded-lg p-4 shadow-sm">
              <span className="text-[10px] font-black font-mono text-[#B2DFDB] shrink-0 mt-0.5">
                {String(i + 1).padStart(2, "0")}
              </span>
              <p className="text-[11px] text-[#667781] leading-relaxed">{rule}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="w-full max-w-4xl px-6 py-12 border-t border-[#D1D7DB] text-center">
        <h3 className="text-xl font-black uppercase tracking-tight text-[#075E54] mb-3">
          Ready to enter the court?
        </h3>
        <p className="text-sm text-[#667781] mb-6 font-sans">
          {isLoggedIn
            ? "A new case awaits. Generate your trial and take your position."
            : "Create a free account and start your first trial in minutes."}
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {isLoggedIn ? (
            <Link
              href="/setup"
              className="px-8 py-3.5 bg-[#25D366] text-white font-mono font-bold uppercase tracking-wider rounded-lg shadow-[0_2px_8px_rgba(37,211,102,0.35)] hover:bg-[#128C7E] transition-all duration-200 hover:-translate-y-0.5"
            >
              Initiate Trial
            </Link>
          ) : (
            <>
              <Link
                href="/register"
                className="px-8 py-3.5 bg-[#25D366] text-white font-mono font-bold uppercase tracking-wider rounded-lg shadow-[0_2px_8px_rgba(37,211,102,0.35)] hover:bg-[#128C7E] transition-all duration-200 hover:-translate-y-0.5"
              >
                Create Account
              </Link>
              <Link
                href="/login"
                className="px-8 py-3.5 bg-white text-[#075E54] font-mono font-bold uppercase tracking-wider rounded-lg border border-[#D1D7DB] shadow-sm hover:bg-[#F0F2F5] hover:border-[#128C7E] transition-all duration-200 hover:-translate-y-0.5"
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
