"use client";

import React, { useEffect, useState } from "react";
import { fetchPolicies } from "@/lib/api";
import { PolicyRule } from "@/lib/types";
import { DecisionBadge } from "@/components/DecisionBadge";
import { Shield, BookOpen, Layers, CheckCircle2 } from "lucide-react";

export default function PoliciesPage() {
  const [rules, setRules] = useState<PolicyRule[]>([]);
  const [defaultDecision, setDefaultDecision] = useState<string>("REQUIRE_HUMAN_APPROVAL");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPolicies()
      .then((data) => {
        setRules(data.rules || []);
        setDefaultDecision(data.default || "REQUIRE_HUMAN_APPROVAL");
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white tracking-tight">Active Governance Policies</h1>
        <p className="text-slate-400 text-xs sm:text-sm mt-1">
          Deterministic safety rules evaluated in strict precedence order. The LLM is advisory only and cannot override these rules.
        </p>
      </div>

      {/* Precedence Banner */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-indigo-400" />
          <span className="font-semibold text-slate-200">Rule Precedence Order:</span>
        </div>
        <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
          <span className="px-2.5 py-1 rounded bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30">
            1. BLOCK (Absolute)
          </span>
          <span className="text-slate-600">→</span>
          <span className="px-2.5 py-1 rounded bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">
            2. REQUIRE_APPROVAL
          </span>
          <span className="text-slate-600">→</span>
          <span className="px-2.5 py-1 rounded bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/30">
            3. ALLOW
          </span>
          <span className="text-slate-600">→</span>
          <span className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 font-bold">
            4. Default ({defaultDecision})
          </span>
        </div>
      </div>

      {/* Policies Table */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider text-[10px] border-b border-slate-800">
              <tr>
                <th className="px-5 py-3.5">Rule ID</th>
                <th className="px-5 py-3.5">Target Condition</th>
                <th className="px-5 py-3.5">Decision</th>
                <th className="px-5 py-3.5">Enforcement Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {rules.map((rule) => {
                const cond = rule.conditions || {};
                return (
                  <tr key={rule.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-5 py-3.5 font-mono font-bold text-indigo-400 whitespace-nowrap">
                      {rule.id}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex flex-wrap gap-1.5 font-mono text-[11px]">
                        {cond.environment && (
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700/50">
                            env:{cond.environment}
                          </span>
                        )}
                        {cond.action_type && (
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 border border-slate-700/50">
                            action:{cond.action_type}
                          </span>
                        )}
                        {cond.is_read_only !== undefined && (
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-300 border border-slate-700/50">
                            read_only:{String(cond.is_read_only)}
                          </span>
                        )}
                        {cond.is_destructive !== undefined && (
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-rose-300 border border-slate-700/50">
                            destructive:{String(cond.is_destructive)}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <DecisionBadge decision={rule.then} />
                    </td>
                    <td className="px-5 py-3.5 text-slate-300">
                      {rule.reason || "Evaluated by policy precedence."}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
