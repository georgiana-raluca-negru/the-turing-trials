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
    <div className="flex flex-col items-center justify-center flex-grow p-4 min-h-[calc(100vh-57px)] bg-[rgb(var(--bg-page))]">
      <div className="w-full max-w-md bg-[rgb(var(--bg-surface))] rounded-2xl border border-[rgb(var(--border-sub))] shadow-lg p-8">

        <div className="text-center mb-8 border-b border-[rgb(var(--border-sub))] pb-6">
          <div className="w-12 h-12 bg-[#075E54] rounded-full flex items-center justify-center mx-auto mb-3 shadow-md">
            <span className="text-white text-xl font-black">T</span>
          </div>
          <h2 className="text-2xl font-black uppercase tracking-widest text-[rgb(var(--heading))]">
            Authorization
          </h2>
          <p className="text-[10px] font-mono text-[rgb(var(--text-muted))] mt-1 uppercase tracking-widest">
            Secure Connection // Enter Credentials
          </p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
          <div className="group">
            <label className="block text-xs font-mono font-bold mb-2 uppercase tracking-widest text-[rgb(var(--text-muted))] group-focus-within:text-[rgb(var(--heading))] transition-colors">
              &gt; User_Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full p-3 bg-[rgb(var(--bg-elevated))] border border-[rgb(var(--border-sub))] rounded-lg text-[rgb(var(--text-fg))] font-mono text-sm focus:ring-2 focus:ring-[#25D366] focus:border-[#25D366] outline-none transition-all placeholder:text-[rgb(var(--text-muted))]/60"
              placeholder="agent@turing.net"
              required
              disabled={isLoading}
            />
          </div>

          <div className="group">
            <label className="block text-xs font-mono font-bold mb-2 uppercase tracking-widest text-[rgb(var(--text-muted))] group-focus-within:text-[rgb(var(--heading))] transition-colors">
              &gt; Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full p-3 bg-[rgb(var(--bg-elevated))] border border-[rgb(var(--border-sub))] rounded-lg text-[rgb(var(--text-fg))] font-mono text-sm focus:ring-2 focus:ring-[#25D366] focus:border-[#25D366] outline-none transition-all placeholder:text-[rgb(var(--text-muted))]/60"
              placeholder="••••••••"
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className={`w-full py-3.5 mt-2 font-mono font-bold uppercase tracking-widest rounded-lg transition-all duration-200 cursor-pointer ${
              isLoading
                ? "bg-[rgb(var(--border-sub))] text-white cursor-wait"
                : "bg-[#25D366] text-white hover:bg-[#128C7E] shadow-[0_2px_8px_rgba(37,211,102,0.35)]"
            }`}
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Validating…
              </span>
            ) : (
              "Authenticate"
            )}
          </button>
        </form>

        <div className="mt-6 text-center border-t border-[rgb(var(--border-sub))] pt-5">
          <p className="text-xs font-mono text-[rgb(var(--text-muted))]">
            No active profile?{" "}
            <Link href="/register" className="text-[rgb(var(--heading))] hover:text-[#25D366] font-bold transition-colors uppercase tracking-wider">
              [ Create Account ]
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
