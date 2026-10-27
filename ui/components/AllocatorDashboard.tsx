"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { COLORS, lifeline } from "@/lib/lifeline";
import { useLocale } from "./LocaleProvider";

const frames = lifeline.sam.frames;

function useTypewriter(text: string, speed = 18) {
  const [shown, setShown] = useState("");
  useEffect(() => {
    setShown("");
    if (!text) return;
    let i = 0;
    const id = setInterval(() => {
      i += 3;
      setShown(text.slice(0, i));
      if (i >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [text, speed]);
  return shown;
}

async function sha256(text: string) {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export default function AllocatorDashboard() {
  const { t } = useLocale();
  const [decision, setDecision] = useState<null | "approve" | "deny">(null);
  const [chain, setChain] = useState<{ seq: number; action: string; hash: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const head = chain.length ? chain[chain.length - 1].hash : "0".repeat(64);

  // One frame, one number. The featured mask is the 35.3% Kerala frame; the
  // other eight stay in the artefact, not on the page.
  const frame =
    frames.find((item) => item.file === "Flood_kerala_2018_3.jpg") ?? frames[0];

  // The qualifying brain and the offline fallback, side by side. Both are
  // re-validated by the same code; this switch changes the proposal, not the rules.
  const brain = lifeline.allocation.brain;
  const hasBrain = Boolean(brain?.source?.startsWith("openweight"));
  const [brainView, setBrainView] = useState<"openweight" | "policy">(
    hasBrain ? "openweight" : "policy",
  );
  const policyJustification = lifeline.allocation.justification;
  const typedOpenweight = useTypewriter(brain?.justification ?? policyJustification);
  const typedPolicy = useTypewriter(policyJustification);

  const allocation =
    brainView === "openweight" && brain?.allocation
      ? brain.allocation
      : lifeline.allocation.policy;
  const hospital = allocation.hospital ?? 0;
  const pump = allocation.water_pump ?? 0;
  const total = hospital + pump;

  const spend = lifeline.credit.spent_usd;
  const budget = lifeline.credit.budget_usd;
  const percent = lifeline.credit.percent;

  const decide = useCallback(
    async (action: "approve" | "deny") => {
      if (busy) return;
      setBusy(true);
      const seq = chain.length + 1;
      const payload = {
        seq,
        ts: new Date().toISOString(),
        tier: decision ? 1 : 7,
        action,
        prev: head,
        allocation: action === "approve" ? { hospital, water_pump: pump } : {},
      };
      const hash = await sha256(JSON.stringify(payload));
      setChain((c) => [...c, { seq, action, hash }]);
      setDecision(action);
      setBusy(false);
    },
    [busy, chain.length, decision, head, hospital, pump],
  );

  const modelRows = useMemo(
    () =>
      Object.entries(lifeline.credit.by_model)
        .filter(([, bucket]) => bucket.calls > 0)
        .sort((a, b) => b[1].spent_usd - a[1].spent_usd),
    [],
  );

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      {/* ---------------- SAM evidence ---------------- */}
      <div className="glass rounded-xl p-4">
        <div className="flex items-baseline justify-between">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">01 · PERCEIVE</div>
          <div className="mono text-[9px] text-teal">{lifeline.sam.model}</div>
        </div>

        <div className="relative mt-2 overflow-hidden rounded-lg border border-line bg-black">
          <img
            key={frame?.stem}
            src={frame?.overlay ?? frame?.photo ?? ""}
            alt={`SAM mask over ${frame?.file}`}
            className="h-[190px] w-full object-cover"
            draggable={false}
          />
          <div className="absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-black/90 to-transparent p-2.5">
            <div>
              <div className="mono text-[9px] text-muted">water extent</div>
              <div className="text-2xl font-bold text-teal">{frame?.severity.toFixed(1)}%</div>
            </div>
            <div className="mono text-right text-[9px] text-muted">
              {frame?.objects} mask{frame?.objects === 1 ? "" : "s"}
              <br />
              {frame?.file}
            </div>
          </div>
          <div className="absolute left-2 top-2 rounded border border-teal/40 bg-black/70 px-1.5 py-0.5 mono text-[8px] text-teal">
            FEATURED FRAME · ONE MASK
          </div>
        </div>

        <div className="mono mt-1.5 text-[8.5px] text-muted/70">
          stored · artifacts/photos/{frame?.file}
        </div>

        <p className="mt-2 text-[10.5px] leading-relaxed text-muted">
          Noun-phrase prompt <span className="mono text-ink">&quot;{lifeline.sam.prompt}&quot;</span>,
          mask decoded from the model response. One frame, one measured number:{" "}
          <span className="text-teal">{frame?.severity.toFixed(1)}% water extent from{" "}
          {frame?.objects} mask</span>. The other eight frames and the two sub-1% aerial
          misses stay in the artefact rather than propping up this panel.
        </p>
      </div>

      {/* ---------------- Voice + Wonder ---------------- */}
      <div className="glass rounded-xl p-4">
        <div className="flex items-baseline justify-between">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">02 · LISTEN</div>
          <div className="mono text-[9px] text-teal">{lifeline.voice.model}</div>
        </div>

        <div className="mt-2 flex h-12 items-end gap-[3px]">
          {Array.from({ length: 48 }).map((_, i) => (
            <motion.span
              key={i}
              className="flex-1 rounded-sm bg-lung/70"
              initial={{ height: 4 }}
              animate={{ height: 6 + Math.abs(Math.sin(i * 0.7)) * 38 }}
              transition={{
                duration: 0.9 + (i % 5) * 0.12,
                repeat: Infinity,
                repeatType: "reverse",
                ease: "easeInOut",
              }}
            />
          ))}
        </div>

        <div className="mt-2 rounded-lg border border-line bg-black/40 p-2.5">
          <div className="flex items-center justify-between">
            <span className="mono text-[9px] text-teal">TA · {lifeline.voice.seconds}s · push to talk</span>
            {lifeline.voice.synthetic && (
              <span className="rounded border border-amber/50 bg-amber/10 px-1.5 py-0.5 mono text-[8px] text-amber">
                SYNTHETIC PLACEHOLDER · LABELLED
              </span>
            )}
          </div>
          <p className="ta mt-1.5 text-[12.5px] leading-relaxed text-ink">{lifeline.voice.transcript}</p>
          <p className="mono mt-1.5 text-[9px] leading-relaxed text-muted">
            real pipeline · {lifeline.voice.model} · Tamil bias + keywords · stored run
            artifacts/audio/report_01.wav
          </p>
        </div>

        <div className="mt-3 flex items-baseline justify-between gap-2">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">05 · ALLOCATE</div>
          <div className="flex gap-1">
            <button
              onClick={() => setBrainView("openweight")}
              disabled={!hasBrain}
              aria-pressed={brainView === "openweight"}
              className={`rounded border px-1.5 py-0.5 mono text-[8px] tracking-[0.1em] transition ${
                brainView === "openweight"
                  ? "border-teal/60 bg-teal/10 text-teal"
                  : "border-line/70 bg-black/20 text-muted hover:border-muted/50"
              } ${hasBrain ? "" : "opacity-40"}`}
            >
              OPEN WEIGHT
            </button>
            <button
              onClick={() => setBrainView("policy")}
              aria-pressed={brainView === "policy"}
              className={`rounded border px-1.5 py-0.5 mono text-[8px] tracking-[0.1em] transition ${
                brainView === "policy"
                  ? "border-amber/60 bg-amber/10 text-amber"
                  : "border-line/70 bg-black/20 text-muted hover:border-muted/50"
              }`}
            >
              OFFLINE POLICY
            </button>
          </div>
        </div>
        <div className="mt-1.5 rounded-lg border border-line bg-[#08141a] p-2.5">
          <div className="flex items-baseline justify-between gap-2">
            <div className="mono text-[9px] text-muted">
              {brainView === "openweight" && brain
                ? `${brain.provider ?? "Baseten"} · ${brain.model ?? "meta-models/muse-spark-open-1026"}`
                : "deterministic policy · no network"}
            </div>
            {brainView === "openweight" && brain && (
              <span className="mono shrink-0 text-[8px] text-teal">
                {brain.status === "live" ? "LIVE CALL" : "STORED RUN"} · {brain.latency_s}s
              </span>
            )}
          </div>
          <p className="mono mt-1 text-[8px] leading-relaxed text-muted/60">
            {brainView === "openweight" && brain
              ? `${brain.valid ? "re-validated locally ✓" : "validator rejected ✗"} · run ${brain.at?.slice(0, 19).replace("T", " ") ?? "?"} UTC · proof ${lifeline.openweight.latencies_s.map((value) => `${value.toFixed(2)} s`).join(" / ")} stored`
              : "policy · same validator · $0 spent on model calls"}
          </p>
          <p className="mt-1 min-h-[54px] text-[11.5px] leading-relaxed text-teal/90">
            {brainView === "openweight" ? typedOpenweight : typedPolicy}
            <span className="ml-0.5 inline-block h-3 w-1 animate-pulse bg-teal align-middle" />
          </p>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {lifeline.allocation.evidence.slice(0, 5).map((item) => (
              <span
                key={item.id}
                title={item.claim}
                className="rounded border border-line px-1.5 py-0.5 mono text-[8.5px] text-muted"
              >
                {item.id}
              </span>
            ))}
            <span className="rounded border border-teal/40 px-1.5 py-0.5 mono text-[8.5px] text-teal">
              validator · {lifeline.allocation.validation?.ok ? "pass" : "fail"} 70L/30L ·{" "}
              {Math.round(lifeline.allocation.confidence * 100)}% conf
            </span>
          </div>
          <p className="mt-1.5 mono text-[8px] leading-relaxed text-muted/70">
            {brainView === "openweight"
              ? "The model proposes; the validator re-checks every hard constraint in code. Nothing is trusted from the model."
              : "LIFELINE_OFFLINE=1 fallback: same validator, no model call, no API key."}
          </p>
        </div>
      </div>

      {/* ---------------- Allocation + gate + ledger ---------------- */}
      <div className="glass flex flex-col rounded-xl p-4">
        <div className="flex items-baseline justify-between">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">{t("alloc.title")}</div>
          <span className="mono text-[9px] text-muted">{t("alloc.note")}</span>
        </div>

        {[
          { key: "hospital", label: t("alloc.hospital"), litres: hospital, cap: 70, color: COLORS.blood },
          { key: "water_pump", label: t("alloc.pump"), litres: pump, cap: 30, color: COLORS.lung },
        ].map((row) => (
          <div key={row.key} className="mt-3">
            <div className="flex items-baseline justify-between">
              <span className="text-[12px] text-ink">{row.label}</span>
              <span className="mono text-[13px] font-semibold" style={{ color: row.color }}>
                {row.litres} L
              </span>
            </div>
            <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-[#16262f]">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${(row.litres / total) * 100}%` }}
                transition={{ duration: 1.1, ease: [0.2, 0.8, 0.2, 1], delay: 0.2 }}
                className="h-full rounded-full"
                style={{ background: `linear-gradient(90deg, ${row.color}aa, ${row.color})` }}
              />
            </div>
          </div>
        ))}

        <div className="mt-2 flex items-baseline justify-between border-t border-line/60 pt-2">
          <span className="mono text-[10px] text-muted">{t("alloc.total", { litres: total })}</span>
          <span className="mono text-[10px] text-teal">{lifeline.allocation.confidence * 100}% conf</span>
        </div>

        <div className="mt-3">
          <div className="flex items-baseline justify-between">
            <span className="mono text-[10px] tracking-[0.16em] text-muted">{t("credit.title")}</span>
            <span className="mono text-[10px] text-ink">
              ${spend.toFixed(4)} <span className="text-muted">/ ${budget.toFixed(0)}</span>
            </span>
          </div>
          <div className="relative mt-1.5 h-2 overflow-hidden rounded-full bg-[#16262f]">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${Math.max(percent, 1.2)}%` }}
              transition={{ duration: 1.2 }}
              className="h-full rounded-full bg-teal"
            />
            <span className="absolute left-[80%] top-0 h-full w-px bg-amber/70" />
            <span className="absolute left-[95%] top-0 h-full w-px bg-blood/80" />
          </div>
          <div className="mt-1 flex justify-between mono text-[8.5px] text-muted">
            <span>alerts 80% / 95%</span>
            <span>
              ${lifeline.credit.remaining_usd.toFixed(2)} left of ${budget.toFixed(0)}
            </span>
          </div>
          <div className="mt-1.5 space-y-0.5">
            {modelRows.map(([model, bucket]) => (
              <div key={model} className="flex justify-between mono text-[9px] text-muted">
                <span>{model}</span>
                <span>
                  {bucket.calls} calls · ${bucket.spent_usd.toFixed(6)}
                </span>
              </div>
            ))}
            <div className="mt-1 flex justify-between border-t border-line/60 pt-1 mono text-[9px] text-ink">
              <span>
                {modelRows.reduce((sum, [, bucket]) => sum + bucket.calls, 0)} priced calls ·{" "}
                {lifeline.credit.ledger_rows} ledger rows
              </span>
              <span>${spend.toFixed(4)} total</span>
            </div>
          </div>
        </div>

        <div className="mt-auto pt-3">
          <div className="rounded-lg border border-teal/25 bg-teal/5 p-2.5">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal opacity-70" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-teal" />
              </span>
              <span className="text-[11px] font-semibold text-teal">{t("gate.title")}</span>
            </div>

            {!decision && (
              <div className="mt-2 flex gap-2">
                <button
                  onClick={() => decide("approve")}
                  disabled={busy}
                  className="flex-1 rounded-md border border-teal bg-teal/15 px-3 py-2 text-[12px] font-bold text-teal transition hover:bg-teal/25 disabled:opacity-50"
                >
                  {t("gate.approve")}
                </button>
                <button
                  onClick={() => decide("deny")}
                  disabled={busy}
                  className="flex-1 rounded-md border border-line px-3 py-2 text-[12px] font-bold text-muted transition hover:border-blood hover:text-blood disabled:opacity-50"
                >
                  {t("gate.deny")}
                </button>
              </div>
            )}

            <AnimatePresence>
              {decision && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mt-2 overflow-hidden"
                >
                  <div
                    className={`rounded border p-2 ${
                      decision === "approve"
                        ? "border-teal/50 bg-teal/10 text-teal"
                        : "border-blood/50 bg-blood/10 text-blood"
                    }`}
                  >
                    <div className="mono text-[9px] tracking-[0.14em]">
                      {decision === "approve" ? "DISPATCH RELEASED" : "HALTED · NOTHING DISPATCHED"}
                    </div>
                    <p className="mt-0.5 text-[10.5px] leading-relaxed text-ink/80">
                      {decision === "approve"
                        ? `${hospital} L hospital, ${pump} L pump. Plan released to the operator; this page drives no vehicle.`
                        : "The agent stops. The reserve stays where it is."}
                    </p>
                    <div className="mt-1.5 border-t border-white/10 pt-1.5 mono text-[8.5px] leading-relaxed text-muted">
                      <div>sha256 chain · height {chain.length}</div>
                      <div className="truncate">head {head.slice(0, 32)}…</div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
