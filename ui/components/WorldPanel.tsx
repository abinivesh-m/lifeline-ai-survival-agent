"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { lifeline, type WorldTown } from "@/lib/lifeline";
import WorldGlobe3D from "./WorldGlobe3D";

const TOWNS = lifeline.world.towns;
const ORIGIN = TOWNS.find((town) => town.data_class === "surveyed") ?? TOWNS[0];

/** The 30-second demo path: origin, then three continents. */
const TOUR_IDS = ["kottur", "manila", "jakarta", "rio_favela", "kibera"];

/** Two presets the judge can hit in one click. Lahore is a labelled template. */
const PRESETS = [
  { id: "kottur", label: "KOTTUR", lat: "11.0168", lon: "76.9558" },
  { id: "lahore", label: "LAHORE", lat: "31.5204", lon: "74.3587" },
];

function haversine(lat1: number, lon1: number, lat2: number, lon2: number) {
  const R = 6371.0088;
  const toRad = (v: number) => (v * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return Math.round(2 * R * Math.asin(Math.sqrt(a)) * 10) / 10;
}

export default function WorldPanel() {
  const [lat, setLat] = useState("11.0168");
  const [lon, setLon] = useState("76.9558");
  const [selected, setSelected] = useState<WorldTown>(ORIGIN);
  const [touring, setTouring] = useState(false);
  const [tourStep, setTourStep] = useState(0);

  const byRegion = useMemo(() => {
    const groups = new Map<string, WorldTown[]>();
    TOWNS.forEach((town) => {
      const list = groups.get(town.region) ?? [];
      list.push(town);
      groups.set(town.region, list);
    });
    return Array.from(groups.entries());
  }, []);

  useEffect(() => {
    if (!touring) return;
    const id = window.setInterval(() => {
      setTourStep((step) => {
        const next = (step + 1) % TOUR_IDS.length;
        const town = TOWNS.find((candidate) => candidate.id === TOUR_IDS[next]);
        if (town) setSelected(town);
        return next;
      });
    }, 3200);
    return () => window.clearInterval(id);
  }, [touring]);

  const distanceFromOrigin = haversine(ORIGIN.lat, ORIGIN.lon, selected.lat, selected.lon);

  const query = () => {
    const la = Number(lat);
    const lo = Number(lon);
    if (!Number.isFinite(la) || !Number.isFinite(lo)) return;
    const ranked = [...TOWNS]
      .map((town) => ({ town, d: haversine(la, lo, town.lat, town.lon) }))
      .sort((a, b) => a.d - b.d);
    setSelected(ranked[0].town);
  };

  const applyPreset = (preset: (typeof PRESETS)[number]) => {
    setLat(preset.lat);
    setLon(preset.lon);
    const town = TOWNS.find((candidate) => candidate.id === preset.id);
    if (town) {
      setTouring(false);
      setSelected(town);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1.15fr]">
      <div className="space-y-3">
        <div className="glass rounded-xl p-4">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">SINGLE POINT QUERY</div>
          <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">
            The same arithmetic runs on any coordinate. Type a point and the agent
            matches the nearest configured town.
          </p>
          <div className="mt-2.5 grid grid-cols-2 gap-2">
            <label className="block">
              <span className="mono text-[9px] text-muted">lat</span>
              <input
                value={lat}
                onChange={(event) => setLat(event.target.value)}
                className="mt-1 w-full rounded border border-line bg-black/40 px-2 py-1.5 mono text-[12px] text-ink outline-none focus:border-teal/60"
              />
            </label>
            <label className="block">
              <span className="mono text-[9px] text-muted">lon</span>
              <input
                value={lon}
                onChange={(event) => setLon(event.target.value)}
                className="mt-1 w-full rounded border border-line bg-black/40 px-2 py-1.5 mono text-[12px] text-ink outline-none focus:border-teal/60"
              />
            </label>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <span className="mono text-[8.5px] tracking-[0.14em] text-muted/70">PRESET</span>
            {PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => applyPreset(preset)}
                className={`rounded border px-1.5 py-0.5 mono text-[8.5px] transition ${
                  selected.id === preset.id
                    ? "border-teal/60 bg-teal/10 text-teal"
                    : "border-line/70 bg-black/20 text-muted hover:border-muted/50"
                }`}
              >
                {preset.label} {preset.lat}, {preset.lon}
              </button>
            ))}
          </div>
          <button
            onClick={query}
            className="mt-2 w-full rounded-md border border-teal/60 bg-teal/10 px-3 py-2 mono text-[11px] font-semibold tracking-[0.12em] text-teal transition hover:bg-teal/20"
          >
            RUN lifeline_query()
          </button>

          <motion.div
            key={selected.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-3 rounded-lg border border-line bg-black/40 p-3"
          >
            <div className="flex items-baseline justify-between">
              <span className="text-[13px] font-semibold text-ink">{selected.name}</span>
              <span className="mono text-[10px] text-muted">{selected.country}</span>
            </div>
            <div className="mono mt-1 text-[10px] text-muted">
              {selected.lat.toFixed(4)}, {selected.lon.toFixed(4)} ·{" "}
              {distanceFromOrigin === 0 ? "origin case" : `${distanceFromOrigin.toLocaleString()} km from Kottur`}
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              <span
                className={`rounded border px-1.5 py-0.5 mono text-[8.5px] ${
                  selected.data_class === "surveyed"
                    ? "border-teal/50 bg-teal/10 text-teal"
                    : "border-amber/50 bg-amber/10 text-amber"
                }`}
              >
                {selected.data_class}
              </span>
              <span className="rounded border border-line px-1.5 py-0.5 mono text-[8.5px] text-muted">
                70 L heart · 30 L lungs
              </span>
              <span className="rounded border border-line px-1.5 py-0.5 mono text-[8.5px] text-muted">
                A* 7.8 km · 40% saved
              </span>
            </div>
            <p className="mt-2 text-[10.5px] leading-relaxed text-muted">
              {selected.data_class === "surveyed"
                ? "Surveyed case: reserve and demands come from town.json in this repo."
                : "Generic template. The arithmetic is real; the local fuel figures are not measured. This is labelled rather than dressed up as a local survey."}
            </p>
          </motion.div>
        </div>

        <div className="rounded-xl border border-line bg-panel/70 p-4">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">SCALE</div>
          <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">{lifeline.world.note}</p>
          <div className="mt-2 grid grid-cols-3 gap-2 text-center">
            <div className="rounded border border-line bg-black/30 p-2">
              <div className="text-lg font-bold text-teal">{TOWNS.length}</div>
              <div className="mono text-[8px] text-muted">configured points</div>
            </div>
            <div className="rounded border border-line bg-black/30 p-2">
              <div className="text-lg font-bold text-amber">1</div>
              <div className="mono text-[8px] text-muted">surveyed</div>
            </div>
            <div className="rounded border border-line bg-black/30 p-2">
              <div className="text-lg font-bold text-lung">3.5B</div>
              <div className="mono text-[8px] text-muted">people in this pattern</div>
            </div>
          </div>
          <div className="mt-2 space-y-1 border-t border-line/60 pt-2 mono text-[8.5px] leading-relaxed text-muted/80">
            <div>World Bank · 2,564 cities · 177 countries · 14M km roads</div>
            <div>Global Flood Database · 913 flood events</div>
            <div>GDIS · 39,953 locations = 3.5B people in this pattern</div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-line bg-panel/60 p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <div className="mono text-[10px] tracking-[0.18em] text-muted">
              BUILT IN KOTTUR · APPLIED ANYWHERE
            </div>
            <div className="mono mt-1 text-[9px] text-muted/70">
              arc = {ORIGIN.name} → {selected.name}
            </div>
          </div>
          <button
            onClick={() => {
              setTouring((value) => !value);
              setTourStep(0);
            }}
            className={`shrink-0 rounded-md border px-2.5 py-1.5 mono text-[9px] font-semibold tracking-[0.12em] transition ${
              touring
                ? "border-blood/60 bg-blood/10 text-blood"
                : "border-teal/60 bg-teal/10 text-teal hover:bg-teal/20"
            }`}
          >
            {touring ? "STOP TOUR" : "30s TOUR"}
          </button>
        </div>

        <WorldGlobe3D selected={selected} onSelect={setSelected} className="mt-2 h-[330px] w-full" />

        <div className="mt-1 flex flex-wrap gap-1">
          {TOUR_IDS.map((id) => {
            const town = TOWNS.find((candidate) => candidate.id === id);
            if (!town) return null;
            const active = town.id === selected.id;
            return (
              <button
                key={id}
                onClick={() => {
                  setTouring(false);
                  setSelected(town);
                }}
                className={`rounded border px-2 py-1 mono text-[9px] transition ${
                  active
                    ? "border-teal/60 bg-teal/10 text-teal"
                    : "border-line/70 bg-black/20 text-muted hover:border-muted/50"
                }`}
              >
                {town.name.split(",")[0]}
              </button>
            );
          })}
        </div>

        <div className="mt-2 max-h-[150px] space-y-2 overflow-y-auto pr-1">
          {byRegion.map(([region, towns]) => (
            <div key={region}>
              <div className="mono text-[8.5px] tracking-[0.16em] text-teal/80">
                {region.toUpperCase()} · {towns.length}
              </div>
              <div className="mt-1 grid gap-1 sm:grid-cols-2">
                {towns.map((town) => (
                  <button
                    key={town.id}
                    onClick={() => {
                      setTouring(false);
                      setSelected(town);
                      setLat(String(town.lat));
                      setLon(String(town.lon));
                    }}
                    className={`flex items-baseline justify-between gap-2 rounded border px-2 py-1 text-left transition ${
                      town.id === selected.id
                        ? "border-teal/50 bg-teal/10"
                        : town.data_class === "surveyed"
                          ? "border-teal/40 bg-teal/5 hover:bg-teal/10"
                          : "border-line/70 bg-black/20 hover:border-muted/50"
                    }`}
                  >
                    <span className="truncate text-[10px] text-ink/85">{town.name}</span>
                    <span className="mono shrink-0 text-[8px] text-muted">
                      {town.lat.toFixed(1)}, {town.lon.toFixed(1)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
