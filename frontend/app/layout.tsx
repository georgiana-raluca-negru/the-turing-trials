import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Header from "@/components/Header"; // Importăm Header-ul proaspăt creat
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "The Turing Trials",
  description: "AI-powered courtroom simulator",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full flex flex-col bg-black text-slate-100 selection:bg-cyan-500/30 selection:text-cyan-200">
        
        {/* Folosim componenta noastră dinamică de tip Client */}
        <Header />

        {/* Conținutul paginilor */}
        <main className="flex-grow flex flex-col bg-slate-950">
          {children}
        </main>

        <div id="toast-container" className="font-mono text-xs"></div>
      </body>
    </html>
  );
}