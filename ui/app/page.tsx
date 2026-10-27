"use client";

import { motion } from "framer-motion";
import Lifegrid3D from "@/components/Lifegrid3D";
import DependencyGraph3D from "@/components/DependencyGraph3D";
import AStarMap3D from "@/components/AStarMap3D";
import BloodPanel from "@/components/BloodPanel";
import AllocatorDashboard from "@/components/AllocatorDashboard";
import OfflineProof3D from "@/components/OfflineProof3D";
import AgenticTimeline3D from "@/components/AgenticTimeline3D";
import WorldPanel from "@/components/WorldPanel";
import LanguageBar from "@/components/LanguageBar";
import SectionNav from "@/components/SectionNav";
import { useLocale } from "@/components/LocaleProvider";
import { COLORS, lifeline } from "@/lib/lifeline";
import { SECTIONS, type SectionMeta } from "@/lib/sections";

/**
 * Every feature lives in its own numbered room. Alternating background bands,
 * a top hairline and a left rule mean two sections can never read as one
 * continuous page — which is exactly what a live demo needs.
 */
function Section({
  meta,
  lede,
  children,
}: {
  meta: SectionMeta;
  lede?: string;
  children: React.ReactNode;
}) {
  const raised = Number(meta.n) % 2 === 0;

  return (
    <section
      id={meta.id}
      className={`relative scroll-mt-28 border-t border-line/70 ${
        raised ? "bg-[#08141b]/70" : "bg-transparent"
      }`}
    >
      <div className="mx-auto w-full max-w-[1800px] px-5 py-12">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.55 }}
          className="mb-6 grid gap-3 border-l-2 border-teal/40 pl-4 md:grid-cols-[auto_1fr_auto] md:items-start md:gap-5 md:pl-5"
        >
          <div className="mono text-[34px] font-bold leading-[0.8] text-teal/25 md:text-[44px]">
            {meta.n}
          </div>
          <div>
            <div className="mono text-[10px] tracking-[0.22em] text-teal">{meta.kicker}</div>
            <h2 className="mt-1.5 text-2xl font-semibold tracking-tight md:text-[28px]">
              {meta.title}
            </h2>
            {lede && (
              <p className="mt-2 max-w-3xl text-[13px] leading-relaxed text-muted">{lede}</p>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5 md:max-w-[300px] md:justify-end">
            {meta.tools.map((tool) => (
              <span
                key={tool}
                className="rounded border border-line/80 bg-black/40 px-2 py-0.5 mono text-[8.5px] tracking-[0.08em] text-muted"
              >
                {tool}
              </span>
            ))}
          </div>
        </motion.div>
        {children}
      </div>
    </section>
  );
}

