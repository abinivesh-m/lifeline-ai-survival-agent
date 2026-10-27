"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import * as THREE from "three";
import { COLORS, ORDER_KEY, lifeline } from "@/lib/lifeline";
import { useVisible } from "@/lib/useVisible";
import { ClampDelta } from "./ClampDelta";
import { useLocale } from "./LocaleProvider";

const NODES = ["fuel_depot", "hospital", "water_pump", "shelters"] as const;
type NodeName = (typeof NODES)[number];

const POS: Record<NodeName, [number, number, number]> = {
  fuel_depot: [-3.9, 0.3, 0],
  hospital: [-1.3, 0.75, 0.35],
  water_pump: [1.3, 0, -0.2],
  shelters: [3.9, 0.55, 0.25],
};

const COLOR: Record<NodeName, string> = {
  fuel_depot: COLORS.teal,
  hospital: COLORS.blood,
  water_pump: COLORS.lung,
  shelters: COLORS.amber,
};

const HOURS: Record<NodeName, number> = {
  fuel_depot: Infinity,
  hospital: lifeline.organs.hospital?.runtime_hours ?? 4,
  water_pump: 6,
  shelters: 0,
};

function Edge({
  from,
  to,
  index,
  failing,
}: {
  from: NodeName;
  to: NodeName;
  index: number;
  failing: boolean;
}) {
  const dot = useRef<THREE.Mesh>(null);
  const a = new THREE.Vector3(...POS[from]);
  const b = new THREE.Vector3(...POS[to]);
  const mid = a.clone().lerp(b, 0.5);
  mid.z += 0.55;

  const curve = useMemo(
    () => new THREE.CatmullRomCurve3([a, mid, b]),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [from, to],
  );

  const geometry = useMemo(() => new THREE.TubeGeometry(curve, 48, 0.014, 8, false), [curve]);

  useFrame((state) => {
    if (!dot.current) return;
    const phase = failing ? 0 : (state.clock.elapsedTime * 0.34 + index * 0.18) % 1;
    const point = curve.getPointAt(phase);
    dot.current.position.copy(point);
    const material = dot.current.material as THREE.MeshBasicMaterial;
    material.opacity = failing ? 0.12 : 0.85;
  });

  return (
    <group>
      <mesh geometry={geometry}>
        <meshStandardMaterial
          color={failing ? "#31505c" : COLOR[to]}
          emissive={failing ? "#000000" : COLOR[to]}
          emissiveIntensity={0.5}
          transparent
          opacity={0.5}
        />
      </mesh>
      <mesh ref={dot}>
        <sphereGeometry args={[0.055, 12, 12]} />
        <meshBasicMaterial color={failing ? "#3d5c66" : "#eafffb"} transparent opacity={0.85} />
      </mesh>
    </group>
  );
}

function Node({
  name,
  failed,
  dead,
  selected,
  onSelect,
  t,
  locale,
}: {
  name: NodeName;
  failed: boolean;
  dead: boolean;
  selected: boolean;
  onSelect: () => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  locale: string;
}) {
  const ref = useRef<THREE.Group>(null);
  const colour = failed ? "#5c2b2b" : COLOR[name];
  const organ = lifeline.organs[name];
  // shelters hold people, not litres - showing "0 L" there was wrong
  const litres = name === "shelters" ? (organ?.people ?? 200) : (organ?.litres ?? 0);

  useFrame((state) => {
    if (!ref.current) return;
    const bob = Math.sin(state.clock.elapsedTime * 1.2 + POS[name][0]) * 0.045;
    ref.current.position.y = POS[name][1] + bob;
    const target = selected ? 1.14 : 1;
    ref.current.scale.lerp(new THREE.Vector3(target, target, target), 0.08);
  });

  return (
    <group
      ref={ref}
      position={POS[name]}
      onClick={onSelect}
      onPointerOver={(event) => {
        event.stopPropagation();
        document.body.style.cursor = "pointer";
      }}
      onPointerOut={() => {
        document.body.style.cursor = "auto";
      }}
    >
      <group rotation={[0.08, name === "fuel_depot" ? 0.34 : -0.3, 0.02]}>
        <mesh>
          <boxGeometry args={[1.15, 0.9, 0.9]} />
          <meshStandardMaterial
            color={colour}
            emissive={colour}
            emissiveIntensity={dead ? 0.05 : failed ? 0.25 : selected ? 0.85 : 0.4}
            roughness={0.3}
            metalness={0.35}
            transparent
            opacity={dead ? 0.45 : 1}
          />
        </mesh>
        <lineSegments>
          <edgesGeometry args={[new THREE.BoxGeometry(1.16, 0.91, 0.91)]} />
          <lineBasicMaterial color={dead ? "#4a5c66" : "#eafffb"} transparent opacity={0.32} />
        </lineSegments>
      </group>

      <Html center distanceFactor={5.5} position={[0, 0.86, 0]} zIndexRange={[10, 0]}>
        <div
          className={`whitespace-nowrap rounded border px-1.5 py-0.5 text-center backdrop-blur-sm ${
            failed ? "border-blood/60 bg-black/70" : "border-white/15 bg-black/55"
          }`}
          style={{ color: failed ? COLORS.blood : COLOR[name] }}
        >
          <div className="mono text-[8px] tracking-[0.14em]">{t(ORDER_KEY[name])}</div>
          <div className={`text-[10px] font-semibold ${locale === "ar" ? "ar" : ""}`}>
            {litres}
            {name === "shelters" ? "" : " L"}
          </div>
        </div>
      </Html>

      <Html center distanceFactor={5.5} position={[0, -0.78, 0]} zIndexRange={[10, 0]}>
        <div className="whitespace-nowrap rounded bg-black/55 px-1 py-0.5 mono text-[7.5px] text-muted">
          {dead
            ? "no service"
            : name === "fuel_depot"
              ? "source"
              : name === "shelters"
                ? `${HOURS.shelters} h water`
                : `${HOURS[name]} h`}
        </div>
      </Html>
    </group>
  );
}

