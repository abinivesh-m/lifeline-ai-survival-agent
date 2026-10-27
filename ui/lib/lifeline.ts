import raw from "@/public/data/lifeline.json";

export type Messages = Record<string, string>;

export type Frame = {
  file: string;
  stem: string;
  severity: number;
  objects: number;
  overlay: string | null;
  photo: string | null;
};

export type TownNode = {
  label: string;
  role: string;
  priority: number;
  litres: number;
  runtime_hours?: number;
  people?: number;
  lat: number;
  lon: number;
};

export type WorldTown = {
  id: string;
  name: string;
  country: string;
  region: string;
  lat: number;
  lon: number;
  data_class: string;
};

export type Clock = {
  litres: number;
  load_factor: number;
  burn_l_per_hour: number;
  hours: number;
  minutes: number;
  dies_at: string;
  started_at: string;
  label: string;
  confidence: string;
  note: string;
};

export type DnaLot = {
  seq: number;
  litres: number;
  mass_kg: number;
  destination: string;
  prev: string;
  hash: string;
  short: string;
};

export type Blood = {
  sweat: {
    litres_measured: number;
    temp_c: number;
    reference_c: number;
    beta_per_c: number;
    litres_at_reference: number;
    deficit_litres: number;
    deficit_percent: number;
    deficit_range_litres: [number, number];
    mass_kg: number;
    density_kg_per_l: number;
    folklore_litres: number;
    folklore_verdict: string;
    note: string;
  };
  dna: {
    lot_litres: number;
    lot_count: number;
    total_litres: number;
    total_mass_kg: number;
    split: Record<string, number>;
    head: string;
    genesis: string;
    algorithm: string;
    note: string;
  };
  dna_lots: DnaLot[];
  dna_verify: { ok: boolean; lots: number; head: string };
  clock: Clock;
  clock_loaded: Clock;
  inverse: {
    heart: { litres: number; label: string; hours: number };
    lungs: { litres: number; label: string; hours: number };
    water: {
      litres_delivered: number;
      people: number;
      days_at_documented_demand: number;
      demand_litres_per_day: number;
    };
    naive_split: { hospital_litres: number; heart_label: string; heart_hours: number };
    note: string;
  };
  allocation: Record<string, number>;
  honesty: string[];
};

export type LifeLineData = {
  town: {
    name?: string;
    district?: string;
    state?: string;
    pin?: string;
    crisis?: { expected_clear_hours?: number; description?: string };
    reserve?: { total_litres?: number };
    allocation_policy?: { priority_order?: string[] };
  };
  organs: Record<string, TownNode>;
  graph: {
    order: string[];
    edges: [string, string][];
    cascade: {
      if_failed: string;
      downstream_failed: string[];
      people_affected: number;
    };
  };
  route: {
    path: string[];
    distance_km: number;
    saving: { km: number; percent: number; fuel_litres: number };
  };
  protocols: {
    snake_boat_relay: {
      mode: "road" | "water" | "none";
      switched: boolean;
      armed: boolean;
      water_edges: number;
      road_km: number | null;
      km: number | null;
      path: string[];
      note: string;
    };
    ant_pheromone: {
      seed: number;
      ants: number;
      iterations: number;
      runs: number;
      best_km: number | null;
      best_path: string[];
      learned_after: number | null;
      blocked_share_final: number;
      note: string;
    };
  };
  blood: Blood;
  allocation: {
    policy: Record<string, number>;
    total: number;
    confidence: number;
    source: string;
    justification: string;
    evidence: { id: string; claim: string; source?: string }[];
    inference: { claim: string; litres: number; confidence: number }[];
    validation?: { ok: boolean; checks?: string[] };
  };
  sam: {
    available: boolean;
    model: string | null;
    prompt: string | null;
    frames: Frame[];
    worst: number | null;
    cost_usd: number | null;
  };
  voice: {
    available: boolean;
    model: string | null;
    transcript: string | null;
    seconds: number | null;
    synthetic: boolean;
    cost_usd: number | null;
  };
  credit: {
    budget_usd: number;
    spent_usd: number;
    percent: number;
    level: string;
    remaining_usd: number;
    reserve_usd: number;
    by_model: Record<string, { calls: number; spent_usd: number; budget_usd: number }>;
  };
  openweight: {
    available: boolean;
    provider: string | null;
    model: string | null;
    runs: number;
    valid_runs: number;
    allocation: Record<string, number> | null;
    latencies_s: number[];
    latest_at: string | null;
    note: string | null;
  };
  escalation: {
    tiers: { tier: number; window: string; action: string; detail: string }[];
    degraded: Record<string, number>;
  };
  world: { towns: WorldTown[]; note: string };
  locales: { code: string; native: string; language: string; dir: string }[];
  messages: Record<string, Messages>;
  baseline: { manual_minutes: number; agent_minutes: number; note: string };
};

export const lifeline = raw as unknown as LifeLineData;

export const ORDER_LABEL: Record<string, string> = {
  fuel_depot: "BLOOD",
  hospital: "HEART",
  water_pump: "LUNGS",
  shelters: "ORGANS",
};

export const ORDER_KEY: Record<string, string> = {
  fuel_depot: "lifegrid.blood",
  hospital: "lifegrid.heart",
  water_pump: "lifegrid.lungs",
  shelters: "lifegrid.organs",
};

export const COLORS = {
  teal: "#2dd4bf",
  blood: "#f87171",
  lung: "#60a5fa",
  amber: "#f5b942",
  muted: "#86a0ab",
  ink: "#e8f3f6",
};

/** The eight steps the agent actually runs, in the order it runs them. */
export const STEPS = [
  { n: 1, key: "PERCEIVE", tool: "SAM 3.1", detail: "noun-phrase segmentation, real pixel masks" },
  { n: 2, key: "LISTEN", tool: "Voice Transcribe", detail: "Tamil report, language bias, keywords" },
  { n: 3, key: "GRAPH", tool: "Kahn sort", detail: "heartbeat before lungs, always" },
  { n: 4, key: "ROUTE", tool: "A* heapq", detail: "4.2 km blocked, 7.8 km found" },
  { n: 5, key: "ALLOCATE", tool: "Wonder + validator", detail: "70 L / 30 L, then checked in code" },
  { n: 6, key: "BUDGET", tool: "$150 ledger", detail: "every call priced, alerts at 80 / 95%" },
  { n: 7, key: "APPROVE", tool: "human gate", detail: "nothing moves until a person decides" },
  { n: 8, key: "REPLAN", tool: "new constraint", detail: "same solver, reserve cut to 80 L" },
] as const;