export default function Page() {
  const { t } = useLocale();

  const stats = [
    { key: "lifegrid.blood", value: `${lifeline.organs.fuel_depot?.litres ?? 100} L`, note: t("lifegrid.fuel"), color: COLORS.teal },
    { key: "lifegrid.heart", value: `${lifeline.organs.hospital?.litres ?? 70} L`, note: t("lifegrid.runtime", { hours: lifeline.organs.hospital?.runtime_hours ?? 4 }), color: COLORS.blood },
    { key: "lifegrid.lungs", value: `${lifeline.organs.water_pump?.litres ?? 30} L`, note: t("lifegrid.feeder"), color: COLORS.lung },
    { key: "lifegrid.organs", value: `${lifeline.organs.shelters?.people ?? 200}`, note: t("lifegrid.nowater", { hours: lifeline.town.crisis?.expected_clear_hours ?? 6 }), color: COLORS.amber },
  ];

  return (
    <main className="min-h-screen bg-[#060d11] pb-10">
      <LanguageBar />

      {/* ---------------------------------------------------------------- hero */}
      <section className="relative min-h-[100vh] overflow-hidden pt-14">
        <video
          className="absolute inset-0 h-full w-full object-cover opacity-[0.22]"
          src="/videos/flood.mp4"
          autoPlay
          muted
          loop
          playsInline
          aria-hidden
        />
        <div className="absolute inset-0 bg-gradient-to-b from-[#060d11]/60 via-[#060d11]/80 to-[#060d11]" />
        <div className="scan absolute inset-0 opacity-40" />

        <div className="relative mx-auto grid w-full max-w-[1800px] items-center gap-6 px-5 py-8 lg:grid-cols-[1.05fr_1fr]">
          <div>
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7 }}
            >
              <div className="mono inline-flex items-center gap-2 rounded-full border border-teal/30 bg-teal/5 px-3 py-1 text-[10px] tracking-[0.18em] text-teal">
                <span className="h-1.5 w-1.5 rounded-full bg-teal" />
                {t("app.tagline").toUpperCase()}
              </div>

              <h1 className="mt-5 text-[40px] font-bold leading-[1.04] tracking-tight md:text-[62px]">
                The town is a body.
                <br />
                <span className="text-teal">100 L is its blood.</span>
              </h1>

              <p className="mt-4 max-w-xl text-[14.5px] leading-relaxed text-muted">
                A landslide blocks NH-544 at km 42. One health centre, 200 people in
                shelters, and 100 L of diesel decides whether the pumps keep turning.
                LIFELINE AI runs the town like an organ system: heart first, lungs
                second, and never a litre moved without a human saying yes.
              </p>

              <div className="mt-5 flex flex-wrap gap-2">
                {[
                  "fuel allocation only · no medical advice",
                  `${lifeline.locales.length} world languages`,
                  "real model calls, real ledger",
                  "runs offline on a 6 GB laptop",
                ].map((chip) => (
                  <span
                    key={chip}
                    className="rounded border border-line bg-black/40 px-2.5 py-1 mono text-[9.5px] text-muted"
                  >
                    {chip}
                  </span>
                ))}
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <a
                  href="#allocate"
                  className="rounded-md border border-teal bg-teal/15 px-4 py-2.5 text-[12.5px] font-bold text-teal transition hover:bg-teal/25"
                >
                  SEE THE ALLOCATION →
                </a>
                <a
                  href="#cascade"
                  className="rounded-md border border-line px-4 py-2.5 text-[12.5px] font-semibold text-muted transition hover:border-muted/60 hover:text-ink"
                >
                  WHY THE HEART COMES FIRST
                </a>
                <a
                  href="#contents"
                  className="rounded-md px-2 py-2.5 mono text-[10.5px] tracking-[0.12em] text-muted underline decoration-line underline-offset-4 transition hover:text-teal"
                >
                  ALL 8 SECTIONS ↓
                </a>
              </div>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.9, delay: 0.15 }}
            className="relative h-[440px] overflow-hidden rounded-2xl border border-line bg-[#050c10]/80 md:h-[520px]"
          >
            <Lifegrid3D />
          </motion.div>
        </div>

        <div className="relative mx-auto grid w-full max-w-[1800px] gap-2 px-5 pb-6 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <div key={stat.key} className="rounded-xl border border-line bg-panel/70 p-3.5">
              <div className="mono text-[9px] tracking-[0.18em]" style={{ color: stat.color }}>
                {t(stat.key)}
              </div>
              <div className="mt-1 flex items-baseline gap-2">
                <span className="text-2xl font-bold" style={{ color: stat.color }}>
                  {stat.value}
                </span>
                <span className="text-[10.5px] leading-tight text-muted">{stat.note}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <SectionNav />

      {/* ------------------------------------------------------------- contents */}
      <section id="contents" className="relative mx-auto w-full max-w-[1800px] scroll-mt-28 px-5 py-10">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="mono text-[10px] tracking-[0.22em] text-teal">
              CONTENTS · {SECTIONS.length} SECTIONS
            </div>
            <h2 className="mt-1.5 text-2xl font-semibold tracking-tight md:text-[28px]">
              Every feature gets its own room
            </h2>
            <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-muted">
              Nothing is stacked on top of anything else. Jump straight to a section, or
              follow the 30-second path a judge follows: dependency, route, allocation,
              world.
            </p>
          </div>
          <div className="mono hidden text-right text-[9px] leading-relaxed text-muted/70 md:block">
            <div>8 ROOMS · 1 AGENT</div>
            <div>NO FEATURE HIDDEN BEHIND A TAB</div>
          </div>
        </div>

        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {SECTIONS.map((section, position) => (
            <motion.a
              key={section.id}
              href={`#${section.id}`}
              initial={{ opacity: 0, y: 12 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4, delay: position * 0.03 }}
              className="group rounded-xl border border-line/80 bg-panel/50 p-3.5 transition hover:border-teal/50 hover:bg-panel"
            >
              <div className="flex items-baseline justify-between">
                <span className="mono text-[10px] text-teal/70">{section.n}</span>
                <span className="mono text-[8px] tracking-[0.14em] text-muted/60 transition group-hover:text-teal">
                  OPEN →
                </span>
              </div>
              <div className="mt-2 mono text-[8.5px] tracking-[0.16em] text-muted">
                {section.kicker}
              </div>
              <div className="mt-1 text-[12.5px] font-semibold leading-snug text-ink/90">
                {section.title}
              </div>
              <p className="mt-1.5 text-[10.5px] leading-relaxed text-muted">{section.note}</p>
            </motion.a>
          ))}
        </div>
      </section>

      {/* ------------------------------------------------------------- cascade */}
      <Section
        meta={SECTIONS[0]}
        lede="Four organs, one directed graph. Kahn's algorithm decides the order, and the order is the whole argument: fund anything below the heart first and the money is wasted."
      >
        <DependencyGraph3D />
      </Section>

      {/* --------------------------------------------------------------- route */}
      <Section
        meta={SECTIONS[1]}
        lede="A* with a binary heap over the real road graph. The blocked corridor is not a saving — it is an impossibility. Every percentage is measured against the 13.0 km detour an operator would actually take."
      >
        <AStarMap3D />
      </Section>

      {/* --------------------------------------------------------------- blood */}
      <Section
        meta={SECTIONS[2]}
        lede="Four deterministic calculations that exist before any model speaks: usable volume at 42 °C, lot provenance, fuel-limited runtime, and the same plan expressed in hours of life. Reproduce every figure with python blood.py --all."
      >
        <BloodPanel />
      </Section>

      {/* ------------------------------------------------------------ allocate */}
      <Section
        meta={SECTIONS[3]}
        lede="Segmentation, transcription, reasoning, validation, the credit ledger and the human gate, side by side. Every number below is read from an artefact in the repo, not typed into the page."
      >
        <AllocatorDashboard />
      </Section>

      {/* ---------------------------------------------------------- escalation */}
      <Section
        meta={SECTIONS[4]}
        lede="A single approval button is a single point of failure. Four tiers, each one logged to a sha256 hash chain so the record cannot be quietly rewritten."
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {lifeline.escalation.tiers.map((tier) => {
            const colours = [COLORS.teal, COLORS.amber, "#fb923c", COLORS.blood];
            const colour = colours[tier.tier - 1];
            return (
              <motion.div
                key={tier.tier}
                initial={{ opacity: 0, y: 14 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.45, delay: tier.tier * 0.06 }}
                className="relative overflow-hidden rounded-xl border bg-panel/70 p-4"
                style={{ borderColor: `${colour}44` }}
              >
                <div
                  className="absolute inset-x-0 top-0 h-[2px]"
                  style={{ background: `linear-gradient(90deg, transparent, ${colour}, transparent)` }}
                />
                <div className="flex items-baseline justify-between">
                  <span className="mono text-[10px]" style={{ color: colour }}>
                    TIER {tier.tier}
                  </span>
                  <span className="mono text-[9px] text-muted">{tier.window}</span>
                </div>
                <div className="mt-2 text-[15px] font-semibold">{tier.action}</div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-muted">{tier.detail}</p>
                <div className="mt-2.5 rounded border border-line/60 bg-black/30 px-2 py-1 mono text-[8.5px] text-muted">
                  {t(`gate.tier${tier.tier}`)}
                </div>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-3 grid gap-3 lg:grid-cols-[1.4fr_1fr]">
          <div className="rounded-xl border border-line bg-panel/60 p-4">
            <div className="mono text-[10px] tracking-[0.18em] text-muted">TIER 3 · DEGRADED PROFILE</div>
            <div className="mt-2 flex flex-wrap items-end gap-4">
              {[
                { label: t("lifegrid.heart"), value: lifeline.escalation.degraded.hospital, color: COLORS.blood },
                { label: t("lifegrid.lungs"), value: lifeline.escalation.degraded.water_pump, color: COLORS.lung },
                { label: "held reserve", value: lifeline.escalation.degraded._held_reserve, color: COLORS.teal },
              ].map((item) => (
                <div key={item.label}>
                  <div className="mono text-[9px]" style={{ color: item.color }}>
                    {item.label}
                  </div>
                  <div className="text-2xl font-bold" style={{ color: item.color }}>
                    {item.value} L
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-2 max-w-xl text-[11px] leading-relaxed text-muted">
              Less than the plan, never zero. Thirty litres stay in the depot because a
              second wave, a second town or a rescued convoy must not find it empty.
            </p>
          </div>

          <div className="rounded-xl border border-line bg-panel/60 p-4">
            <div className="mono text-[10px] tracking-[0.18em] text-muted">NOTIFICATIONS</div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
              Tier 2 and tier 4 compose SMS, WhatsApp and voice payloads in the reader's
              language. They are generated, translated and logged.
            </p>
            <div className="mt-2 rounded border border-amber/40 bg-amber/5 px-2 py-1.5 mono text-[9px] text-amber">
              DELIVERY: PENDING_CREDENTIALS
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-muted/80">
              No gateway is configured, so nothing here claims a message was sent.
            </p>
          </div>
        </div>
      </Section>

      {/* -------------------------------------------------------------- offline */}
      <Section
        meta={SECTIONS[5]}
        lede="The core — routing, topological order, the 70/30 validator, the ledger — runs on this laptop with the network off. Partner inference is shown for what it is: partner inference."
      >
        <OfflineProof3D />
      </Section>

      {/* ------------------------------------------------------------- timeline */}
      <Section
        meta={SECTIONS[6]}
        lede="The same sequence the CLI runs: perceive, listen, order, route, allocate, budget, approve, replan."
      >
        <AgenticTimeline3D />
      </Section>

      {/* ---------------------------------------------------------------- world */}
      <Section
        meta={SECTIONS[7]}
        lede="Built in Kottur because that is where the numbers are real. The same cascade exists in Manila, Jakarta, Nairobi and Khartoum — and the page says exactly which data is surveyed and which is a labelled template."
      >
        <WorldPanel />
      </Section>

      {/* --------------------------------------------------------------- footer */}
      <footer className="mx-auto mt-6 w-full max-w-[1800px] px-5">
        <div className="hairline mb-5" />
        <div className="grid gap-5 pb-8 md:grid-cols-4">
          <div>
            <div className="mono text-[11px] font-bold tracking-[0.2em] text-ink">LIFELINE AI</div>
            <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
              {t("world.scope")}.
            </p>
            <p className="mt-2 mono text-[9px] text-muted/70">
              Built in Kottur · Pollachi · Tamil Nadu · 642114
            </p>
          </div>
          <div>
            <div className="mono text-[9px] tracking-[0.18em] text-muted">MODELS</div>
            <ul className="mt-1.5 space-y-1 mono text-[9.5px] text-muted">
              <li>SAM 3.1 · eyes</li>
              <li>muse-voice-transcribe-1.0 · ears</li>
              <li>muse-wonder-1.0 · allocator</li>
              <li>muse-spark-open-1026 · partner</li>
            </ul>
          </div>
          <div>
            <div className="mono text-[9px] tracking-[0.18em] text-muted">DATA HONESTY</div>
            <ul className="mt-1.5 space-y-1 text-[10px] leading-relaxed text-muted">
              <li>Photos: Wikimedia, credited in CREDITS.json</li>
              <li>Voice: synthetic placeholder, labelled</li>
              <li>Masks &amp; transcripts: real API output</li>
              <li>Baseline: documented assumption</li>
            </ul>
          </div>
          <div>
            <div className="mono text-[9px] tracking-[0.18em] text-muted">SAFETY</div>
            <p className="mt-1.5 text-[10px] leading-relaxed text-muted">
              Diesel and water allocation only. No diagnosis, no dosing, no clinical
              advice. A human approves before anything is dispatched.
            </p>
            <p className="mt-2 mono text-[9px] text-muted/70">
              ledger ${lifeline.credit.spent_usd.toFixed(6)} / ${lifeline.credit.budget_usd}
            </p>
          </div>
        </div>
      </footer>
    </main>
  );
}

