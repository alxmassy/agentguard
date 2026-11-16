import React from "react";
import { RiskLevel } from "@/lib/types";

export function RiskBadge({ level, score }: { level: RiskLevel; score?: number }) {
  const styles: Record<RiskLevel, { bg: string; text: string; border: string }> = {
    LOW: {
      bg: "bg-slate-500/10",
      text: "text-slate-300",
      border: "border-slate-500/30",
    },
    MEDIUM: {
      bg: "bg-yellow-500/10",
      text: "text-yellow-400",
      border: "border-yellow-500/30",
    },
    HIGH: {
      bg: "bg-orange-500/10",
      text: "text-orange-400",
      border: "border-orange-500/30",
    },
    CRITICAL: {
      bg: "bg-red-500/10",
      text: "text-red-400",
      border: "border-red-500/30",
    },
  };

  const style = styles[level] || styles.LOW;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${style.bg} ${style.text} border ${style.border}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current"></span>
      {level}
      {score !== undefined && <span className="opacity-75 font-mono">({score})</span>}
    </span>
  );
}
