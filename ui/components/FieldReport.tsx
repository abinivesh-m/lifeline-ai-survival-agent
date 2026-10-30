"use client";

import { COLORS, lifeline } from "@/lib/lifeline";

/**
 * The loop the rest of the page only describes: a phone call arrives, the
 * transcript becomes typed constraints, and the plan moves - no restart, no
 * model call.
 *
 * Two calls, because the interesting behaviour is the pair. The first one
 * confirms what the town already knows and changes nothing; an agent that
 * rewrites its plan on every call is not trustworthy. The second one takes the
 * village road away, and the detour costs fuel the pump was going to get.
 *
 * Every number here is read from artifacts/field_replan.json, produced by
 * `python field_reports.py --from-artifact --write`.
 */
export default function FieldReport() {
  const field = lifeline.field;
  if (!field?.available || field.runs.length === 0) return null;

  const changed = field.runs.find((run) => run.status !== "no_change") ?? field.runs[0];

  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {field.runs.map((run, index) => {
        const moved = run.status !== "no_change";
        const colour = moved ? COLORS.amber : COLORS.muted;
        return (
          <div
            key={run.source}
            className="relative overflow-hidden rounded-xl border border-line bg-panel/60 p-4"
          >
            <div
              className="absolute inset-x-0 top-0 h-[2px]"
              style={{ background: `linear-gradient(90deg, transparent, ${colour}, transparent)` }}
            />
            <div className="flex items-baseline justify-between gap-2">
              <span className="mono text-[10px] tracking-[0.18em]" style={{ color: colour }}>
                CALL {index + 1} · {run.source}
              </span>
              <span className="mono text-[9px] text-muted">
                {run.synthetic ? "SYNTHETIC CLIP" : "REAL RECORDING"}
              </span>
            </div>

            <p className="mt-2 rounded border border-line/70 bg-black/20 px-2 py-1.5 text-[11px] leading-relaxed text-ink/90">
              {run.transcript.trim()}
            </p>

            <div className="mt-2 space-y-1">
              {run.constraints.length === 0 ? (
                <p className="mono text-[9.5px] text-muted">no actionable constraint</p>
              ) : (
                run.constraints.map((c, i) => (
                  <div key={`${c.kind}-${i}`} className="mono text-[9.5px] text-muted">
                    <span className="text-teal">{c.kind}</span> = {String(c.value)}
                    {c.unit ? ` ${c.unit}` : ""}
                    {c.span ? <span className="text-muted/60"> ← &ldquo;{c.span.slice(0, 48)}&rdquo;</span> : null}
                  </div>
                ))
              )}
            </div>

            <div className="mt-2 flex flex-wrap items-baseline gap-2">
              <span
                className="rounded border px-1.5 py-0.5 mono text-[9px]"
                style={{ borderColor: `${colour}55`, color: colour }}
              >
                {run.status}
              </span>
              <span className="mono text-[9.5px] text-muted">
                {run.route_km_before} km → {run.route_km_after} km · {run.route_fuel_before} L →{" "}
                {run.route_fuel_after} L
              </span>
            </div>

            {run.allocation_after ? (
              <div className="mt-1.5 grid grid-cols-2 gap-1.5">
                <div className="rounded border border-line/70 px-2 py-1">
                  <div className="mono text-[8.5px] tracking-[0.14em] text-muted">BEFORE</div>
                  <div className="mono text-[11px] text-ink/80">
                    {run.allocation_before.hospital ?? 0} L heart ·{" "}
                    {run.allocation_before.water_pump ?? 0} L lungs
                  </div>
                </div>
                <div className="rounded border border-line/70 px-2 py-1">
                  <div className="mono text-[8.5px] tracking-[0.14em] text-muted">AFTER</div>
                  <div className="mono text-[11px]" style={{ color: moved ? COLORS.amber : COLORS.ink }}>
                    {run.allocation_after.hospital ?? 0} L heart ·{" "}
                    {run.allocation_after.water_pump ?? 0} L lungs
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        );
      })}

      <div className="rounded-xl border border-line bg-panel/60 p-4 lg:col-span-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <span className="mono text-[10px] tracking-[0.18em] text-teal">WHAT THE SECOND CALL COST</span>
          <span className="mono text-[9px] text-muted">same A* · same solver · no model call</span>
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded border border-line/70 px-2.5 py-1.5">
            <div className="mono text-[8.5px] tracking-[0.14em] text-muted">ROUTE</div>
            <div className="mono text-[12px] text-ink">
              {changed.route_km_before} → {changed.route_km_after} km
            </div>
            <div className="text-[9.5px] text-muted">the 40% saving is gone</div>
          </div>
          <div className="rounded border border-line/70 px-2.5 py-1.5">
            <div className="mono text-[8.5px] tracking-[0.14em] text-muted">DIESEL TO DELIVER</div>
            <div className="mono text-[12px] text-ink">
              {changed.route_fuel_before} → {changed.route_fuel_after} L
            </div>
            <div className="text-[9.5px] text-muted">charged to the reserve, not hidden</div>
          </div>
          <div className="rounded border border-line/70 px-2.5 py-1.5">
            <div className="mono text-[8.5px] tracking-[0.14em] text-muted">PUMP RUNTIME</div>
            <div className="mono text-[12px]" style={{ color: COLORS.amber }}>
              {changed.pump_hours_before} → {changed.pump_hours_after} h
            </div>
            <div className="text-[9.5px] text-muted">one 5 L block off the lungs</div>
          </div>
          <div className="rounded border border-line/70 px-2.5 py-1.5">
            <div className="mono text-[8.5px] tracking-[0.14em] text-muted">WATER LOST</div>
            <div className="mono text-[12px]" style={{ color: COLORS.blood }}>
              {changed.water_litres_lost.toLocaleString()} L
            </div>
            <div className="text-[9.5px] text-muted">stated, not rounded away</div>
          </div>
        </div>
        <p className="mt-2 text-[10.5px] leading-relaxed text-muted">
          {field.note} The extraction is regex over the verbatim transcript: a misheard
          number can be transcribed, but it cannot move diesel unless the words name it.
        </p>
      </div>
    </div>
  );
}
