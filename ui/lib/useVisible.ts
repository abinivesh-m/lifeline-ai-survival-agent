"use client";

import { useEffect, useRef, useState } from "react";

/**
 * True while the element is near the viewport.
 *
 * Six live WebGL contexts on one machine is a stutter waiting to happen, so
 * every section scene uses this to set `frameloop="never"` once it scrolls
 * away. The fixed background stays out of this: it is always on screen and
 * always expected to be moving.
 */
export function useVisible<T extends HTMLElement = HTMLDivElement>(
  rootMargin = "240px",
) {
  const ref = useRef<T>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => setVisible(entries[0]?.isIntersecting ?? false),
      { rootMargin },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [rootMargin]);

  return { ref, visible };
}
