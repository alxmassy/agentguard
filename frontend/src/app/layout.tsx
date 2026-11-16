import type { Metadata } from "next";
import { Navbar } from "@/components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentGuard — AI Agent Runtime Safety & Governance",
  description: "Pre-execution deterministic safety, human approvals, and audit trail for autonomous AI agents.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#090d16] text-slate-100 antialiased flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
        <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute -top-40 -left-40 w-96 h-96 bg-indigo-600/10 rounded-full blur-[128px]"></div>
          <div className="absolute top-1/3 -right-40 w-96 h-96 bg-cyan-600/10 rounded-full blur-[128px]"></div>
          <div className="absolute -bottom-40 left-1/3 w-96 h-96 bg-violet-600/10 rounded-full blur-[128px]"></div>
        </div>

        <Navbar />

        <main className="flex-1 relative z-10 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        <footer className="relative z-10 border-t border-slate-900/80 py-6 text-center text-xs text-slate-500">
          AgentGuard Runtime Safety Gateway • Deterministic Policy Enforcement • Human-In-The-Loop Governance
        </footer>
      </body>
    </html>
  );
}
