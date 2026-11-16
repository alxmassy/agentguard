import React from "react";
import { Decision } from "@/lib/types";
import { CheckCircle2, ShieldAlert, AlertTriangle } from "lucide-react";

export function DecisionBadge({ decision }: { decision: Decision }) {
  if (decision === "ALLOW") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
        ALLOW
      </span>
    );
  }
  if (decision === "BLOCK") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
        <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
        BLOCK
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
      <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
      REQUIRE APPROVAL
    </span>
  );
}
