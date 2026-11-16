"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Shield, CheckSquare, ListFilter, BookOpen, RefreshCw, Sparkles } from "lucide-react";
import { checkHealth, fetchApprovals, seedDemoData } from "@/lib/api";

export function Navbar() {
  const pathname = usePathname();
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [backendStatus, setBackendStatus] = useState<"checking" | "online" | "offline">("checking");
  const [storageMode, setStorageMode] = useState<string>("sqlite");
  const [seeding, setSeeding] = useState(false);

  const loadStatus = async () => {
    try {
      const health = await checkHealth();
      setBackendStatus(health.status === "healthy" ? "online" : "offline");
      setStorageMode(health.storage_mode || "sqlite");
    } catch {
      setBackendStatus("offline");
    }

    try {
      const pending = await fetchApprovals("pending");
      setPendingCount(pending.length);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      await seedDemoData();
      await loadStatus();
      window.location.reload();
    } catch (e) {
      alert("Failed to seed demo data. Is backend running?");
    } finally {
      setSeeding(false);
    }
  };

  const navLinks = [
    { href: "/", label: "Overview", icon: Shield },
    {
      href: "/approvals",
      label: "Approvals",
      icon: CheckSquare,
      badge: pendingCount > 0 ? pendingCount : null,
    },
    { href: "/audit", label: "Audit Trail", icon: ListFilter },
    { href: "/policies", label: "Policies", icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                  AgentGuard
                </span>
                <span className="text-[10px] ml-1.5 px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono uppercase tracking-wider border border-indigo-500/30">
                  Runtime Safety
                </span>
              </div>
            </Link>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? "bg-slate-800/90 text-cyan-400 shadow-sm border border-slate-700/60"
                      : "text-slate-400 hover:text-slate-100 hover:bg-slate-900/60"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                  {item.badge !== null && (
                    <span className="ml-1 px-1.5 py-0.5 text-xs font-bold rounded-full bg-amber-500 text-slate-950 animate-pulse">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Status & Actions */}
          <div className="flex items-center gap-3">
            {/* System Health Status */}
            <div className="flex items-center gap-2 text-xs px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800">
              <span
                className={`w-2 h-2 rounded-full ${
                  backendStatus === "online"
                    ? "bg-emerald-400 shadow-sm shadow-emerald-400/50"
                    : backendStatus === "checking"
                    ? "bg-amber-400 animate-pulse"
                    : "bg-red-400 shadow-sm shadow-red-400/50"
                }`}
              />
              <span className="text-slate-300">
                {backendStatus === "online"
                  ? `Live (${storageMode})`
                  : backendStatus === "checking"
                  ? "Checking..."
                  : "API Offline"}
              </span>
            </div>

            {/* Quick Demo Seed */}
            <button
              onClick={handleSeed}
              disabled={seeding}
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-md shadow-indigo-600/20 active:scale-95 transition-all disabled:opacity-50"
              title="Populate sample CLI executions for college demonstration"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{seeding ? "Seeding..." : "Seed Demo Scenarios"}</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
