"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { COLORS, lifeline } from "@/lib/lifeline";
import { ClampDelta } from "./ClampDelta";

/* Palette: lifeline colours where they exist, the three extra accents the
   scene needs (router red / bypass green / flow orange) declared once. */
const GRID = "#94a3b8";
const RED = "#ef4444";
const GREEN = "#22c55e";
const ORANGE = "#fb923c";
const PURPLE = "#a78bfa";
const BG = "#0a0a0f";

type NodeSpec = {
  id: string;
  title: string;
  sub?: string;
  position: [number, number, number];
  color: string;
  beat?: boolean;
  pulse?: boolean;
  labelOffset?: [number, number, number];
};

const BLOOD_L = lifeline.organs.fuel_depot?.litres ?? 100;
const HEART_L = lifeline.organs.hospital?.litres ?? 70;
const LUNGS_L = lifeline.organs.water_pump?.litres ?? 30;
const ORGANS_N = lifeline.organs.shelters?.people ?? 200;
const ROUTE_KM = lifeline.route?.distance_km ?? 7.8;
const SAVE_PCT = lifeline.route?.saving?.percent ?? 40;

const NODES: NodeSpec[] = [
  {
    id: "blood",
    title: `BLOOD ${BLOOD_L}L`,
    sub: "DEPOT · FUEL",
    position: [-4.2, 0.55, 0.5],
    color: COLORS.teal,
  },
  {
    id: "heart",
    title: `HEART ${HEART_L}L`,
    sub: "HOSPITAL · 4H",
    position: [-1.9, 0.55, 0.1],
    color: PURPLE,
    beat: true,
  },
  {
    id: "lungs",
    title: `LUNGS ${LUNGS_L}L`,
    sub: "WATER PUMP",
    position: [0.5, 0.55, -0.2],
    color: COLORS.teal,
  },
  {
    id: "organs",
    title: `ORGANS ${ORGANS_N}`,
    sub: "SHELTERS",
    position: [3.3, 0.55, 0.6],
    color: COLORS.amber,
  },
  {
    id: "blocked",
    title: "NH-544 BLOCKED",
    sub: "km 42 · 5x5 RISK / TDR LOG",
    position: [2.0, 0.42, 2.0],
    color: RED,
    pulse: true,
    labelOffset: [-1.05, -0.5, 0.3],
  },
  {
    id: "bypass",
    title: `A* ${ROUTE_KM} km · ${SAVE_PCT}% SAVE`,
    sub: "TRACEABILITY MATRIX / B3",
    position: [4.0, 0.42, 3.0],
    color: GREEN,
    labelOffset: [0.95, 0.7, 0],
  },
];

const byId = Object.fromEntries(NODES.map((node) => [node.id, node]));
const at = (id: string, y?: number): [number, number, number] => {
  const [x, cy, z] = byId[id].position;
  return [x, y ?? cy, z];
};

/* ------------------------------------------------------------------ grid */

function useGrid() {
  return useMemo(() => {
    const span = 7;
    const step = 0.5;
    const minor: number[] = [];
    const major: number[] = [];

    for (let value = -span; value <= span; value += step) {
      const target = Math.abs(value % 2.5) < 0.001 ? major : minor;
      target.push(-span, 0, value, span, 0, value);
      target.push(value, 0, -span, value, 0, span);
    }

    const build = (points: number[]) => {
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
      return geometry;
    };

    return { minor: build(minor), major: build(major) };
  }, []);
}

/* --------------------------------------------------------------- nodes */

