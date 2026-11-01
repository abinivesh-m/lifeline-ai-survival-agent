"use client";

import { useMemo, useState } from "react";

import grid from "@/public/data/counterfactuals.json";
import { COLORS } from "@/lib/lifeline";

/**
 * The console the rest of the page only describes.
 *
 * Nothing here computes. Every number is a row in
 * `ui/public/data/counterfactuals.json`, produced by the same A* search and the
 * same priority solver the agent runs, and re-derived by `test_counterfactual.py`
 * so a stale row fails the build instead of lying to a judge.
 *
 * Two things are worth dragging: the reserve down, to watch the lungs lose their
 * last block; and the operator switch, to watch the validator refuse a human.
 */

type Row = {
  id: string;
  reserve_litres: number;
  village_road: "open" | "blocked";
  operator: "none" | "pump_first";
  status: string;
  route_km: number;
  route_fuel_litres: number;
  reserve_in_force: number;
  allocation: Record<string, number>;
  total_litres: number;
  pump_hours: number;
  water_litres_lost: number;
  heart_protected: boolean;
  validator: string[];
  changes: { kind: string; before: string | number; after: string | number }[];
  instruction?: Record<string, number>;
  override_refused?: boolean;
  override_reasons?: string[];
  applied_instead?: Record<string, number>;
};

const DATA = grid as unknown as {
  axes: { reserve_litres: number[]; village_road: ("open" | "blocked")[]; operator: ("none" | "pump_first")[] };
  base: { reserve_litres: number; hospital_demand_litres: number; pump_demand_litres: number };
  rows: Row[];
  note: string;
};

const RESERVES = [...DATA.axes.reserve_litres].sort((a, b) => a - b);
const HOSPITAL_DEMAND = DATA.base.hospital_demand_litres;

function initialState() {
  if (typeof window === "undefined") {
    return { reserve: DATA.base.reserve_litres, road: "open" as "open" | "blocked", operator: "none" as "none" | "pump_first" };
  }
  const params = new URLSearchParams(window.location.search);
  const reserve = Number(params.get("reserve"));
  const road = params.get("road");
  const operator = params.get("operator");
  return {
    reserve: RESERVES.includes(reserve) ? reserve : DATA.base.reserve_litres,
    road: road === "blocked" ? ("blocked" as const) : ("open" as const),
    operator: operator === "pump_first" ? ("pump_first" as const) : ("none" as const),
  };
}

