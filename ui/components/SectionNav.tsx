"use client";

import { useEffect, useState } from "react";
import { SECTIONS } from "@/lib/sections";

/**
 * Sticky section rail. Sits directly under the fixed language bar so a judge
 * can jump from the hero to any feature in one click — and so it is always
 * obvious which of the eight sections is on screen.
 */
export default function SectionNav() {
  const [active, setActive] = useState(SECTIONS[0].id);

  useEffect(() => {
    const elements = SECTIONS.map((section) => document.getElementById(section.id)).filter(
      (element): element is HTMLElement => Boolean(element)
    );
    if (!elements.length || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: [0, 0.15, 0.4] }
    );

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  return (
    <nav
      aria-label="Sections"
      className="sticky top-[45px] z-40 hidden border-y border-line/70 bg-[#060d11]/90 backdrop-blur-xl md:block"
    >
      <div className="mx-auto flex w-full max-w-[1800px] items-center gap-1 overflow-x-auto px-5 py-1.5">
        <span className="mono mr-2 shrink-0 text-[8.5px] tracking-[0.18em] text-muted/60">
          SECTIONS
        </span>
        {SECTIONS.map((section) => {
          const on = section.id === active;
          return (
            <a
              key={section.id}
              href={`#${section.id}`}
              aria-current={on ? "true" : undefined}
              className={`group flex shrink-0 items-center gap-1.5 rounded border px-2 py-1 mono text-[9px] transition ${
                on
                  ? "border-teal/50 bg-teal/10 text-teal"
                  : "border-transparent text-muted hover:border-line hover:text-ink"
              }`}
            >
              <span className={`mono text-[8px] ${on ? "text-teal/70" : "text-muted/50"}`}>
                {section.n}
              </span>
              {section.kicker
                .toLowerCase()
                .replace(/\b\w/g, (letter) => letter.toUpperCase())}
            </a>
          );
        })}
        <a
          href="#world"
          className="ml-auto hidden shrink-0 rounded border border-amber/40 bg-amber/10 px-2 py-1 mono text-[9px] text-amber transition hover:bg-amber/20 lg:block"
        >
          30s TOUR →
        </a>
      </div>
    </nav>
  );
}
