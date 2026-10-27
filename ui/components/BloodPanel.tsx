"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { COLORS, lifeline } from "@/lib/lifeline";

const B = lifeline.blood;

function hoursLabel(hours: number) {
  const total = Math.round(hours * 60);
  return `${Math.floor(total / 60)} h ${String(total % 60).padStart(2, "0")} m`;
}

function Card({
  index,
  title,
  verdict,
  colour,
  children,
  footer,
}: {
  index: string;
  title: string;
  verdict: string;
  colour: string;
  children: React.ReactNode;
  footer: string;
}) {
  return (
    <div className="relative flex flex-col overflow-hidden rounded-xl border border-line bg-panel/70 p-4">
      <div
        className="absolute inset-x-0 top-0 h-[2px]"
        style={{ background: `linear-gradient(90deg, transparent, ${colour}, transparent)` }}
      />
      <div className="flex items-baseline justify-between">
        <div className="mono text-[10px] tracking-[0.18em]" style={{ color: colour }}>
          {index}
        </div>
        <div className="mono text-[8.5px] uppercase tracking-[0.14em] text-muted">
          {verdict}
        </div>
      </div>
      <div className="mt-1 text-[13px] font-semibold text-ink">{title}</div>
      <div className="mt-2 flex-1">{children}</div>
      <p className="mt-3 border-t border-line/60 pt-2 text-[10px] leading-relaxed text-muted/85">
        {footer}
      </p>
    </div>
  );
}

