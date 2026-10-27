export type SectionMeta = {
  id: string;
  n: string;
  kicker: string;
  title: string;
  note: string;
  tools: string[];
};

/**
 * One list, three uses: the sticky nav, the contents grid and each section
 * header. Keeping it in one place means a section can never be numbered twice
 * and the labels can never drift apart.
 */
export const SECTIONS: SectionMeta[] = [
  {
    id: "cascade",
    n: "01",
    kicker: "DEPENDENCY",
    title: "The pump cannot run without the heart",
    note: "One DAG: fuel_depot → hospital → water_pump → shelters. Kahn's algorithm fixes the order.",
    tools: ["Kahn sort", "dependency_graph.py", "deterministic"],
  },
  {
    id: "route",
    n: "02",
    kicker: "ROUTE",
    title: "4.2 km that cannot be driven",
    note: "A* over the repo road graph, every saving measured against the 13.0 km detour. No weather API.",
    tools: ["A* heapq", "a_star.py", "4.2 km blocked", "no weather API"],
  },
  {
    id: "blood",
    n: "03",
    kicker: "BLOOD INTELLIGENCE",
    title: "Measure the blood before you spend it",
    note: "Usable volume at 42 °C, lot provenance and runtime hours, before any model speaks.",
    tools: ["blood.py --all", "no model call", "reproducible"],
  },
  {
    id: "allocate",
    n: "04",
    kicker: "ALLOCATE",
    title: "What the models actually returned",
    note: "Segmentation, transcript, reasoning, validation and the ledger, side by side.",
    tools: ["SAM 3.1", "muse-voice", "muse-wonder", "ledger"],
  },
  {
    id: "escalation",
    n: "05",
    kicker: "LATE APPROVAL",
    title: "When the one person with the phone does not answer",
    note: "Four escalation tiers, hash-chained, ending in a human decision. PAPER QR + TEMPLE BELL PROTOCOL — 0 phone needed to Tier 4.",
    tools: ["4 tiers", "sha256 chain", "human gate", "paper QR"],
  },
  {
    id: "offline",
    n: "06",
    kicker: "OFFLINE + OPEN WEIGHT",
    title: "The core runs with the wire cut",
    note: "Deterministic routing and allocation with no network; the Open Weight path is partner-hosted, not local.",
    tools: ["LIFELINE_OFFLINE=1", "no API key", "Spark Open · Baseten"],
  },
  {
    id: "timeline",
    n: "07",
    kicker: "AGENTIC RUN",
    title: "Eight steps, in the order they execute",
    note: "The exact CLI sequence: perceive, listen, order, route, allocate, budget, approve, replan.",
    tools: ["agent.py --yes", "8 steps", "replan"],
  },
  {
    id: "world",
    n: "08",
    kicker: "WORKS ANYWHERE",
    title: "One point query, any point on Earth",
    note: "24 configured coordinates, one surveyed town, every template labelled as a template.",
    tools: ["24 points", "1 surveyed", "honest labels"],
  },
];
