"use client";

import { motion } from "framer-motion";
import { lifeline } from "@/lib/lifeline";
import { useLocale } from "./LocaleProvider";

export default function LanguageBar() {
  const { code, setCode, locale } = useLocale();

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-line/70 bg-[#060d11]/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1800px] flex-wrap items-center gap-x-4 gap-y-2 px-5 py-2.5">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-teal opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-teal" />
          </span>
          <span className="mono text-[11px] font-bold tracking-[0.22em] text-ink">LIFELINE AI</span>
          <span className="hidden mono text-[9px] tracking-[0.16em] text-muted sm:inline">
            TOWN SURVIVAL AGENT
          </span>
        </div>

        <div className="ml-auto flex items-center gap-1">
          {lifeline.locales.map((item) => {
            const on = item.code === code;
            return (
              <button
                key={item.code}
                onClick={() => setCode(item.code)}
                aria-pressed={on}
                title={`${item.language} (${item.code})`}
                className={`relative rounded px-1.5 py-1 text-[10.5px] transition ${
                  on ? "text-teal" : "text-muted hover:text-ink"
                } ${item.code === "ar" ? "ar" : ""}`}
              >
                {on && (
                  <motion.span
                    layoutId="lang-pill"
                    className="absolute inset-0 rounded border border-teal/50 bg-teal/10"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <span className="relative">{item.native}</span>
              </button>
            );
          })}
        </div>

        <div className="mono hidden items-center gap-3 text-[9px] text-muted lg:flex">
          <span>{locale.code.toUpperCase()}</span>
          <span className="h-3 w-px bg-line" />
          <a
            href="http://127.0.0.1:8765"
            target="_blank"
            rel="noreferrer"
            className="transition hover:text-teal"
          >
            LIVE RUN ↗
          </a>
          <span className="h-3 w-px bg-line" />
          <span>KOTTUR · 11.0168 N 76.9558 E</span>
        </div>
      </div>
    </header>
  );
}
