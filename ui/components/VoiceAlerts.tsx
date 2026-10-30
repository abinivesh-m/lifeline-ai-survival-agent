"use client";

import { useMemo, useRef, useState } from "react";
import { COLORS, lifeline } from "@/lib/lifeline";

type Clip = "tier2" | "allocation";

/**
 * The ladder so far was text in eight languages, which assumes the reader can
 * read. This plays the same validated payloads aloud, from committed WAV
 * files, so a reader with a feature phone and no literacy still gets the alert.
 *
 * What is real here: the words were drafted by muse-spark-1.3 and passed the
 * code check plus a muse-wonder-1.0 review; the audio is MMS-TTS, an
 * open-weight model run on this laptop. What is not: any delivery. No call is
 * placed - the line below says so on screen, every time.
 */
export default function VoiceAlerts() {
  const multi = lifeline.multilingual;
  const locales = useMemo(
    () => (multi?.available ? multi.locales.filter((entry) => entry.valid) : []),
    [multi],
  );

  const [code, setCode] = useState(locales[0]?.code ?? "ta");
  const [clip, setClip] = useState<Clip | null>(null);
  const [chain, setChain] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const active = locales.find((entry) => entry.code === code) ?? locales[0];

  if (!multi?.available || locales.length === 0) {
    return null;
  }

  const play = (localeCode: string, which: Clip, chainMode = false) => {
    const url = locales.find((entry) => entry.code === localeCode)?.audio?.[which]?.src;
    const audio = audioRef.current;
    if (!url || !audio) return;
    audio.pause();
    audio.src = url;
    setChain(chainMode);
    setCode(localeCode);
    setClip(which);
    void audio.play().catch(() => {
      setClip(null);
      setChain(false);
    });
  };

  const stop = () => {
    audioRef.current?.pause();
    setClip(null);
    setChain(false);
  };

  const onEnded = () => {
    if (!chain || clip !== "tier2") {
      stop();
      return;
    }
    const index = locales.findIndex((entry) => entry.code === code);
    const next = locales.slice(index + 1).find((entry) => entry.audio?.tier2);
    if (next) {
      play(next.code, "tier2", true);
    } else {
      stop();
    }
  };

  const totals = multi.totals;
  const speech = multi.speech;
  const spokenCount = locales.filter((entry) => entry.audio?.tier2).length;

  return (
    <div className="mt-3 rounded-xl border border-line bg-panel/60 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="mono text-[10px] tracking-[0.18em] text-muted">
          SPOKEN ALERT ·{" "}
          <span style={{ color: COLORS.teal }}>
            {totals?.valid}/{totals?.locales} locales validated
          </span>{" "}
          · <span className="text-muted/70">{spokenCount} spoken</span>
        </div>
        <button
          onClick={() => (clip ? stop() : play(locales[0].code, "tier2", true))}
          className="rounded border border-teal/50 bg-teal/10 px-2 py-1 mono text-[8.5px] tracking-[0.12em] text-teal transition hover:bg-teal/20"
        >
          {clip ? "STOP" : "PLAY ALL ALERTS"}
        </button>
      </div>

      <div className="mt-2 flex flex-wrap gap-1.5">
        {locales.map((entry) => {
          const selected = entry.code === active?.code;
          const hasClip = Boolean(entry.audio?.tier2);
          return (
            <button
              key={entry.code}
              onClick={() => play(entry.code, "tier2")}
              disabled={!hasClip}
              aria-pressed={selected}
              className={`rounded border px-2 py-1 mono text-[9px] tracking-[0.08em] transition ${
                selected
                  ? "border-teal/60 bg-teal/15 text-teal"
                  : hasClip
                    ? "border-line/70 bg-black/20 text-muted hover:border-muted/60"
                    : "cursor-not-allowed border-line/40 bg-black/10 text-muted/40"
              }`}
              title={hasClip ? `Play the ${entry.language} alert` : "no clip on file"}
            >
              {entry.native}
            </button>
          );
        })}
      </div>

      {active && (
        <div className="mt-3 grid gap-2 md:grid-cols-[1.1fr_0.9fr]">
          <div dir={active.code === "ar" ? "rtl" : "ltr"}>
            <div className="mono text-[8.5px] tracking-[0.14em] text-muted">
              SMS · {active.code}
            </div>
            <p className="mt-1 text-[11.5px] leading-relaxed text-ink/90">{active.sms}</p>
            <div className="mono mt-2 text-[8.5px] tracking-[0.14em] text-muted">
              SPOKEN DECISION · {active.code}
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">{active.allocation}</p>
          </div>

          <div className="flex flex-col gap-1.5">
            <button
              onClick={() => play(active.code, "tier2")}
              className={`flex items-center justify-between rounded border px-2.5 py-2 text-left transition ${
                clip === "tier2"
                  ? "border-teal/60 bg-teal/15"
                  : "border-line/70 bg-black/20 hover:border-muted/60"
              }`}
            >
              <span className="mono text-[9px] tracking-[0.1em] text-ink">
                ▶ ALERT · {active.native}
              </span>
              <span className="mono text-[8px] text-muted">
                {active.audio?.tier2 ? `${active.audio.tier2.seconds.toFixed(1)} s` : "no clip"}
              </span>
            </button>
            <button
              onClick={() => play(active.code, "allocation")}
              disabled={!active.audio?.allocation}
              className={`flex items-center justify-between rounded border px-2.5 py-2 text-left transition ${
                clip === "allocation"
                  ? "border-amber/60 bg-amber/15"
                  : "border-line/70 bg-black/20 hover:border-muted/60"
              } ${active.audio?.allocation ? "" : "cursor-not-allowed opacity-50"}`}
            >
              <span className="mono text-[9px] tracking-[0.1em] text-ink">
                ▶ 70 / 30 DECISION
              </span>
              <span className="mono text-[8px] text-muted">
                {active.audio?.allocation
                  ? `${active.audio.allocation.seconds.toFixed(1)} s`
                  : "no clip"}
              </span>
            </button>
            <div className="mono mt-1 text-[8px] leading-relaxed text-muted/70">
              {speech?.engine ?? "MMS-TTS"} · {speech?.device ?? "cpu"} · $
              {(speech?.cost_usd ?? 0).toFixed(2)} · synthetic, not a human recording
            </div>
          </div>
        </div>
      )}

      <audio ref={audioRef} onEnded={onEnded} onError={() => setClip(null)} preload="none" />

      <p className="mt-2 text-[9.5px] leading-relaxed text-muted/70">
        Drafted by {multi.generator?.model} · reviewed by {multi.reviewer?.model} ·{" "}
        {speech?.clips ?? 0} clips / {Number(speech?.seconds ?? 0).toFixed(1)} s rendered locally.
        No gateway is configured: nothing was dialled, and every payload is still
        PENDING_CREDENTIALS.
      </p>
    </div>
  );
}