function Diamond({ node }: { node: NodeSpec }) {
  const core = useRef<THREE.Group>(null);
  const halo = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    if (core.current) {
      const beat = node.beat ? 0.8 + 0.2 * (1 + Math.sin(t * 3.4)) : 1;
      const pulse = node.pulse ? 1 + Math.sin(t * 4.2) * 0.08 : 1;
      core.current.scale.setScalar(beat * pulse);
    }
    if (halo.current) {
      const material = halo.current.material as THREE.MeshBasicMaterial;
      material.opacity = node.pulse
        ? 0.06 + 0.09 * (0.5 + 0.5 * Math.sin(t * 4.2))
        : 0.12;
    }
  });

  const [x, y, z] = node.position;

  return (
    <group>
      {/* blueprint stem from the grid to the floating node */}
      <Line
        points={[
          [x, 0.001, z],
          [x, y - 0.16, z],
        ]}
        color={node.color}
        lineWidth={0.7}
        transparent
        opacity={0.22}
      />

      <group position={node.position}>
        <group ref={core}>
          <mesh>
            <octahedronGeometry args={[0.19, 0]} />
            <meshStandardMaterial
              color={node.color}
              emissive={node.color}
              emissiveIntensity={node.pulse ? 1.1 : 1.4}
              flatShading
              roughness={0.35}
              metalness={0.15}
            />
          </mesh>
          <mesh scale={1.35}>
            <octahedronGeometry args={[0.19, 0]} />
            <meshBasicMaterial
              color={node.color}
              wireframe
              transparent
              opacity={0.3}
              depthWrite={false}
            />
          </mesh>
        </group>

        {/* additive shell instead of a post-process bloom: no extra package */}
        <mesh ref={halo} scale={2.0}>
          <sphereGeometry args={[0.19, 12, 12]} />
          <meshBasicMaterial
            color={node.color}
            transparent
            opacity={0.12}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>

        <Html
          center
          position={node.labelOffset ?? [0, 0.5, 0]}
          zIndexRange={[12, 0]}
          style={{ pointerEvents: "none" }}
        >
          <div className="w-max whitespace-nowrap text-center">
            <div
              className="mono text-[8.5px] font-semibold tracking-[0.12em]"
              style={{ color: node.color, textShadow: `0 0 8px ${node.color}55` }}
            >
              {node.title}
            </div>
            {node.sub && (
              <div className="mono mt-0.5 text-[6.5px] tracking-[0.14em] text-ink/60">
                {node.sub}
              </div>
            )}
          </div>
        </Html>
      </group>
    </group>
  );
}

/* ------------------------------------------------------------- particles */

