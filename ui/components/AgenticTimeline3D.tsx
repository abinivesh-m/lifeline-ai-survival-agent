"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { lifeline, STEPS } from "@/lib/lifeline";

const DETAIL: Record<number, string[]> = {
  1: [
    `${lifeline.sam.frames.length} flood photographs sent to SAM 3.1`,
    `prompt: "${lifeline.sam.prompt}" — a bare noun phrase, no instructions`,
    `masks decoded and measured: ${lifeline.sam.worst}% worst frame`,
  ],
  2: [
    "Tamil voice note, 24 kHz mono",
    `transcript: ${lifeline.voice.transcript?.slice(0, 64)}…`,
    "language bias Tamil + English, domain keywords in the request",
  ],
  3: [
    "Kahn topological sort over town.json",
    `order: ${lifeline.graph.order.join(" → ")}`,
    `if the heart fails, ${lifeline.graph.cascade.people_affected} people lose water`,
  ],
  4: [
    "A* with heapq over the road graph",
    `4.2 km corridor blocked at km 42`,
    `${lifeline.route.distance_km} km found, ${lifeline.route.saving.percent}% fuel saved`,
  ],
  5: [
    `policy: ${JSON.stringify(lifeline.allocation.policy)} = ${lifeline.allocation.total} L`,
    "validator re-checks every hard constraint in code",
    `source: ${lifeline.allocation.source}`,
  ],
  6: [
    `spent $${lifeline.credit.spent_usd.toFixed(6)} of a $${lifeline.credit.budget_usd} ceiling`,
    "alerts at 80% and 95%, sub-cent calls kept at 6 dp",
    `remaining $${lifeline.credit.remaining_usd.toFixed(2)}, reserve $${lifeline.credit.reserve_usd}`,
  ],
  7: [
    "nothing is dispatched until a person decides",
    "approve, deny, or the four-tier escalation takes over",
    "every transition appended to a sha256 hash chain",
  ],
  8: [
    "reserve cut from 100 L to 80 L",
    "same solver, new constraint, heart still protected",
    "pump runtime drops — and the agent says so out loud",
  ],
};

export default function AgenticTimeline3D() {
  const [active, setActive] = useState(1);
  const [playing, setPlaying] = useState(true);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => setActive((n) => (n % 8) + 1), 2600);
    return () => clearInterval(id);
  }, [playing]);

  const step = STEPS[active - 1];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPlaying((v) => !v)}
            className="rounded-md border border-line px-3 py-1.5 mono text-[10px] text-muted transition hover:border-teal/60 hover:text-teal"
          >
            {playing ? "PAUSE" : "AUTOPLAY"}
          </button>
          <span className="mono text-[10px] text-muted">
            step {active} / 8 · click any card
          </span>
        </div>
        <div className="flex items-center gap-3 rounded-md border border-line bg-panel/70 px-3 py-1.5">
          <span className="mono text-[9px] text-muted">baseline</span>
          <div className="flex items-center gap-2">
            <span className="mono text-[11px] text-blood line-through decoration-1">
              {lifeline.baseline.manual_minutes} min
            </span>
            <span className="text-muted">→</span>
            <span className="mono text-[13px] font-bold text-teal">
              {lifeline.baseline.agent_minutes} min
            </span>
          </div>
        </div>
      </div>

      <div className="relative">
        <div className="pointer-events-none absolute left-0 right-0 top-1/2 h-px bg-gradient-to-r from-transparent via-line to-transparent" />
        <div className="grid grid-cols-4 gap-2 lg:grid-cols-8">
          {STEPS.map((item) => {
            const on = item.n === active;
            const done = item.n < active;
            return (
              <button
                key={item.n}
                onClick={() => {
                  setActive(item.n);
                  setPlaying(false);
                }}
                className="group relative text-left"
                style={{ perspective: 900 }}
              >
                <motion.div
                  animate={{
                    rotateY: on ? 0 : 12,
                    rotateX: on ? 0 : 8,
                    y: on ? -6 : 0,
                    opacity: on ? 1 : done ? 0.75 : 0.55,
                  }}
                  transition={{ type: "spring", stiffness: 210, damping: 22 }}
                  className={`rounded-lg border p-2.5 ${
                    on
                      ? "border-teal/70 bg-teal/10 glow-teal"
                      : "border-line bg-panel/70 group-hover:border-muted/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className={`mono text-[10px] ${on ? "text-teal" : "text-muted"}`}>
                      {String(item.n).padStart(2, "0")}
                    </span>
                    {done && <span className="text-[9px] text-teal/70">✓</span>}
                  </div>
                  <div className={`mt-1 text-[10.5px] font-bold tracking-wide ${on ? "text-ink" : "text-ink/70"}`}>
                    {item.key}
                  </div>
                  <div className="mono mt-0.5 text-[8.5px] leading-tight text-muted">{item.tool}</div>
                </motion.div>
              </button>
            );
          })}
        </div>
      </div>

      <motion.div
        key={active}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="grid gap-3 rounded-xl border border-line bg-panel/70 p-4 lg:grid-cols-[1fr_1.1fr]"
      >
        <div>
          <div className="mono text-[9px] tracking-[0.2em] text-teal">
            STEP {String(step.n).padStart(2, "0")} · {step.tool.toUpperCase()}
          </div>
          <h3 className="mt-1 text-xl font-semibold">{step.key}</h3>
          <p className="mt-1 text-[12px] text-muted">{step.detail}</p>
        </div>
        <ul className="space-y-1.5">
          {DETAIL[active].map((line) => (
            <li key={line} className="flex gap-2 text-[11.5px] leading-relaxed text-ink/80">
              <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-teal" />
              <span className={line.match(/[\u0B80-\u0BFF]/) ? "ta" : ""}>{line}</span>
            </li>
          ))}
        </ul>
      </motion.div>

      <p className="text-[10px] leading-relaxed text-muted/80">{lifeline.baseline.note}</p>
    </div>
  );
}