export default function DependencyGraph3D() {
  const { t, code } = useLocale();
  const [selected, setSelected] = useState<NodeName>("hospital");
  const [failure, setFailure] = useState<NodeName | null>(null);
  const [stage, setStage] = useState(0);

  // cascade: hospital fails, then the pump, then the shelters
  useEffect(() => {
    if (!failure) {
      setStage(0);
      return;
    }
    const timers = [
      setTimeout(() => setStage(1), 700),
      setTimeout(() => setStage(2), 1500),
      setTimeout(() => setStage(3), 2300),
    ];
    return () => timers.forEach(clearTimeout);
  }, [failure]);

  const isDead = (name: NodeName) => {
    if (!failure) return false;
    const rank = NODES.indexOf(name);
    const from = NODES.indexOf(failure);
    return rank > from && stage >= rank - from;
  };

  const order = lifeline.graph.order as NodeName[];
  const people = lifeline.graph.cascade.people_affected;
  const { ref: frameRef, visible } = useVisible<HTMLDivElement>();

  return (
    <div className="grid gap-4 lg:grid-cols-[1.55fr_1fr]">
      <div
        ref={frameRef}
        className="relative h-[420px] overflow-hidden rounded-xl border border-line bg-[#071016]"
      >
        <Canvas
          frameloop={visible ? "always" : "never"}
          dpr={[1, 1.6]}
          camera={{ position: [0, 1.4, 9.4], fov: 40 }}
        >
          <ClampDelta />
          <ambientLight intensity={0.7} />
          <pointLight position={[-4, 4, 5]} intensity={22} color={COLORS.teal} />
          <pointLight position={[4, -2, 4]} intensity={16} color={COLORS.blood} />
          <fog attach="fog" args={["#071016", 10, 19]} />

          {lifeline.graph.edges.map(([from, to], index) => {
            const source = from as NodeName;
            const target = to as NodeName;
            return (
              <Edge
                key={`${from}-${to}`}
                from={source}
                to={target}
                index={index}
                failing={Boolean(failure) && isDead(target)}
              />
            );
          })}

          {NODES.map((name) => (
            <Node
              key={name}
              name={name}
              failed={failure === name}
              dead={isDead(name)}
              selected={selected === name}
              onSelect={() => setSelected(name)}
              t={t}
              locale={code}
            />
          ))}

          <OrbitControls
            enablePan={false}
            enableZoom
            minDistance={7.5}
            maxDistance={12}
            maxPolarAngle={Math.PI * 0.58}
            minPolarAngle={Math.PI * 0.38}
            // keep the four organs spread across the frame: without a hard
            // azimuth limit the orbit reaches an edge-on angle and the graph
            // collapses into a single vertical line of labels.
            minAzimuthAngle={-0.55}
            maxAzimuthAngle={0.55}
          />
        </Canvas>

        <div className="pointer-events-none absolute left-4 top-4 mono text-[9px] tracking-[0.2em] text-muted">
          KAHN TOPOLOGICAL ORDER · {order.join(" → ")}
        </div>
        <div className="absolute bottom-3 right-3 rounded border border-line bg-black/55 px-2 py-1 mono text-[9px] text-muted">
          click a node · drag to orbit
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="rounded-xl border border-line bg-panel/80 p-4">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">SELECTED ORGAN</div>
          <div className="mt-1 text-lg font-semibold" style={{ color: COLOR[selected] }}>
            {t(ORDER_KEY[selected])}
          </div>
          <div className="mt-1 text-[12px] leading-relaxed text-muted">
            {selected === "fuel_depot" && "100 L at the depot on NH-544 km 42. Everything downstream is fed from here."}
            {selected === "hospital" &&
              "Priority 1. 70 L keeps the ICU, the vaccine cold chain and the pump feeder alive for 4 hours."}
            {selected === "water_pump" && "Priority 2 and electrically downstream: 30 L only reaches the pump if the hospital has power."}
            {selected === "shelters" && "Priority 3. 200 people, 3 shelters, 12,000 L of water needed today, no water for 6 hours."}
          </div>
        </div>

        <div className="rounded-xl border border-line bg-panel/80 p-4">
          <div className="flex items-center justify-between">
            <div className="mono text-[10px] tracking-[0.18em] text-muted">CASCADE TEST</div>
            <span className="mono text-[9px] text-muted">{stage}/3</span>
          </div>
          <p className="mt-1.5 text-[12px] leading-relaxed text-muted">
            Fail the heart and the lungs go with it, because the pump runs off the
            hospital feeder. This is the dependency the allocation order exists to
            respect.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => setFailure(failure ? null : "hospital")}
              className={`flex-1 rounded-md border px-3 py-2 text-[12px] font-semibold transition ${
                failure
                  ? "border-teal/60 bg-teal/10 text-teal hover:bg-teal/20"
                  : "border-blood/60 bg-blood/10 text-blood hover:bg-blood/20"
              }`}
            >
              {failure ? "RESET" : "FAIL THE HEART"}
            </button>
          </div>
          {failure && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-3 rounded border border-blood/40 bg-blood/5 p-2.5"
            >
              <div className="mono text-[10px] text-blood">
                CASCADE · {stage >= 3 ? "complete" : "propagating"}
              </div>
              <div className="mt-1 text-[12px] text-ink">
                {stage >= 3
                  ? `${people} people lose water. The pump cannot run without the heart.`
                  : "Warning propagating downstream…"}
              </div>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
