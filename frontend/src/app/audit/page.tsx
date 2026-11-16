"use client";

import React, { useEffect, useState } from "react";
import { fetchActions, fetchAuditEvents } from "@/lib/api";
import { ActionRequest, AuditEvent } from "@/lib/types";
import { DecisionBadge } from "@/components/DecisionBadge";
import { RiskBadge } from "@/components/RiskBadge";
import { RiskFactorsBar } from "@/components/RiskFactorsBar";
import { Search, Filter, Terminal, Calendar, ChevronDown, ChevronUp, Clock, AlertCircle } from "lucide-react";

export default function AuditPage() {
  const [actions, setActions] = useState<ActionRequest[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [environment, setEnvironment] = useState<string>("all");
  const [decision, setDecision] = useState<string>("all");
  const [search, setSearch] = useState<string>("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [eventsMap, setEventsMap] = useState<{ [reqId: string]: AuditEvent[] }>({});

  const loadActions = async () => {
    try {
      setLoading(true);
      const res = await fetchActions(environment, decision, 100, 0);
      setActions(res.actions || []);
      setTotal(res.total || 0);
    } catch {
      // offline
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActions();
  }, [environment, decision]);

  const toggleExpand = async (reqId: string) => {
    if (expandedId === reqId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(reqId);
    if (!eventsMap[reqId]) {
      try {
        const events = await fetchAuditEvents(reqId);
        setEventsMap((prev) => ({ ...prev, [reqId]: events }));
      } catch {
        // ignore
      }
    }
  };

  const filtered = actions.filter((a) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      a.request_id.toLowerCase().includes(s) ||
      a.command?.raw.toLowerCase().includes(s) ||
      (a.policy_id && a.policy_id.toLowerCase().includes(s))
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Audit Trail & Execution Logs</h1>
        <p className="text-slate-400 text-xs sm:text-sm mt-1">
          Immutable event log of every command evaluated by AgentGuard, complete with risk factor breakdown and execution telemetry.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search request ID, command or policy..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Dropdowns */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {/* Environment */}
          <select
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500 cursor-pointer"
          >
            <option value="all">All Environments</option>
            <option value="production">Production</option>
            <option value="staging">Staging</option>
            <option value="development">Development</option>
            <option value="local">Local</option>
          </select>

          {/* Decision */}
          <select
            value={decision}
            onChange={(e) => setDecision(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500 cursor-pointer"
          >
            <option value="all">All Decisions</option>
            <option value="ALLOW">ALLOW</option>
            <option value="BLOCK">BLOCK</option>
            <option value="REQUIRE_HUMAN_APPROVAL">REQUIRE APPROVAL</option>
          </select>

          <span className="text-slate-500 font-mono text-[11px] ml-1">
            {filtered.length} of {total} records
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
              <tr>
                <th className="px-5 py-3">Timestamp</th>
                <th className="px-5 py-3">Request ID</th>
                <th className="px-5 py-3">Command</th>
                <th className="px-5 py-3">Environment</th>
                <th className="px-5 py-3">Decision</th>
                <th className="px-5 py-3">Risk</th>
                <th className="px-5 py-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {filtered.length > 0 ? (
                filtered.map((action) => {
                  const isExpanded = expandedId === action.request_id;
                  const events = eventsMap[action.request_id] || [];

                  return (
                    <React.Fragment key={action.request_id}>
                      <tr
                        onClick={() => toggleExpand(action.request_id)}
                        className="hover:bg-slate-800/30 cursor-pointer transition-colors"
                      >
                        <td className="px-5 py-3 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                          {new Date(action.created_at).toLocaleTimeString()}
                        </td>
                        <td className="px-5 py-3 font-mono font-bold text-indigo-400 whitespace-nowrap">
                          {action.request_id}
                        </td>
                        <td className="px-5 py-3 font-mono text-slate-200 max-w-sm truncate">
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
                        <td className="px-5 py-3 text-right text-slate-400">
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4 inline-block" />
                          ) : (
                            <ChevronDown className="w-4 h-4 inline-block" />
                          )}
                        </td>
                      </tr>

                      {/* Expandable Lifecycle Detail Row */}
                      {isExpanded && (
                        <tr className="bg-slate-950/80">
                          <td colSpan={7} className="p-6 border-b border-slate-800 space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                              {/* Left: Command & Context */}
                              <div className="space-y-3">
                                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                                  Command & Execution Context
                                </h4>
                                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs text-cyan-300">
                                  {action.command?.raw}
                                </div>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                                    <span className="text-slate-500 block text-[11px]">Tool / Op</span>
                                    <span className="text-slate-200 font-mono font-medium">
                                      {action.parsed_action.tool} → {action.parsed_action.operation}
                                    </span>
                                  </div>
                                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800">
                                    <span className="text-slate-500 block text-[11px]">Action Type</span>
                                    <span className="text-slate-200 font-mono font-medium">
                                      {action.parsed_action.action_type}
                                    </span>
                                  </div>
                                </div>
                                {action.original_task && (
                                  <div className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs text-slate-300">
                                    <span className="text-slate-500 font-bold block text-[10px] uppercase">
                                      Original Task / Prompt Intent
                                    </span>
                                    {action.original_task}
                                  </div>
                                )}
                              </div>

                              {/* Right: Policy & Risk */}
                              <div className="space-y-3">
                                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                                  Policy Evaluation & 5-Factor Risk Weights
                                </h4>
                                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs">
                                  <div className="flex items-center justify-between mb-1.5">
                                    <span className="text-slate-400 font-medium">Enforced Policy:</span>
                                    <span className="font-mono text-indigo-400 font-bold">
                                      {action.policy_id || "default"}
                                    </span>
                                  </div>
                                  <div className="text-slate-300">
                                    Decision Reason: {action.policy_id ? "Evaluated against deterministic rules." : "Default fail-closed policy applied."}
                                  </div>
                                </div>
                                <div>
                                  <RiskFactorsBar factors={action.risk_factors} />
                                </div>
                              </div>
                            </div>

                            {/* Lifecycle Timeline */}
                            <div className="pt-2 border-t border-slate-850">
                              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">
                                Lifecycle Audit Trail
                              </h4>
                              {events.length > 0 ? (
                                <div className="flex flex-wrap items-center gap-3">
                                  {events.map((ev, idx) => (
                                    <div
                                      key={ev.id || idx}
                                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs"
                                    >
                                      <Clock className="w-3.5 h-3.5 text-cyan-400" />
                                      <span className="font-mono font-bold text-slate-200">
                                        {ev.event_type}
                                      </span>
                                      <span className="text-[10px] text-slate-500 font-mono">
                                        {new Date(ev.occurred_at).toLocaleTimeString()}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <div className="text-xs text-slate-500 font-mono">
                                  Event recorded: request_created → decision_made ({action.decision})
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                    No matching actions found.
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