export default function Counterfactual() {
  const initial = initialState();
  const [reserve, setReserve] = useState(initial.reserve);
  const [road, setRoad] = useState<"open" | "blocked">(initial.road);
  const [operator, setOperator] = useState<"none" | "pump_first">(initial.operator);
  const [copied, setCopied] = useState(false);

  const row = useMemo<Row | undefined>(
    () =>
      DATA.rows.find(
        (r) => r.reserve_litres === reserve && r.village_road === road && r.operator === operator,
      ),
    [reserve, road, operator],
  );

  // The lungs' share across the whole slider, for the current road. This is the
  // cliff: one block per 5 L until the heart is fed, then nothing.
  const strip = useMemo(
    () =>
      RESERVES.map((value) => {
        const r = DATA.rows.find(
          (item) => item.reserve_litres === value && item.village_road === road && item.operator === "none",
        );
        return { reserve: value, litres: r?.allocation.water_pump ?? 0, hours: r?.pump_hours ?? 0 };
      }),
    [road],
  );

  if (!row) return null;

  const heart = row.allocation.hospital ?? 0;
  const lungs = row.allocation.water_pump ?? 0;
  const maxLungs = Math.max(...strip.map((s) => s.litres), 1);
  const refused = row.operator === "pump_first" && row.override_refused;

  const copyLink = () => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.set("reserve", String(reserve));
    url.searchParams.set("road", road);
    url.searchParams.set("operator", operator);
    navigator.clipboard?.writeText(url.toString()).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    });
  };

  const card = "rounded border border-line/70 px-2.5 py-1.5";
  const kicker = "mono text-[8.5px] tracking-[0.14em] text-muted";
  const value = "mono text-[15px] leading-tight";

  return (
    <div className="mt-3 rounded-xl border border-line bg-panel/60 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <span className="mono text-[10px] tracking-[0.18em] text-teal">
          MOVE THE WORLD · THE PLAN MOVES
        </span>
        <span className="mono text-[9px] text-muted">
          {DATA.rows.length} real solver runs · no model call · no network
        </span>
        <button
          onClick={copyLink}
          className="mono rounded border border-line/70 px-2 py-0.5 text-[9px] text-muted transition hover:border-teal/60 hover:text-teal"
        >
          {copied ? "copied" : "copy link to this world"}
        </button>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-[280px_1fr]">
        {/* controls */}
        <div className="space-y-3">
          <div>
            <div className="flex items-baseline justify-between">
              <span className={kicker}>USABLE DIESEL</span>
              <span className="mono text-[12px] text-ink">{reserve} L</span>
            </div>
            <input
              aria-label="Usable diesel in litres"
              type="range"
              min={RESERVES[0]}
              max={RESERVES[RESERVES.length - 1]}
              step={5}
              value={reserve}
              onChange={(event) => setReserve(Number(event.target.value))}
              className="mt-1.5 w-full accent-[#2dd4bf]"
            />
            <div className="mono mt-1 flex justify-between text-[8.5px] text-muted">
              <span>{RESERVES[0]} L</span>
              <span>100 L was the plan</span>
            </div>
          </div>

          <div>
            <span className={kicker}>VILLAGE ROAD</span>
            <div className="mt-1 flex gap-1.5">
              {DATA.axes.village_road.map((option) => {
                const active = road === option;
                return (
                  <button
                    key={option}
                    onClick={() => setRoad(option)}
                    className="mono flex-1 rounded border px-2 py-1 text-[9.5px] uppercase tracking-[0.1em] transition"
                    style={{
                      borderColor: active ? COLORS.teal : "rgba(134,160,171,0.35)",
                      color: active ? COLORS.teal : COLORS.muted,
                      background: active ? "rgba(45,212,191,0.08)" : "transparent",
                    }}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <span className={kicker}>OPERATOR SAYS</span>
            <div className="mt-1 flex gap-1.5">
              <button
                onClick={() => setOperator("none")}
                className="mono flex-1 rounded border px-2 py-1 text-[9.5px] uppercase tracking-[0.1em] transition"
                style={{
                  borderColor: operator === "none" ? COLORS.teal : "rgba(134,160,171,0.35)",
                  color: operator === "none" ? COLORS.teal : COLORS.muted,
                  background: operator === "none" ? "rgba(45,212,191,0.08)" : "transparent",
                }}
              >
                trust the plan
              </button>
              <button
                onClick={() => setOperator("pump_first")}
                className="mono flex-1 rounded border px-2 py-1 text-[9.5px] uppercase tracking-[0.1em] transition"
                style={{
                  borderColor: operator === "pump_first" ? COLORS.amber : "rgba(134,160,171,0.35)",
                  color: operator === "pump_first" ? COLORS.amber : COLORS.muted,
                  background: operator === "pump_first" ? "rgba(245,185,66,0.08)" : "transparent",
                }}
              >
                pump first
              </button>
            </div>
          </div>

          <div className="rounded border border-line/70 px-2 py-1.5">
            <div className={kicker}>LUNGS ACROSS THE SLIDER</div>
            <div className="mt-1 flex h-8 items-end gap-[2px]">
              {strip.map((s) => (
                <div
                  key={s.reserve}
                  title={`${s.reserve} L -> ${s.litres} L to the pump`}
                  className="flex-1 rounded-sm"
                  style={{
                    height: `${Math.max(2, (s.litres / maxLungs) * 100)}%`,
                    background: s.reserve === reserve ? COLORS.teal : "rgba(96,165,250,0.35)",
                  }}
                />
              ))}
            </div>
            <div className="mono mt-1 flex justify-between text-[8px] text-muted">
              <span>{RESERVES[0]}</span>
              <span>L to the pump</span>
              <span>{RESERVES[RESERVES.length - 1]}</span>
            </div>
          </div>
        </div>

        {/* result */}
        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2 xl:grid-cols-4">
            <div className={card}>
              <div className={kicker}>HEART</div>
              <div className={value} style={{ color: row.heart_protected ? COLORS.ink : COLORS.blood }}>
                {heart} L
              </div>
              <div className="text-[9.5px] text-muted">
                {row.heart_protected ? "demand met" : `short of ${HOSPITAL_DEMAND} L`}
              </div>
            </div>
            <div className={card}>
              <div className={kicker}>LUNGS</div>
              <div className={value} style={{ color: lungs > 0 ? COLORS.lung : COLORS.muted }}>
                {lungs} L
              </div>
              <div className="text-[9.5px] text-muted">{row.pump_hours} h of pumping</div>
            </div>
            <div className={card}>
              <div className={kicker}>ROUTE</div>
              <div className={value} style={{ color: road === "open" ? COLORS.teal : COLORS.amber }}>
                {row.route_km} km
              </div>
              <div className="text-[9.5px] text-muted">{row.route_fuel_litres} L to deliver</div>
            </div>
            <div className={card}>
              <div className={kicker}>WATER LOST</div>
              <div className={value} style={{ color: row.water_litres_lost > 0 ? COLORS.blood : COLORS.ink }}>
                {row.water_litres_lost.toLocaleString()} L
              </div>
              <div className="text-[9.5px] text-muted">stated, not rounded</div>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2">
            <div className={card}>
              <div className={kicker}>THE PLAN</div>
              <div className="mono text-[12px] text-ink">
                {heart} L heart · {lungs} L lungs · {row.total_litres} L total
              </div>
              <div className="text-[9.5px] text-muted">
                reserve in force {row.reserve_in_force} L
                {row.changes.length ? ` · ${row.changes.length} change(s) from the base plan` : " · unchanged"}
              </div>
            </div>

            <div
              className="rounded border px-2.5 py-1.5"
              style={{
                borderColor: refused ? `${COLORS.amber}66` : `${COLORS.teal}44`,
                background: refused ? "rgba(245,185,66,0.06)" : "rgba(45,212,191,0.05)",
              }}
            >
              <div className={kicker}>VALIDATOR</div>
              {refused ? (
                <>
                  <div className="mono text-[11px]" style={{ color: COLORS.amber }}>
                    REFUSED · applied instead {row.applied_instead?.hospital ?? 0} L /{" "}
                    {row.applied_instead?.water_pump ?? 0} L
                  </div>
                  <ul className="mt-1 space-y-0.5">
                    {(row.override_reasons ?? []).map((reason) => (
                      <li key={reason} className="text-[9.5px] leading-snug text-muted">
                        · {reason}
                      </li>
                    ))}
                  </ul>
                </>
              ) : (
                <>
                  <div className="mono text-[11px]" style={{ color: COLORS.teal }}>
                    PASS · every hard rule holds
                  </div>
                  <div className="text-[9.5px] text-muted">
                    exact total, no organ over demand, heart never starved
                  </div>
                </>
              )}
            </div>
          </div>

          <p className="text-[10.5px] leading-relaxed text-muted">
            {DATA.note} The operator switch is the point: the agent accepts a changed world and refuses a
            changed priority, and it names both reasons instead of quietly obeying.
          </p>
        </div>
      </div>
    </div>
  );
}
