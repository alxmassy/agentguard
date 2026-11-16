import React from "react";
import { RiskFactors } from "@/lib/types";

export function RiskFactorsBar({ factors }: { factors: RiskFactors }) {
  const items = [
    { label: "Action", val: factors.action_weight, max: 6 },
    { label: "Environment", val: factors.environment_weight, max: 4 },
    { label: "Blast Radius", val: factors.blast_radius_weight, max: 5 },
    { label: "Reversibility", val: factors.reversibility_weight, max: 5 },
    { label: "Privilege", val: factors.privilege_weight, max: 3 },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
      {items.map((item) => {
        const pct = Math.min(100, Math.round((item.val / item.max) * 100));
        return (
          <div key={item.label} className="bg-slate-900/60 p-2 rounded-lg border border-slate-800">
            <div className="flex justify-between text-slate-400 mb-1">
              <span>{item.label}</span>
              <span className="font-mono text-slate-200">+{item.val}</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  item.val >= 4 ? "bg-red-500" : item.val >= 2 ? "bg-amber-500" : "bg-emerald-500"
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
