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
    brain?: {
      source: string | null;
      model: string | null;
      provider: string | null;
      status: string | null;
      latency_s: number | null;
      at: string | null;
      justification: string | null;
      confidence: number | null;
      allocation: Record<string, number> | null;
      valid: boolean;
      rejected: unknown;
    } | null;
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
    ledger_rows: number;
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
  field: {
    available: boolean;
    note: string | null;
    runs: {
      source: string;
      transcript: string;
      status: string;
      synthetic: boolean;
      constraints: { kind: string; value: string | number; unit: string | null; span: string | null }[];
      route_km_before: number;
      route_km_after: number;
      route_fuel_before: number;
      route_fuel_after: number;
      allocation_before: Record<string, number>;
      allocation_after: Record<string, number> | null;
      pump_hours_before: number;
      pump_hours_after: number;
      water_litres_lost: number;
      changes: {
        kind: string;
        before: string | number;
        after: string | number;
        detail: string;
        span: string | null;
      }[];
      validator: string[];
    }[];
  };
  escalation: {
    tiers: { tier: number; window: string; action: string; detail: string }[];
    degraded: Record<string, number>;
    run?: {
      tier: number;
      decision: string;
      window: string;
      tier2_at_s: number;
      languages: string[];
      payloads_per_language: number;
      payloads_total: number;
      channels: string[];
      status: string | string[];
      note: string;
      evidence: string;
      gate: string;
      at: string;
    } | null;
  };
  world: { towns: WorldTown[]; note: string };
  locales: { code: string; native: string; language: string; dir: string }[];
  multilingual: {
    available: boolean;
    note?: string;
    generated_utc?: string;
    generator?: { provider: string; model: string; cost_usd?: number };
    reviewer?: { provider: string; model: string; cost_usd?: number };
    totals?: {
      locales: number;
      valid: number;
      model_drafted: number;
      voice_scripts: number;
      allocation_scripts: number;
      cost_usd: number;
      last_batch_usd?: number;
    };
    rules?: {
      max_chars: Record<string, number>;
      allowed_numbers: string[];
      require_reply_codes: string[];
      fallback: string;
      speech: string;
    };
    speech?: {
      engine: string;
      licence: string;
      device: string;
      sample_rate_hz: number;
      cost_usd: number;
      clips: number;
      seconds: number;
      note: string;
    };
    locales: {
      code: string;
      language: string;
      native: string;
      sms: string;
      voice: string;
      allocation: string;
      sms_source: string;
      voice_source: string;
      drafted: boolean;
      valid: boolean;
      audio: Record<
        string,
        { src: string; seconds: number; bytes: number; model: string; text_sha256: string }
      >;
    }[];
  };
  seri: {
    available: boolean;
    note?: string;
    generated_utc?: string;
    summary?: {
      languages: number;
      spoken: number;
      approved: number;
      withheld: number;
      text_only: Record<string, string>;
    };
    locales: {
      locale: string;
      native: string;
      language: string;
      phrase: string;
      transcript: string | null;
      asr?: {
        status: string;
        model: string;
        latency_s?: number;
        language_bias?: string[];
      };
      model?: {
        status: string;
        intent: string;
        confidence: number;
        reason: string;
        latency_s: number;
      };
      gate?: {
        decision: string;
        approved: boolean;
        locale: string;
        token_intent: string;
        model_intent: string;
        confidence: number;
        threshold: number;
        reasons: string[];
        rule: string;
      };
      ledger?: { seq: number; action: string; hash: string; prev: string } | null;
      cost_usd?: number;
      audio: { src: string | null; sha256: string | null; seconds: number | null };
    }[];
    cost_usd?: number;
  };
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
  { n: 5, key: "ALLOCATE", tool: "Open weight + validator", detail: "70 L / 30 L, then checked in code" },
  { n: 6, key: "BUDGET", tool: "$150 ledger", detail: "every call priced, alerts at 80 / 95%" },
  { n: 7, key: "APPROVE", tool: "human gate", detail: "a person decides; silence climbs to SMS, WhatsApp, voice" },
  { n: 8, key: "REPLAN", tool: "new constraint", detail: "replans without a restart, writes runs/latest.json" },
] as const;
