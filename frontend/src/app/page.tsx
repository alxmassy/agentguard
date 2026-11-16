"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchStats, fetchApprovals, approveRequest, rejectRequest, seedDemoData } from "@/lib/api";
import { DashboardStats, Approval } from "@/lib/types";
import { DecisionBadge } from "@/components/DecisionBadge";
import { RiskBadge } from "@/components/RiskBadge";
import { 
  ShieldCheck, 
  ShieldAlert, 
  AlertTriangle, 
  Terminal, 
  ArrowRight, 
  Clock, 
  Check, 
  X,
  Sparkles,
  RefreshCw,
  Cpu,
  Layers
} from "lucide-react";

export default function OverviewPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [s, a] = await Promise.all([
        fetchStats().catch(() => null),
        fetchApprovals("pending").catch(() => []),
      ]);
      if (s) setStats(s);
      setPendingApprovals(a);
    } catch {
      // offline
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (id: string) => {
    setActionInProgress(id);
    try {
      await approveRequest(id, "Approved from Quick Action");
      await loadData();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setActionInProgress(null);
    }
  };

  const handleReject = async (id: string) => {
    setActionInProgress(id);
    try {
      await rejectRequest(id, "Rejected from Quick Action");
      await loadData();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setActionInProgress(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Hero / Presentation Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-b from-slate-900/90 to-slate-950/80 border border-slate-800/80 p-6 sm:p-8 shadow-xl">
        <div className="relative z-10 max-w-3xl space-y-3">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-xs font-semibold text-cyan-400">
            <Cpu className="w-3.5 h-3.5" />
            <span>AI Agent Pre-Execution Gateway</span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-white">
            Runtime Safety & Governance for Autonomous Agents
          </h1>
          <p className="text-slate-400 text-sm sm:text-base leading-relaxed">
            AgentGuard sits directly between AI coding/infrastructure agents (Claude Code, Cursor, Codex)
            and the consequential terminal actions they execute. Deterministic rules decide safety before the command ever runs.
          </p>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Evaluated */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Evaluated</div>
            <div className="text-3xl font-extrabold text-white mt-1">
              {stats?.total_evaluations ?? 0}
            </div>
            <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
              <Layers className="w-3 h-3" />
              <span>Full lifecycle audit</span>
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-slate-800/80 flex items-center justify-center text-slate-300">
            <Terminal className="w-6 h-6" />
          </div>
        </div>

        {/* Allowed */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-emerald-500/20 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-emerald-400 uppercase tracking-wider">Allowed</div>
            <div className="text-3xl font-extrabold text-emerald-400 mt-1">
              {stats?.allowed_count ?? 0}
            </div>
            <div className="text-[11px] text-emerald-500/80 mt-1">
              Safe & authorized actions
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
          </div>
        </div>

        {/* Blocked */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-rose-500/20 flex items-center justify-between">
          <div>
            <div className="text-xs font-medium text-rose-400 uppercase tracking-wider">Blocked</div>
            <div className="text-3xl font-extrabold text-rose-400 mt-1">
              {stats?.blocked_count ?? 0}
            </div>
            <div className="text-[11px] text-rose-500/80 mt-1">
              Deterministic policy veto
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
        </div>

        {/* Pending Approvals */}
        <Link
          href="/approvals"
          className="p-5 rounded-xl bg-slate-900/60 border border-amber-500/30 hover:border-amber-500/50 flex items-center justify-between transition-all group"
        >
          <div>
            <div className="text-xs font-medium text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <span>Human Approvals</span>
              {pendingApprovals.length > 0 && (
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
              )}
            </div>
            <div className="text-3xl font-extrabold text-amber-400 mt-1">
              {pendingApprovals.length}
            </div>
            <div className="text-[11px] text-amber-400/80 mt-1 group-hover:underline flex items-center gap-1">
              <span>View queue</span>
              <ArrowRight className="w-3 h-3" />
            </div>
          </div>
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 group-hover:scale-105 transition-transform">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </Link>
      </div>

      {/* Pending Human Approvals Section (Live Waiting Spinner Demo) */}
      {pendingApprovals.length > 0 && (
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-400 font-bold text-lg">
              <Clock className="w-5 h-5 animate-spin" />
              <span>Active Human Approvals Required ({pendingApprovals.length})</span>
            </div>
            <span className="text-xs text-amber-300 bg-amber-500/20 px-2 py-0.5 rounded font-mono">
              CLI Gateway is waiting for response
            </span>
          </div>

          <div className="space-y-3">
            {pendingApprovals.map((appr) => {
              const act = appr.action_requests;
              return (
                <div
                  key={appr.id}
                  className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-lg"
                >
                  <div className="space-y-1.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-indigo-400 font-semibold">
                        {appr.request_id}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {act?.environment}
                      </span>
                      {act && <RiskBadge level={act.risk_level} score={act.risk_score} />}
                    </div>
                    <div className="font-mono text-sm bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-cyan-300">
                      {act?.command?.raw || "Command"}
                    </div>
                    {act?.original_task && (
                      <div className="text-xs text-slate-400">
                        <span className="text-slate-500">Stated Task:</span> {act.original_task}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleApprove(appr.id)}
                      disabled={actionInProgress === appr.id}
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all active:scale-95 disabled:opacity-50"
                    >
                      <Check className="w-4 h-4" />
                      <span>Approve</span>
                    </button>
                    <button
                      onClick={() => handleReject(appr.id)}
                      disabled={actionInProgress === appr.id}
                      className="px-4 py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 font-semibold text-xs flex items-center gap-1.5 transition-all active:scale-95 disabled:opacity-50"
                    >
                      <X className="w-4 h-4" />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* College Presentation Quick Guide & CLI Scenarios */}
      <div className="rounded-2xl bg-slate-900/40 border border-slate-800 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-white font-bold">
            <Terminal className="w-5 h-5 text-indigo-400" />
            <span>Interactive Demo Scenarios (Run via Terminal)</span>
          </div>
          <span className="text-xs text-slate-400">Try these commands in your shell</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs font-mono">
          {/* Scenario 1: ALLOW */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-emerald-500/30 space-y-2">
            <div className="flex items-center justify-between font-sans">
              <span className="font-bold text-emerald-400">1. Safe Read Operation</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 text-[10px] font-bold">
                ALLOW
              </span>
            </div>
            <div className="p-2.5 rounded bg-slate-900 text-slate-200 select-all border border-slate-800">
              agentguard terraform plan
            </div>
            <p className="text-[11px] font-sans text-slate-400">
              Evaluates non-destructive infrastructure reads in staging. Authorizes and runs directly.
            </p>
          </div>

          {/* Scenario 2: BLOCK */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-rose-500/30 space-y-2">
            <div className="flex items-center justify-between font-sans">
              <span className="font-bold text-rose-400">2. Destructive Veto</span>
              <span className="px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 text-[10px] font-bold">
                BLOCK
              </span>
            </div>
            <div className="p-2.5 rounded bg-slate-900 text-slate-200 select-all border border-slate-800">
              agentguard terraform destroy
            </div>
            <p className="text-[11px] font-sans text-slate-400">
              Destructive actions on production infrastructure are unconditionally blocked before reaching the system.
            </p>
          </div>

          {/* Scenario 3: REQUIRE APPROVAL */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-amber-500/30 space-y-2">
            <div className="flex items-center justify-between font-sans">
              <span className="font-bold text-amber-400">3. High Impact</span>
              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 text-[10px] font-bold">
                APPROVAL
              </span>
            </div>
            <div className="p-2.5 rounded bg-slate-900 text-slate-200 select-all border border-slate-800">
              agentguard terraform apply
            </div>
            <p className="text-[11px] font-sans text-slate-400">
              CLI pauses and shows spinner. Click &quot;Approve&quot; in this dashboard to let the command continue!
            </p>
          </div>
        </div>
      </div>

      {/* Recent Evaluations Table */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden shadow-lg">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-white">Recent Evaluated Commands</h2>
            <p className="text-xs text-slate-400 mt-0.5">Live feed of requests evaluated by AgentGuard</p>
          </div>
          <Link
            href="/audit"
            className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
          >
            <span>Full Audit Trail</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
              <tr>
                <th className="px-5 py-3">Request ID</th>
                <th className="px-5 py-3">Command</th>
                <th className="px-5 py-3">Environment</th>
                <th className="px-5 py-3">Decision</th>
                <th className="px-5 py-3">Risk Level</th>
                <th className="px-5 py-3">Policy ID</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {stats?.recent_actions && stats.recent_actions.length > 0 ? (
                stats.recent_actions.map((action) => (
                  <tr key={action.request_id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-5 py-3 font-mono font-semibold text-indigo-400">
                      {action.request_id}
                    </td>
                    <td className="px-5 py-3 font-mono text-slate-200 max-w-xs truncate">
                      {action.command?.raw}
                    </td>
                    <td className="px-5 py-3">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                        {action.environment}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <DecisionBadge decision={action.decision} />
                    </td>
                    <td className="px-5 py-3">
                      <RiskBadge level={action.risk_level} score={action.risk_score} />
                    </td>
                    <td className="px-5 py-3 font-mono text-slate-400">
                      {action.policy_id || "—"}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-500">
                    No evaluations recorded yet. Run a command with the CLI or click &quot;Seed Demo Scenarios&quot; above!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
