"use client";

import { useThree } from "@react-three/fiber";
import { useEffect } from "react";

/**
 * Keeps simulated motion from teleporting after the scene was paused.
 *
 * Section scenes switch to `frameloop="never"` while off screen, and the
 * browser also stops calling rAF in a background tab. The first frame back
 * would otherwise report the whole gap as its delta and every accumulation
 * (`t += delta * speed`) would jump. Clamping is invisible at 60 fps and
 * keeps the resume seamless.
 */
export function ClampDelta({ max = 0.05 }: { max?: number }) {
  const clock = useThree((state) => state.clock);

  useEffect(() => {
    const getDelta = clock.getDelta.bind(clock);
    const clamped = () => Math.min(getDelta(), max);
    clock.getDelta = clamped;
    return () => {
      clock.getDelta = getDelta;
    };
  }, [clock, max]);

  return null;
}
