"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { COLORS } from "@/lib/lifeline";

const TRIGGER_L = 10;

/**
 * The temple bell is the one channel that needs no phone, no battery and no
 * signal. This is a reserve simulator, not live telemetry: dragging below the
 * 10 L trigger shows the three-strike tier-4 call, and the label says so.
 */
export default function TempleBell() {
  const [reserve, setReserve] = useState(34);
  const [sound, setSound] = useState(true);
  const contextRef = useRef<AudioContext | null>(null);

  const ringing = reserve < TRIGGER_L;
  const pct = Math.max(0, Math.min(100, reserve));

  useEffect(() => {
    if (!ringing || !sound) return;

    const AudioCtx =
      typeof window !== "undefined"
        ? window.AudioContext ??
          (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
        : undefined;
    if (!AudioCtx) return;

    const context = contextRef.current ?? new AudioCtx();
    contextRef.current = context;
    if (context.state === "suspended") void context.resume();

    /** Three partials, exponential decay: a struck bell, synthesised offline. */
    const strike = () => {
      const now = context.currentTime;
      [
        { frequency: 740, gain: 0.16 },
        { frequency: 1180, gain: 0.07 },
        { frequency: 2230, gain: 0.03 },
      ].forEach(({ frequency, gain }) => {
        const osc = context.createOscillator();
        const amp = context.createGain();
        osc.type = "sine";
        osc.frequency.value = frequency;
        amp.gain.setValueAtTime(0.0001, now);
        amp.gain.linearRampToValueAtTime(gain, now + 0.008);
        amp.gain.exponentialRampToValueAtTime(0.0001, now + 1.9);
        osc.connect(amp).connect(context.destination);
        osc.start(now);
        osc.stop(now + 2);
      });
    };

    strike();
    const timers = [setTimeout(strike, 900), setTimeout(strike, 1800)];
    return () => timers.forEach(clearTimeout);
  }, [ringing, sound]);

  useEffect(() => {
    return () => {
      void contextRef.current?.close();
      contextRef.current = null;
    };
  }, []);

  const accent = ringing ? COLORS.blood : COLORS.amber;

  return (
    <div className="mt-3 grid gap-3 rounded-xl border border-line bg-panel/60 p-4 md:grid-cols-[1.25fr_0.75fr]">
      <div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">
            RESERVE SIMULATOR · TEMPLE BELL
          </div>
          <button
            onClick={() => setSound((value) => !value)}
            aria-pressed={sound}
            className={`rounded border px-2 py-0.5 mono text-[8.5px] tracking-[0.12em] transition ${
              sound
                ? "border-teal/50 bg-teal/10 text-teal"
                : "border-line/70 bg-black/20 text-muted hover:border-muted/50"
            }`}
          >
            {sound ? "SOUND ON" : "SOUND OFF"}
          </button>
        </div>

        <div className="mt-2.5 flex items-baseline gap-2">
          <span className="text-3xl font-bold tabular-nums" style={{ color: accent }}>
            {pct} L
          </span>
          <span className="mono text-[9px] text-muted">diesel reserve · trigger &lt; {TRIGGER_L} L</span>
        </div>

        <div className="relative mt-2 h-2 overflow-hidden rounded-full bg-black/50">
          <div
            className="h-full rounded-full transition-[width] duration-200"
            style={{ width: `${pct}%`, background: accent }}
          />
          <div
            className="absolute inset-y-0 w-px bg-ink/60"
            style={{ left: `${TRIGGER_L}%` }}
            aria-hidden="true"
          />
        </div>

        <input
          type="range"
          min={0}
          max={100}
          step={1}
          value={pct}
          onChange={(event) => setReserve(Number(event.target.value))}
          aria-label="diesel reserve in litres"
          className="mt-2.5 w-full accent-[#2dd4bf]"
        />

        <div className="mt-1.5 flex flex-wrap gap-1.5">
          <button
            onClick={() => setReserve(8)}
            className="rounded border border-blood/60 bg-blood/10 px-2 py-1 mono text-[9px] tracking-[0.1em] text-blood transition hover:bg-blood/20"
          >
            DRAIN TO 8 L
          </button>
          <button
            onClick={() => setReserve(100)}
            className="rounded border border-line/70 bg-black/20 px-2 py-1 mono text-[9px] tracking-[0.1em] text-muted transition hover:border-muted/50"
          >
            REFILL 100 L
          </button>
        </div>

        <p className="mt-2 text-[10px] leading-relaxed text-muted/80" aria-live="polite">
          {ringing
            ? "Three strikes: tier 4 is live. Three shelter leaders, two of three agree; the decision is written by hand and hashed at the desk."
            : "Bell idle. Two strikes mean tier 3; three mean tier 4. No phone, no battery, no signal."}
        </p>
      </div>

      <div className="flex flex-col items-center justify-center rounded-lg border border-line/70 bg-black/30 p-3">
        <motion.svg
          viewBox="0 0 120 120"
          className="h-[104px] w-[104px]"
          aria-hidden="true"
          animate={ringing ? { rotate: [0, -16, 12, -8, 6, 0] } : { rotate: 0 }}
          transition={ringing ? { duration: 1.1, repeat: Infinity, ease: "easeInOut" } : { duration: 0.3 }}
          style={{ transformOrigin: "60px 8px" }}
        >
          <path d="M58 6h4v10h-4z" fill={accent} opacity="0.7" />
          <path
            d="M60 16c-15 0-24 11-24 26 0 12-4 20-10 27h68c-6-7-10-15-10-27 0-15-9-26-24-26z"
            fill={ringing ? "rgba(255,99,99,0.16)" : "rgba(251,191,36,0.14)"}
            stroke={accent}
            strokeWidth="2.2"
          />
          <path d="M23 74h74" stroke={accent} strokeWidth="3" strokeLinecap="round" />
          <circle cx="60" cy="84" r="6" fill={accent} />
          <path d="M60 90v8" stroke={accent} strokeWidth="2" strokeLinecap="round" />
        </motion.svg>

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={ringing ? "ringing" : "idle"}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            className="mt-1 mono text-center text-[8.5px] tracking-[0.14em]"
            style={{ color: accent }}
          >
            {ringing ? "STRIKING · 3 OF 3" : "IDLE · 0 STRIKES"}
          </motion.div>
        </AnimatePresence>
        <div className="mt-1 mono text-center text-[8px] leading-relaxed text-muted/70">
          one speaker · 0 phone needed · local alert only
        </div>
      </div>
    </div>
  );
}
