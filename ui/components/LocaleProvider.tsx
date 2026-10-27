"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { lifeline } from "@/lib/lifeline";

type Ctx = {
  code: string;
  setCode: (code: string) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  dir: "ltr" | "rtl";
  locale: { code: string; native: string; language: string; dir: string };
};

const LocaleContext = createContext<Ctx | null>(null);

const FALLBACK: Record<string, string> = lifeline.messages["en"];

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [code, setCodeState] = useState("en");

  // Remember the choice, but never block first paint on localStorage.
  useEffect(() => {
    const saved = window.localStorage.getItem("lifeline.locale");
    if (saved && lifeline.messages[saved]) setCodeState(saved);
  }, []);

  const setCode = useCallback((next: string) => {
    setCodeState(next);
    document.documentElement.lang = next;
    document.documentElement.dir = next === "ar" ? "rtl" : "ltr";
    try {
      window.localStorage.setItem("lifeline.locale", next);
    } catch {
      /* private mode, ignore */
    }
  }, []);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      const table = lifeline.messages[code] ?? FALLBACK;
      let out = table[key] ?? FALLBACK[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          out = out.replaceAll(`{${k}}`, String(v));
        }
      }
      return out;
    },
    [code],
  );

  const value = useMemo<Ctx>(() => {
    const locale =
      lifeline.locales.find((l) => l.code === code) ?? lifeline.locales[0];
    return {
      code,
      setCode,
      t,
      dir: code === "ar" ? "rtl" : "ltr",
      locale,
    };
  }, [code, setCode, t]);

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const ctx = useContext(LocaleContext);
  if (!ctx) throw new Error("useLocale must be used inside LocaleProvider");
  return ctx;
}