function Flow({
  from,
  to,
  count = 14,
  color = "#ffffff",
  speed = 0.18,
}: {
  from: [number, number, number];
  to: [number, number, number];
  count?: number;
  color?: string;
  speed?: number;
}) {
  const points = useRef<THREE.Points>(null);
  const phases = useMemo(
    () => Array.from({ length: count }, (_, index) => index / count),
    [count]
  );
  const positions = useMemo(() => new Float32Array(count * 3), [count]);

  useFrame(({ clock }) => {
    const attribute = points.current?.geometry.getAttribute("position") as
      | THREE.BufferAttribute
      | undefined;
    if (!attribute) return;

    const array = attribute.array as Float32Array;
    const t0 = clock.getElapsedTime();
    for (let index = 0; index < count; index += 1) {
      const t = (t0 * speed + phases[index]) % 1;
      array[index * 3] = from[0] + (to[0] - from[0]) * t;
      array[index * 3 + 1] = from[1] + (to[1] - from[1]) * t;
      array[index * 3 + 2] = from[2] + (to[2] - from[2]) * t;
    }
    attribute.needsUpdate = true;
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.055}
        color={color}
        transparent
        opacity={0.9}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/* ------------------------------------------------------- drifting dots */

function DriftingDots({ count = 20 }: { count?: number }) {
  const points = useRef<THREE.Points>(null);

  const { positions, colors, velocities } = useMemo(() => {
    const position = new Float32Array(count * 3);
    const colour = new Float32Array(count * 3);
    const velocity = new Float32Array(count * 3);
    const palette = [RED, PURPLE, COLORS.teal];

    for (let index = 0; index < count; index += 1) {
      position[index * 3] = (Math.random() - 0.5) * 11;
      position[index * 3 + 1] = 0.25 + Math.random() * 2.4;
      position[index * 3 + 2] = (Math.random() - 0.5) * 8;

      const swatch = new THREE.Color(palette[index % palette.length]);
      colour[index * 3] = swatch.r;
      colour[index * 3 + 1] = swatch.g;
      colour[index * 3 + 2] = swatch.b;

      velocity[index * 3] = (Math.random() - 0.5) * 0.05;
      velocity[index * 3 + 1] = 0.02 + Math.random() * 0.05;
      velocity[index * 3 + 2] = (Math.random() - 0.5) * 0.05;
    }

    return { positions: position, colors: colour, velocities: velocity };
  }, [count]);

  useFrame((_, delta) => {
    const attribute = points.current?.geometry.getAttribute("position") as
      | THREE.BufferAttribute
      | undefined;
    if (!attribute) return;
    const array = attribute.array as Float32Array;

    for (let index = 0; index < count; index += 1) {
      array[index * 3] += velocities[index * 3] * delta;
      array[index * 3 + 1] += velocities[index * 3 + 1] * delta;
      array[index * 3 + 2] += velocities[index * 3 + 2] * delta;

      if (array[index * 3 + 1] > 2.9) {
        array[index * 3] = (Math.random() - 0.5) * 11;
        array[index * 3 + 1] = 0.2;
        array[index * 3 + 2] = (Math.random() - 0.5) * 8;
      }
    }
    attribute.needsUpdate = true;
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.07}
        vertexColors
        transparent
        opacity={0.75}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/* ----------------------------------------------------------- the scene */

function Rig() {
  const { camera } = useThree();
  useEffect(() => {
    camera.lookAt(0, 0.6, 0);
  }, [camera]);
  return null;
}

function Scene({ drift }: { drift: boolean }) {
  const world = useRef<THREE.Group>(null);
  const grid = useGrid();

  useFrame((_, delta) => {
    if (!drift || !world.current) return;
    world.current.rotation.y += 0.0005 * Math.min(delta, 0.05) * 60;
  });

  return (
    <>
      <fog attach="fog" args={[BG, 16, 34]} />
      <ambientLight intensity={1.1} />
      <directionalLight position={[5, 8, 6]} intensity={1.3} />
      <pointLight position={[-3, 2, 1]} intensity={6} distance={9} color={COLORS.teal} />
      <pointLight position={[3, 2, 2]} intensity={5} distance={9} color={COLORS.amber} />

      <group ref={world} position={[0, -0.9, 0]}>
        <lineSegments geometry={grid.minor}>
          <lineBasicMaterial color={GRID} transparent opacity={0.55} />
        </lineSegments>
        <lineSegments geometry={grid.major}>
          <lineBasicMaterial color={GRID} transparent opacity={0.95} />
        </lineSegments>

        {/* fuel cascade: blood -> heart -> lungs -> organs */}
        {[
          ["blood", "heart"],
          ["heart", "lungs"],
          ["lungs", "organs"],
        ].map(([a, b]) => (
          <group key={`${a}-${b}`}>
            <Line
              points={[at(a), at(b)]}
              color={ORANGE}
              lineWidth={1.2}
              transparent
              opacity={0.7}
            />
            <Flow from={at(a)} to={at(b)} count={14} color="#ffffff" speed={0.18} />
          </group>
        ))}

        {/* the corridor that cannot be driven */}
        <Line
          points={[at("lungs"), at("organs")]}
          color={RED}
          lineWidth={1}
          dashed
          dashSize={0.16}
          gapSize={0.12}
          transparent
          opacity={0.55}
        />

        {/* the route A* actually found */}
        <Line
          points={[at("lungs"), at("bypass"), at("organs")]}
          color={GREEN}
          lineWidth={1.2}
          transparent
          opacity={0.55}
        />
        <Flow from={at("lungs")} to={at("bypass")} count={8} color={GREEN} speed={0.22} />
        <Flow from={at("bypass")} to={at("organs")} count={8} color={GREEN} speed={0.22} />

        {NODES.map((node) => (
          <Diamond key={node.id} node={node} />
        ))}

        {/* heartbeat and blocked-corridor echoes on the floor */}
        <GroundPulse at={at("heart")} color={PURPLE} speed={0.5} />
        <GroundPulse at={at("blocked")} color={RED} speed={0.85} reach={1.1} />

        <DriftingDots count={20} />
      </group>
    </>
  );
}

/* ------------------------------------------------------- ground pulses */

function GroundPulse({
  at,
  color,
  speed = 0.45,
  reach = 1.4,
}: {
  at: [number, number, number];
  color: string;
  speed?: number;
  reach?: number;
}) {
  const ring = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    const mesh = ring.current;
    if (!mesh) return;
    const t = (clock.getElapsedTime() * speed) % 1;
    mesh.scale.setScalar(0.25 + t * reach);
    const material = mesh.material as THREE.MeshBasicMaterial;
    material.opacity = (1 - t) * 0.22;
  });

  return (
    <mesh ref={ring} position={[at[0], 0.012, at[2]]} rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[0.86, 1, 48]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.2}
        side={THREE.DoubleSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

/* -------------------------------------------------------------- export */

export default function RunningGridBackground() {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = () => setReduced(query.matches);
    query.addEventListener?.("change", onChange);
    return () => query.removeEventListener?.("change", onChange);
  }, []);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="absolute inset-0 opacity-[0.15]">
        <Canvas
          dpr={[1, 1.5]}
          camera={{ position: [9.5, 7.5, 12.5], fov: 36, near: 0.1, far: 60 }}
          gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
          style={{ pointerEvents: "none" }}
        >
          <ClampDelta />
          <Rig />
          <Scene drift={!reduced} />
        </Canvas>
      </div>

      {/* vignette: keeps the grid dense in the middle, invisible at the edges */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_60%,transparent_0%,rgba(6,13,17,0.25)_55%,rgba(6,13,17,0.78)_100%)]" />
      {/* faint teal floor glow, so the grid reads as a horizon rather than a texture */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_100%,rgba(45,212,191,0.05),transparent_55%)]" />
    </div>
  );
}
