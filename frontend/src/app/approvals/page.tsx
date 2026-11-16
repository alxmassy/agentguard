"use client";

import React, { useEffect, useState } from "react";
import { fetchApprovals, approveRequest, rejectRequest } from "@/lib/api";
import { Approval } from "@/lib/types";
import { RiskBadge } from "@/components/RiskBadge";
import { RiskFactorsBar } from "@/components/RiskFactorsBar";
import { Check, X, Clock, AlertTriangle, CheckCircle2, ShieldX, Terminal, FileText, ChevronDown, ChevronUp } from "lucide-react";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"pending" | "resolved" | "all">("pending");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [commentInput, setCommentInput] = useState<{ [id: string]: string }>({});
  const [processingId, setProcessingId] = useState<string | null>(null);

  const loadApprovals = async () => {
    try {
      const data = await fetchApprovals();
      setApprovals(data);
    } catch {
      // offline
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadApprovals();
    const interval = setInterval(loadApprovals, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleApprove = async (id: string) => {
    setProcessingId(id);
    const comment = commentInput[id] || "Approved via Dashboard";
    try {
      await approveRequest(id, comment);
      await loadApprovals();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (id: string) => {
    setProcessingId(id);
    const reason = commentInput[id] || "Rejected by human reviewer";
    try {
      await rejectRequest(id, reason);
      await loadApprovals();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setProcessingId(null);
    }
  };

  const filtered = approvals.filter((a) => {
    if (filter === "pending") return a.status === "pending";
    if (filter === "resolved") return a.status !== "pending";
    return true;
  });

  const pendingCount = approvals.filter((a) => a.status === "pending").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-white tracking-tight">Human Approval Queue</h1>
            {pendingCount > 0 && (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                {pendingCount} Pending
              </span>
            )}
          </div>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Real-time human-in-the-loop decision plane. When agents attempt high-impact commands, they halt until resolved here.
          </p>
        </div>

        {/* Filter buttons */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800 text-xs">
          <button
            onClick={() => setFilter("pending")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              filter === "pending"
                ? "bg-slate-800 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Pending ({pendingCount})
          </button>
          <button
            onClick={() => setFilter("resolved")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              filter === "resolved"
                ? "bg-slate-800 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            Resolved
          </button>
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              filter === "all"
                ? "bg-slate-800 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            All History
          </button>
        </div>
      </div>

      {/* Approvals List */}
      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-slate-800/80 text-emerald-400 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-white">
            {filter === "pending" ? "No Pending Approvals 🎉" : "No Records Found"}
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            {filter === "pending"
              ? "All actions evaluated by AgentGuard are either resolved or authorized automatically by deterministic policy."
              : "Try running 'agentguard terraform apply' in the terminal to trigger an approval request live."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map((appr) => {
            const act = appr.action_requests;
            const isExpanded = expandedId === appr.id;
            const isPending = appr.status === "pending";
            const isProcessing = processingId === appr.id;

            return (
              <div
                key={appr.id}
                className={`rounded-2xl border transition-all ${
                  isPending
                    ? "border-amber-500/30 bg-slate-900/80 shadow-lg shadow-amber-500/5"
                    : "border-slate-800 bg-slate-900/50"
                }`}
              >
                {/* Main Card Header */}
                <div className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {appr.request_id}
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {act?.environment || "production"}
                      </span>
                      {act && <RiskBadge level={act.risk_level} score={act.risk_score} />}
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                          appr.status === "pending"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                            : appr.status === "approved"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                        }`}
                      >
                        {appr.status.toUpperCase()}
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono ml-auto">
                        {new Date(appr.created_at).toLocaleTimeString()}
                      </span>
                    </div>

                    <div className="font-mono text-sm bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 text-cyan-300 flex items-center justify-between">
                      <span className="truncate">{act?.command?.raw || "Command"}</span>
                    </div>

                    {act?.original_task && (
                      <div className="text-xs text-slate-400 flex items-start gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-slate-500 mt-0.5 shrink-0" />
                        <span>
                          <strong className="text-slate-300">Stated Task:</strong> {act.original_task}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Actions (if Pending) */}
                  {isPending && (
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 shrink-0">
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          placeholder="Optional comment..."
                          value={commentInput[appr.id] || ""}
                          onChange={(e) =>
                            setCommentInput({ ...commentInput, [appr.id]: e.target.value })
                          }
                          className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 w-full sm:w-48"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleApprove(appr.id)}
                          disabled={isProcessing}
                          className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20 active:scale-95 transition-all disabled:opacity-50"
                        >
                          <Check className="w-4 h-4" />
                          <span>Approve</span>
                        </button>
                        <button
                          onClick={() => handleReject(appr.id)}
                          disabled={isProcessing}
                          className="px-4 py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 font-semibold text-xs flex items-center justify-center gap-1.5 transition-all active:scale-95 disabled:opacity-50"
                        >
                          <X className="w-4 h-4" />
                          <span>Reject</span>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Comment if resolved */}
                  {!isPending && appr.comment && (
                    <div className="text-xs text-slate-400 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 max-w-xs">
                      <span className="text-slate-500 font-semibold">Note:</span> {appr.comment}
                    </div>
                  )}
                </div>

                {/* Details toggle */}
                <div className="px-5 py-2 bg-slate-950/40 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400">
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : appr.id)}
                    className="flex items-center gap-1 hover:text-slate-200 transition-colors"
                  >
                    <span>{isExpanded ? "Hide Risk & Evaluation Details" : "Show Risk & Evaluation Details"}</span>
                    {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  </button>

                  <span className="font-mono text-[11px] text-slate-500">
                    Policy Rule: {act?.policy_id || "prod-apply-approval"}
                  </span>
                </div>

                {/* Expanded Details Drawer */}
                {isExpanded && act && (
                  <div className="p-5 bg-slate-950/60 border-t border-slate-800 space-y-4 text-xs">
                    <div>
                      <div className="text-slate-400 font-semibold mb-2">5-Factor Risk Weight Breakdown</div>
                      <RiskFactorsBar factors={act.risk_factors} />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-slate-300">
                      <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-slate-500 text-[11px]">Parsed Tool & Operation</div>
                        <div className="font-mono mt-1 font-semibold text-cyan-400">
                          {act.parsed_action.tool} → {act.parsed_action.operation}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-slate-500 text-[11px]">Action Classification</div>
                        <div className="font-mono mt-1 text-slate-200">
                          {act.parsed_action.action_type}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                        <div className="text-slate-500 text-[11px]">Project & Agent</div>
                        <div className="font-mono mt-1 text-slate-200">
                          {act.project_id} ({act.agent_id || "agent"})
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
