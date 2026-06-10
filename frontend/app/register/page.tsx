"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import { apiFetch } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleRegister = async (e: React.SyntheticEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      showToast("Password hashes do not match.", "error");
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiFetch("/api/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, email, password }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Registration failed" }));
        throw new Error(err.detail ?? "Registration protocol failed");
      }

      const data = await response.json();
      localStorage.setItem("turing_access_token", data.access_token);
      showToast("Record initialized. Welcome, Agent.", "success");
      router.push("/setup");

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Registration failed";
      showToast(`ERR: ${msg}`, "error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center flex-grow p-4 min-h-[calc(100vh-73px)] relative z-10">

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-purple-900/10 blur-[100px] -z-10 rounded-full" />

      <div className="w-full max-w-md bg-slate-900/80 backdrop-blur-md p-8 rounded-lg border border-purple-500/30 shadow-[0_0_25px_rgba(0,0,0,0.8)]">

        <div className="text-center mb-8 border-b border-purple-500/20 pb-4">
          <h2 className="text-2xl font-black uppercase tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-cyan-200">
            Initialize Record
          </h2>
          <p className="text-[10px] font-mono text-purple-500/60 mt-2 uppercase tracking-widest">
            New User Registration Protocol
          </p>
        </div>

        <form onSubmit={handleRegister} className="space-y-5">
          <div className="relative group">
            <label className="block text-xs font-mono font-bold mb-2 uppercase tracking-widest text-slate-400 group-focus-within:text-purple-300 transition-colors">
              &gt; Agent_Alias (Username)
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full p-3 bg-black/50 border border-slate-700/50 rounded text-slate-200 font-mono text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500 outline-none shadow-inner transition-all"
              placeholder="NeonLawyer99"
              required
              disabled={isLoading}
            />
          </div>

          <div className="relative group">
            <label className="block text-xs font-mono font-bold mb-2 uppercase tracking-widest text-slate-400 group-focus-within:text-purple-300 transition-colors">
              &gt; User_Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3 bg-black/50 border border-slate-700/50 rounded text-slate-200 font-mono text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500 outline-none shadow-inner transition-all"
              placeholder="agent@turing.net"
              required
              disabled={isLoading}
            />
          </div>

          <div className="relative group">
            <label className="block text-xs font-mono font-bold mb-2 uppercase tracking-widest text-slate-400 group-focus-within:text-purple-300 transition-colors">
              &gt; Assign_Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3 bg-black/50 border border-slate-700/50 rounded text-slate-200 font-mono text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500 outline-none shadow-inner transition-all"
              placeholder="••••••••"
              required
              disabled={isLoading}
            />
          </div>

          <div className="relative group">
            <label className="block text-xs font-mono font-bold mb-2 uppercase tracking-widest text-slate-400 group-focus-within:text-purple-300 transition-colors">
              &gt; Confirm_Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full p-3 bg-black/50 border border-slate-700/50 rounded text-slate-200 font-mono text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500 outline-none shadow-inner transition-all"
              placeholder="••••••••"
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-3.5 mt-4 font-mono font-bold uppercase tracking-widest border rounded transition-all duration-300 cursor-pointer ${
              isLoading
                ? "border-slate-800 text-slate-600 bg-transparent cursor-wait"
                : "bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border-purple-500/50 hover:border-purple-400 hover:shadow-[0_0_15px_rgba(168,85,247,0.2)]"
            }`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-purple-500/30 border-t-purple-400 rounded-full animate-spin" />
                Generating Record…
              </span>
            ) : (
              "Submit Record"
            )}
          </button>
        </form>

        <div className="mt-8 text-center border-t border-slate-800/50 pt-4">
          <p className="text-xs font-mono text-slate-500">
            Already have clearance?{" "}
            <Link href="/login" className="text-cyan-400 hover:text-cyan-300 transition-colors uppercase tracking-wider">
              [ Secure Login ]
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
