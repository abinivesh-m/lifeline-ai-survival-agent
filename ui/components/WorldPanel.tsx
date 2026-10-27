"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { lifeline } from "@/lib/lifeline";

const TOWNS = lifeline.world.towns;

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

type Result = {
  name: string;
  country: string;
  distance: number;
  dataClass: string;
  lat: number;
  lon: number;
} | null;

export default function WorldPanel() {
  const [lat, setLat] = useState("14.5995");
  const [lon, setLon] = useState("120.9842");
  const [result, setResult] = useState<Result>(null);

  const byRegion = useMemo(() => {
    const groups = new Map<string, typeof TOWNS>();
    TOWNS.forEach((town) => {
      const list = groups.get(town.region) ?? [];
      list.push(town);
      groups.set(town.region, list);
    });
    return Array.from(groups.entries());
  }, []);

  const query = () => {
    const la = Number(lat);
    const lo = Number(lon);
    if (!Number.isFinite(la) || !Number.isFinite(lo)) return;
    const ranked = [...TOWNS]
      .map((town) => ({ town, d: haversine(la, lo, town.lat, town.lon) }))
      .sort((a, b) => a.d - b.d);
    const best = ranked[0];
    setResult({
      name: best.town.name,
      country: best.town.country,
      distance: best.d,
      dataClass: best.town.data_class,
      lat: best.town.lat,
      lon: best.town.lon,
    });
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_1.35fr]">
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
          <button
            onClick={query}
            className="mt-2 w-full rounded-md border border-teal/60 bg-teal/10 px-3 py-2 mono text-[11px] font-semibold tracking-[0.12em] text-teal transition hover:bg-teal/20"
          >
            RUN lifeline_query()
          </button>

          {result && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 rounded-lg border border-line bg-black/40 p-3"
            >
              <div className="flex items-baseline justify-between">
                <span className="text-[13px] font-semibold text-ink">{result.name}</span>
                <span className="mono text-[10px] text-muted">{result.country}</span>
              </div>
              <div className="mono mt-1 text-[10px] text-muted">
                nearest configured point · {result.distance} km · {result.lat.toFixed(4)},{" "}
                {result.lon.toFixed(4)}
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <span
                  className={`rounded border px-1.5 py-0.5 mono text-[8.5px] ${
                    result.dataClass === "surveyed"
                      ? "border-teal/50 bg-teal/10 text-teal"
                      : "border-amber/50 bg-amber/10 text-amber"
                  }`}
                >
                  {result.dataClass}
                </span>
                <span className="rounded border border-line px-1.5 py-0.5 mono text-[8.5px] text-muted">
                  70 L heart · 30 L lungs
                </span>
              </div>
              <p className="mt-2 text-[10.5px] leading-relaxed text-muted">
                {result.dataClass === "surveyed"
                  ? "Surveyed case: reserve and demands come from town.json in this repo."
                  : "Generic template. The arithmetic is real; the local fuel figures are not measured. This is labelled rather than dressed up as a local survey."}
              </p>
            </motion.div>
          )}
        </div>

        <div className="rounded-xl border border-line bg-panel/70 p-4">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">SCALE</div>
          <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted">
            {lifeline.world.note}
          </p>
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
        </div>
      </div>

      <div className="rounded-xl border border-line bg-panel/60 p-4">
        <div className="mono text-[10px] tracking-[0.18em] text-muted">
          CONFIGURED WORLD POINTS · COORDINATES ONLY EXCEPT KOTTUR
        </div>
        <div className="mt-2 max-h-[330px] space-y-3 overflow-y-auto pr-1">
          {byRegion.map(([region, towns]) => (
            <div key={region}>
              <div className="mono text-[9px] tracking-[0.16em] text-teal/80">
                {region.toUpperCase()} · {towns.length}
              </div>
              <div className="mt-1 grid gap-1 sm:grid-cols-2">
                {towns.map((town) => (
                  <button
                    key={town.id}
                    onClick={() => {
                      setLat(String(town.lat));
                      setLon(String(town.lon));
                      setResult({
                        name: town.name,
                        country: town.country,
                        distance: 0,
                        dataClass: town.data_class,
                        lat: town.lat,
                        lon: town.lon,
                      });
                    }}
                    className={`flex items-baseline justify-between gap-2 rounded border px-2 py-1 text-left transition ${
                      town.data_class === "surveyed"
                        ? "border-teal/40 bg-teal/5 hover:bg-teal/10"
                        : "border-line/70 bg-black/20 hover:border-muted/50"
                    }`}
                  >
                    <span className="truncate text-[10.5px] text-ink/85">{town.name}</span>
                    <span className="mono shrink-0 text-[8.5px] text-muted">
                      {town.lat.toFixed(2)}, {town.lon.toFixed(2)}
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
