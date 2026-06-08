"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/ui/Toast";
import { apiFetch } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { showToast } = useToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.SyntheticEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const response = await apiFetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Authentication failed" }));
        throw new Error(err.detail ?? "Authentication failed");
      }

      const data = await response.json();
      localStorage.setItem("turing_access_token", data.access_token);
      showToast("Authentication successful. Welcome back.", "success");
      router.push("/dashboard");

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      showToast(`ERR: ${msg}`, "error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center flex-grow p-4 min-h-[calc(100vh-73px)] relative z-10">

      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-900/10 blur-[100px] -z-10 rounded-full" />

      <div className="w-full max-w-md bg-slate-900/80 backdrop-blur-md p-8 rounded-lg border border-cyan-500/30 shadow-[0_0_25px_rgba(0,0,0,0.8)]">

        <div className="text-center mb-8 border-b border-cyan-500/20 pb-4">
          <h2 className="text-2xl font-black uppercase tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-teal-200">
            Authorization
          </h2>
          <p className="text-[10px] font-mono text-cyan-500/60 mt-2 uppercase tracking-widest">
            Awaiting Credentials // Secure Connection
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div className="relative group">
            <label className="block text-xs font-mono font-bold mb-2 uppercase tracking-widest text-slate-400 group-focus-within:text-cyan-300 transition-colors">
              &gt; User_Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3 bg-black/50 border border-slate-700/50 rounded text-slate-200 font-mono text-sm focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none shadow-inner transition-all"
              placeholder="agent@turing.net"
              required
              disabled={isLoading}
            />
          </div>

          <div className="relative group">
            <label className="block text-xs font-mono font-bold mb-2 uppercase tracking-widest text-slate-400 group-focus-within:text-cyan-300 transition-colors">
              &gt; Password_Hash
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3 bg-black/50 border border-slate-700/50 rounded text-slate-200 font-mono text-sm focus:ring-1 focus:ring-cyan-500 focus:border-cyan-500 outline-none shadow-inner transition-all"
              placeholder="••••••••"
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-3.5 mt-2 font-mono font-bold uppercase tracking-widest border rounded transition-all duration-300 cursor-pointer ${
              isLoading
                ? "border-slate-800 text-slate-600 bg-transparent cursor-wait"
                : "bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border-cyan-500/50 hover:border-cyan-400 hover:shadow-[0_0_15px_rgba(34,211,238,0.2)]"
            }`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin" />
                Validating…
              </span>
            ) : (
              "Authenticate"
            )}
          </button>
        </form>

        <div className="mt-8 text-center border-t border-slate-800/50 pt-4">
          <p className="text-xs font-mono text-slate-500">
            No active profile?{" "}
            <Link href="/register" className="text-purple-400 hover:text-purple-300 transition-colors uppercase tracking-wider">
              [ Initialize Record ]
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
