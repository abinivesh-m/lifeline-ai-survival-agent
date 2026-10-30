"use client";

import { useRef, useState } from "react";
import { COLORS, lifeline } from "@/lib/lifeline";

/**
 * One spoken word is the whole approval, in the reader's own language. A reader
 * who cannot read a QR card can still say "சரி", "sí" or "ndiyo" - and this card
 * shows why the machine believed them, or why it refused.
 *
 * The decision is made in Python (seri_gate.py), not here: the per-language
 * token match, the model's intent and the confidence threshold must all agree.
 * This panel only replays the recorded evidence, including the ledger hash that
 * sealed each language.
 */
export default function SeriGate() {
  const seri = lifeline.seri;
  const entries = seri?.locales ?? [];
  const spoken = entries.filter((entry) => entry.audio?.src);
  const [code, setCode] = useState(
    () => spoken.find((entry) => entry.locale === "ta")?.locale ?? spoken[0]?.locale ?? "",
  );
  const [playing, setPlaying] = useState(false);
  const audio = useRef<HTMLAudioElement | null>(null);

  if (!seri?.available || spoken.length === 0) return null;

  const active = spoken.find((entry) => entry.locale === code) ?? spoken[0];
  const gate = active.gate;
  const model = active.model;
  const asr = active.asr;
  const approved = Boolean(gate?.approved);
  const accent = approved ? COLORS.teal : COLORS.blood;
  const summary = seri.summary;
  const textOnly = Object.keys(summary?.text_only ?? {});

  const toggle = () => {
    const node = audio.current;
    if (!node || !active.audio?.src) return;
    if (playing) {
      node.pause();
      setPlaying(false);
      return;
    }
    node.src = active.audio.src;
    void node.play().then(() => setPlaying(true)).catch(() => setPlaying(false));
  };

  const pick = (locale: string) => {
    audio.current?.pause();
    setPlaying(false);
    setCode(locale);
  };

  const checks = [
    {
      label: "SPOKEN WORD",
      value: gate?.token_intent === "APPROVE" ? "APPROVE" : (gate?.token_intent ?? "—"),
      title: `verbatim transcript: ${active.transcript ?? ""}`,
      ok: gate?.token_intent === "APPROVE",
    },
    {
      label: "INTENT MODEL",
      value: `${model?.intent ?? "—"} · ${((model?.confidence ?? 0) * 100).toFixed(0)}%`,
      title: model?.reason,
      ok: model?.intent === gate?.token_intent,
    },
    {
      label: "THRESHOLD",
      value: `>= ${((gate?.threshold ?? 0) * 100).toFixed(0)}% · code decides`,
      title: gate?.rule,
      ok: (model?.confidence ?? 0) >= (gate?.threshold ?? 1),
    },
  ];

  return (
    <div className="mt-3 grid gap-3 rounded-xl border border-line bg-panel/60 p-4 md:grid-cols-[1.15fr_0.85fr]">
      <div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">
            SERI GATE ·{" "}
            <span style={{ color: COLORS.teal }}>
              one word, {summary?.spoken ?? spoken.length} languages
            </span>
          </div>
          <span
            className="rounded border px-1.5 py-0.5 mono text-[8px] tracking-[0.12em]"
            style={{ borderColor: `${accent}66`, color: accent, background: `${accent}18` }}
          >
            {gate?.decision ?? "NO RUN"}
          </span>
        </div>

        <div className="mt-1 mono text-[8.5px] tracking-[0.1em] text-muted/70">
          {summary?.approved ?? 0} approved · {summary?.withheld ?? 0} withheld ·{" "}
          {summary?.spoken ?? spoken.length} spoken clips
          {textOnly.length > 0 ? ` · ${textOnly.join(", ")} text-only` : ""}
        </div>

        <div className="mt-2 flex flex-wrap gap-1.5">
          {spoken.map((entry) => {
            const selected = entry.locale === active.locale;
            const sealed = Boolean(entry.gate?.approved);
            return (
              <button
                key={entry.locale}
                onClick={() => pick(entry.locale)}
                aria-pressed={selected}
                title={`${entry.language} · ${entry.gate?.decision ?? "no run"}`}
                className={`rounded border px-2 py-1 mono text-[9px] tracking-[0.06em] transition ${
                  selected
                    ? "border-teal/60 bg-teal/15 text-teal"
                    : sealed
                      ? "border-line/70 bg-black/20 text-muted hover:border-muted/60"
                      : "border-blood/40 bg-blood/5 text-muted hover:border-blood/60"
                }`}
              >
                {entry.native}
                <span className="ml-1 text-[7.5px] opacity-70">
                  {sealed ? "✓" : "✗"}
                </span>
              </button>
            );
          })}
          {textOnly.map((locale) => {
            const native =
              lifeline.locales.find((entry) => entry.code === locale)?.native ?? locale;
            return (
              <span
                key={locale}
                title={summary?.text_only?.[locale] ?? "text only"}
                className="cursor-not-allowed rounded border border-line/40 bg-black/10 px-2 py-1 mono text-[9px] tracking-[0.06em] text-muted/40"
              >
                {native} · text
              </span>
            );
          })}
        </div>

        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={toggle}
            disabled={!active.audio?.src}
            className={`rounded border px-2.5 py-1.5 mono text-[9px] tracking-[0.1em] transition ${
              playing
                ? "border-amber/60 bg-amber/15 text-amber"
                : "border-teal/50 bg-teal/10 text-teal hover:bg-teal/20"
            } ${active.audio?.src ? "" : "cursor-not-allowed opacity-40"}`}
          >
            {playing ? "■ STOP" : `▶ HEAR · ${active.native}`}
          </button>
          <span className="mono text-[8.5px] text-muted">
            {asr?.model ?? "muse-voice-transcribe-1.0"} · {asr?.latency_s ?? "—"} s
          </span>
        </div>

        <div className="mono mt-2 text-[8px] tracking-[0.14em] text-muted/70">
          VERBATIM ASR · {active.audio?.seconds?.toFixed(2) ?? "—"} s CLIP
        </div>
        <p dir={active.locale === "ar" ? "rtl" : "ltr"} className="mt-0.5 text-[15px] leading-relaxed text-ink">
          “{active.transcript ?? "—"}”
        </p>

        <div className="mt-2 grid gap-1 sm:grid-cols-3">
          {checks.map((check) => (
            <div
              key={check.label}
              title={check.title}
              className="rounded border border-line/70 bg-black/25 px-2 py-1.5"
            >
              <div className="mono text-[8px] tracking-[0.12em] text-muted">{check.label}</div>
              <div
                className="mono mt-0.5 truncate text-[9px] leading-snug"
                style={{ color: check.ok ? COLORS.teal : COLORS.blood }}
              >
                {check.ok ? "✓" : "✗"} {check.value}
              </div>
            </div>
          ))}
        </div>

        <audio
          ref={audio}
          onEnded={() => setPlaying(false)}
          onError={() => setPlaying(false)}
          preload="none"
        />
      </div>

      <div className="rounded-lg border border-line/70 bg-black/30 p-3">
        <div className="mono text-[8.5px] tracking-[0.14em] text-muted">
          SEALED IN THE LEDGER · {active.locale}
        </div>
        {active.ledger ? (
          <>
            <div className="mono mt-1 text-[9px] leading-relaxed text-teal">
              seq {active.ledger.seq} · {active.ledger.action}
            </div>
            <div className="mono mt-1 break-all text-[8px] leading-relaxed text-muted">
              hash {active.ledger.hash?.slice(0, 32)}…
            </div>
            <div className="mono mt-1 break-all text-[8px] leading-relaxed text-muted/70">
              prev {active.ledger.prev?.slice(0, 32)}…
            </div>
          </>
        ) : (
          <p className="mt-1 text-[10px] leading-relaxed text-muted">
            Withheld, so nothing was sealed. {gate?.reasons?.[0] ?? ""}
          </p>
        )}
        <div className="mono mt-2 text-[8px] tracking-[0.12em] text-muted/60">AUDIO sha256</div>
        <div className="mono mt-0.5 break-all text-[8px] leading-relaxed text-muted/70">
          {active.audio?.sha256 ?? "—"}
        </div>
        <p className="mt-2 text-[9.5px] leading-relaxed text-muted/70">
          A misheard “no” must never dispatch fuel, so the model gets one vote and the
          word matcher gets another. Each language is sealed separately. Cost $
          {Number(seri.cost_usd ?? 0).toFixed(4)} for {summary?.languages ?? entries.length}{" "}
          runs. No gateway: nothing was dialled.
        </p>
      </div>
    </div>
  );
}
