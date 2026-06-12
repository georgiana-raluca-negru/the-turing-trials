"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useTheme } from "@/contexts/ThemeContext";

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const [username, setUsername] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [prevPathname, setPrevPathname] = useState(pathname);
  if (prevPathname !== pathname) {
    setPrevPathname(pathname);
    setMenuOpen(false);
  }

  useEffect(() => {
    const fetchUser = async () => {
      const token = localStorage.getItem("turing_access_token");
      if (!token) { setUsername(null); return; }

      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/api/users/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setUsername(data.username);
        } else {
          setUsername(null);
        }
      } catch {
        setUsername(null);
      }
    };
    fetchUser();
  }, [pathname]);

  const handleLogout = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      await fetch(`${apiUrl}/api/auth/logout`, { method: "POST" });
    } catch { /* ignore */ }
    localStorage.removeItem("turing_access_token");
    setUsername(null);
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-[#054d42] bg-[#075E54] shadow-[0_2px_8px_rgba(0,0,0,0.25)]">
      <div className="flex items-center justify-between px-4 py-3 max-w-7xl mx-auto w-full">

        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 group shrink-0">
          <div className="w-2.5 h-2.5 rounded-sm bg-[#25D366] shadow-[0_0_8px_rgba(37,211,102,0.6)] group-hover:scale-110 transition-transform" />
          <h1 className="text-base sm:text-lg font-mono font-black uppercase tracking-wider text-white">
            The Turing Trials <span className="text-xs text-[#B2DFDB] font-normal hidden sm:inline">v1.0</span>
          </h1>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex font-mono text-xs items-center gap-5">
          {username ? (
            <>
              <Link href="/dashboard" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest">
                [ Archives ]
              </Link>
              <Link href="/leaderboard" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest">
                [ Leaderboard ]
              </Link>
              <Link href="/setup" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest">
                [ New Trial ]
              </Link>
              <span className="text-white font-bold bg-white/10 px-2 py-1 rounded border border-white/20 uppercase">
                {username}
              </span>
              <button
                onClick={handleLogout}
                className="text-[#FF8A80] hover:text-white transition-colors border border-[#FF8A80]/40 hover:border-[#FF8A80] px-2 py-1 bg-white/5 uppercase tracking-widest text-[10px] cursor-pointer"
              >
                Disconnect
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest">
                [ Login ]
              </Link>
              <Link href="/register" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest">
                [ Register ]
              </Link>
            </>
          )}

          {/* Dark / Light toggle */}
          <button
            onClick={toggle}
            title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className="w-8 h-8 flex items-center justify-center rounded border border-white/20 hover:border-white/50 text-white/60 hover:text-white transition-all cursor-pointer"
          >
            {theme === "dark" ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                <circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
          </button>
        </nav>

        {/* Mobile: theme toggle + hamburger */}
        <div className="flex items-center gap-2 md:hidden">
          <button
            onClick={toggle}
            className="w-8 h-8 flex items-center justify-center rounded border border-white/20 text-white/60 cursor-pointer"
          >
            {theme === "dark" ? (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                <circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            )}
          </button>

          <button
            onClick={() => setMenuOpen((v) => !v)}
            aria-label="Toggle menu"
            className="w-8 h-8 flex flex-col items-center justify-center gap-1.5 cursor-pointer"
          >
            <span className={`block h-0.5 w-5 bg-white transition-all ${menuOpen ? "rotate-45 translate-y-2" : ""}`} />
            <span className={`block h-0.5 w-5 bg-white transition-all ${menuOpen ? "opacity-0" : ""}`} />
            <span className={`block h-0.5 w-5 bg-white transition-all ${menuOpen ? "-rotate-45 -translate-y-2" : ""}`} />
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {menuOpen && (
        <div className="md:hidden border-t border-[#054d42] bg-[#075E54] px-4 py-4 flex flex-col gap-4 font-mono text-xs">
          {username ? (
            <>
              <div className="text-white font-bold uppercase tracking-widest border-b border-white/10 pb-3">
                Agent: {username}
              </div>
              <Link href="/dashboard" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest py-1">
                [ Archives ]
              </Link>
              <Link href="/leaderboard" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest py-1">
                [ Leaderboard ]
              </Link>
              <Link href="/setup" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest py-1">
                [ New Trial ]
              </Link>
              <button
                onClick={handleLogout}
                className="text-left text-[#FF8A80] uppercase tracking-widest py-1 cursor-pointer"
              >
                [ Disconnect ]
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest py-1">
                [ Login ]
              </Link>
              <Link href="/register" className="text-[#B2DFDB] hover:text-white transition-colors uppercase tracking-widest py-1">
                [ Register ]
              </Link>
            </>
          )}
        </div>
      )}
    </header>
  );
}