export default function BloodPanel() {
  const [temp, setTemp] = useState(B.sweat.temp_c);
  const [load, setLoad] = useState(1.0);
  const [shortfall, setShortfall] = useState(false);

  // same formula as blood.py - the coefficient and reference come from the
  // Python export, so the two cannot drift apart on constants.
  const sweat = useMemo(() => {
    const factor = 1 + B.sweat.beta_per_c * (temp - B.sweat.reference_c);
    const atReference = B.sweat.litres_measured / factor;
    return {
      atReference,
      deficit: B.sweat.litres_measured - atReference,
      percent: (1 - atReference / B.sweat.litres_measured) * 100,
      mass: atReference * B.sweat.density_kg_per_l,
    };
  }, [temp]);

  const baseBurn = B.clock.burn_l_per_hour / B.clock.load_factor;
  const burn = baseBurn * load;
  const clockHours = B.clock.litres / burn;
  const loaded = clockHours < B.inverse.heart.hours - 0.01;

  const missingLot = shortfall ? 7 : null;
  const scanned = shortfall
    ? B.dna.total_litres - B.dna.lot_litres
    : B.dna.total_litres;

  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {/* ------------------------------------------------------------ sweat */}
        <Card
          index="01 · SWEAT"
          title="100 L is not 100 L at 42 °C"
          verdict="volume correction"
          colour={COLORS.amber}
          footer={B.sweat.note}
        >
          <div className="flex items-end gap-2">
            <motion.span
              key={sweat.atReference.toFixed(2)}
              initial={{ opacity: 0.4 }}
              animate={{ opacity: 1 }}
              className="text-[34px] font-bold leading-none text-amber"
            >
              {sweat.atReference.toFixed(2)}
            </motion.span>
            <span className="pb-1 text-[11px] text-muted">L usable at 15 °C</span>
          </div>
          <div className="mono mt-1 text-[10px] text-muted">
            {B.sweat.litres_measured.toFixed(0)} L measured at {temp.toFixed(0)} °C ·{" "}
            {sweat.mass.toFixed(2)} kg
          </div>

          <input
            aria-label="diesel temperature input"
            type="range"
            min={20}
            max={45}
            step={1}
            value={temp}
            onChange={(event) => setTemp(Number(event.target.value))}
            className="mt-3 w-full accent-amber"
          />

          <div className="mt-2 flex flex-wrap gap-1.5">
            <span className="rounded border border-blood/40 bg-blood/10 px-1.5 py-0.5 mono text-[9px] text-blood">
              −{sweat.deficit.toFixed(2)} L
            </span>
            <span className="rounded border border-line px-1.5 py-0.5 mono text-[9px] text-muted">
              {sweat.percent.toFixed(2)}%
            </span>
            <span className="rounded border border-line px-1.5 py-0.5 mono text-[9px] text-muted">
              range {B.sweat.deficit_range_litres[0]}–{B.sweat.deficit_range_litres[1]} L
            </span>
            <span className="rounded border border-amber/40 bg-amber/5 px-1.5 py-0.5 mono text-[9px] text-amber">
              diesel {B.sweat.beta_per_c}/°C
            </span>
          </div>
          <p className="mt-2 text-[10px] leading-relaxed text-muted">
            The number going around is{" "}
            <span className="text-blood">−{B.sweat.folklore_litres.toFixed(0)} L</span>. The
            diesel expansion coefficient, {B.sweat.beta_per_c}/°C, says{" "}
            {B.sweat.deficit_litres.toFixed(2)} L. We publish the physics, not the folklore.
          </p>
        </Card>

        {/* -------------------------------------------------------------- dna */}
        <Card
          index="02 · FUEL DNA"
          title={`${B.dna.lot_count} lots, each with a hash`}
          verdict="append-only"
          colour={COLORS.teal}
          footer={B.dna.note}
        >
          <div className="flex items-baseline gap-2">
            <span className="text-[34px] font-bold leading-none text-teal">
              {B.dna.lot_count}
            </span>
            <span className="pb-1 text-[11px] text-muted">
              lots of {B.dna.lot_litres} L · {B.dna.total_mass_kg} kg total
            </span>
          </div>
          <div className="mono mt-2 flex gap-3 text-[10px] text-muted">
            <span className="text-blood">{B.dna.split.hospital} · heart</span>
            <span className="text-lung">{B.dna.split.water_pump} · lungs</span>
          </div>
          <div className="mt-2 rounded border border-line/70 bg-black/35 px-2 py-1.5 mono text-[8.5px] text-muted">
            <div className="truncate">head {B.dna.head.slice(0, 40)}…</div>
            <div className="mt-0.5 text-teal">
              verify: {B.dna_verify.ok ? "chain intact" : "BROKEN"}
            </div>
          </div>
          <button
            onClick={() => setShortfall((v) => !v)}
            className={`mt-2 w-full rounded-md border px-2 py-1.5 mono text-[9.5px] tracking-[0.1em] transition ${
              shortfall
                ? "border-teal/60 bg-teal/10 text-teal"
                : "border-line text-muted hover:border-muted/60"
            }`}
          >
            {shortfall ? "RESET SCAN" : "SCAN 90 L INSTEAD OF 100"}
          </button>
        </Card>

        {/* ------------------------------------------------------------ clock */}
        <Card
          index="03 · DEATH CLOCK"
          title="When the heart stops"
          verdict="fuel-limited runtime"
          colour={COLORS.blood}
          footer={B.clock.note}
        >
          <div className="flex items-end gap-2">
            <motion.span
              key={clockHours.toFixed(3)}
              initial={{ opacity: 0.5 }}
              animate={{ opacity: 1 }}
              className="text-[34px] font-bold leading-none"
              style={{ color: loaded ? COLORS.blood : COLORS.ink }}
            >
              {hoursLabel(clockHours)}
            </motion.span>
          </div>
          <div className="mono mt-1 text-[10px] text-muted">
            {B.clock.litres} L ÷ {burn.toFixed(1)} L/h
          </div>

          <div className="mt-3 flex items-center justify-between">
            <span className="mono text-[9px] text-muted">generator load</span>
            <span className="mono text-[10px] text-ink">{load.toFixed(2)}×</span>
          </div>
          <input
            aria-label="generator load input"
            type="range"
            min={0.8}
            max={1.4}
            step={0.05}
            value={load}
            onChange={(event) => setLoad(Number(event.target.value))}
            className="mt-1 w-full accent-[#f87171]"
          />
          <div className="mt-1 flex justify-between mono text-[8.5px] text-muted">
            <span>0.8× quiet</span>
            <span>1.4× ICU peak</span>
          </div>
          <p className="mt-2 text-[10px] leading-relaxed text-muted">
            {loaded
              ? `At ${load.toFixed(2)}× the same 70 L ends ${hoursLabel(
                  B.inverse.heart.hours - clockHours,
                )} earlier.`
              : "At nameplate load the 70 L plan buys exactly four hours."}{" "}
            Mechanical failure is not modelled.
          </p>
        </Card>

        {/* ---------------------------------------------------------- inverse */}
        <Card
          index="04 · INVERSE UPTIME GUARANTEE"
          title="Allocate hours, not litres"
          verdict="same plan, human units"
          colour={COLORS.lung}
          footer={B.inverse.note}
        >
          <div className="space-y-2">
            {[
              {
                label: "heart",
                value: B.inverse.heart.label,
                sub: `${B.inverse.heart.litres} L hospital`,
                colour: COLORS.blood,
              },
              {
                label: "lungs",
                value: B.inverse.lungs.label,
                sub: `${B.inverse.lungs.litres} L pump`,
                colour: COLORS.lung,
              },
              {
                label: "organs",
                value: `${B.inverse.water.days_at_documented_demand.toFixed(1)} days`,
                sub: `${B.inverse.water.litres_delivered.toLocaleString("en-US")} L water · ${B.inverse.water.people} people`,
                colour: COLORS.amber,
              },
            ].map((row) => (
              <div key={row.label} className="flex items-baseline justify-between gap-2">
                <div>
                  <div className="mono text-[8.5px] tracking-[0.14em]" style={{ color: row.colour }}>
                    {row.label.toUpperCase()}
                  </div>
                  <div className="mono text-[8.5px] text-muted">{row.sub}</div>
                </div>
                <div className="text-[19px] font-bold" style={{ color: row.colour }}>
                  {row.value}
                </div>
              </div>
            ))}
          </div>
          <div className="mt-2 rounded border border-blood/30 bg-blood/5 px-2 py-1.5 mono text-[9px] text-blood">
            50 / 50 split = {B.inverse.naive_split.heart_label} of heart
          </div>
        </Card>
      </div>

      {/* ------------------------------------------------------------ ledger */}
      <div className="rounded-xl border border-line bg-panel/60 p-4">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">
            DISPATCH LEDGER · {B.dna.algorithm}
          </div>
          <div className="mono text-[10px]">
            <span className="text-muted">scanned </span>
            <span className={shortfall ? "text-blood" : "text-teal"}>{scanned} L</span>
            <span className="text-muted"> of {B.dna.total_litres} L</span>
          </div>
        </div>

        <div className="mt-2.5 grid grid-cols-5 gap-1.5 sm:grid-cols-10">
          {B.dna_lots.map((lot) => {
            const gone = missingLot === lot.seq;
            return (
              <motion.div
                key={lot.seq}
                initial={false}
                animate={{
                  opacity: gone ? 0.35 : 1,
                  scale: gone ? 0.96 : 1,
                }}
                className={`rounded border px-1.5 py-1 ${
                  gone
                    ? "border-blood/70 bg-blood/10"
                    : lot.destination === "hospital"
                      ? "border-blood/30 bg-blood/5"
                      : "border-lung/30 bg-lung/5"
                }`}
              >
                <div className="mono text-[8px] text-muted">lot {String(lot.seq).padStart(2, "0")}</div>
                <div
                  className={`text-[11px] font-semibold ${
                    gone ? "text-blood line-through" : "text-ink"
                  }`}
                >
                  {lot.litres} L
                </div>
                <div className="mono truncate text-[7.5px] text-muted">{lot.short}</div>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          {shortfall ? (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded border border-blood/50 bg-blood/10 px-2 py-1 mono text-[9.5px] text-blood"
            >
              LOT 07 NEVER SCANNED · 10 L short at the heart · chain still verifies
            </motion.div>
          ) : (
            <div className="rounded border border-teal/40 bg-teal/5 px-2 py-1 mono text-[9.5px] text-teal">
              ALL 10 LOTS RECONCILED · 70 L HEART · 30 L LUNGS
            </div>
          )}
          <span className="mono text-[9px] text-muted/80">
            evidence of a missing lot, not proof of who took it
          </span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-line/60 pt-2.5">
          <span className="mono text-[8.5px] tracking-[0.14em] text-muted/70">
            NOT CLAIMED:
          </span>
          {[
            "generator-failure sound model",
            "handwriting OCR",
            "water-graph reroute",
            "biogas fallback",
            "panic scoring",
          ].map((item) => (
            <span
              key={item}
              className="rounded border border-line/70 px-1.5 py-0.5 mono text-[8px] text-muted/70 line-through decoration-line"
            >
              {item}
            </span>
          ))}
          <span className="mono text-[8.5px] text-muted/60">
            each needs a dataset this repo does not have
          </span>
        </div>
      </div>
    </div>
  );
}
