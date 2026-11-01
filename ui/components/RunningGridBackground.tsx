"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Html, Line } from "@react-three/drei";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { COLORS, lifeline } from "@/lib/lifeline";
import { ClampDelta } from "./ClampDelta";

/* ------------------------------------------------------------------ palette */
const GRID_COLOR = "#0ea5e9";
const GRID_DEEP = "#042f2e";
const RED = "#ef4444";
const GREEN = "#10b981";
const ORANGE = "#f97316";
const PURPLE = "#c084fc";
const TEAL = "#2dd4bf";
const AMBER = "#fbbf24";
const BG = "#04090d";

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
    position: [-4.6, 0.75, 0.4],
    color: TEAL,
  },
  {
    id: "heart",
    title: `HEART ${HEART_L}L`,
    sub: "HOSPITAL · 4H",
    position: [-1.8, 0.85, 0.1],
    color: PURPLE,
    beat: true,
  },
  {
    id: "lungs",
    title: `LUNGS ${LUNGS_L}L`,
    sub: "WATER PUMP",
    position: [1.1, 0.75, -0.3],
    color: TEAL,
  },
  {
    id: "organs",
    title: `ORGANS ${ORGANS_N}`,
    sub: "SHELTERS",
    position: [4.2, 0.75, 0.6],
    color: AMBER,
  },
  {
    id: "blocked",
    title: "NH-544 BLOCKED",
    sub: "km 42 · 5x5 RISK / TDR LOG",
    position: [2.2, 0.55, 2.2],
    color: RED,
    pulse: true,
    labelOffset: [-1.05, -0.5, 0.3],
  },
  {
    id: "bypass",
    title: `A* ${ROUTE_KM} km · ${SAVE_PCT}% SAVE`,
    sub: "TRACEABILITY MATRIX / B3",
    position: [4.4, 0.55, 3.2],
    color: GREEN,
    labelOffset: [0.95, 0.7, 0],
  },
];

const byId = Object.fromEntries(NODES.map((node) => [node.id, node]));
const at = (id: string, y?: number): [number, number, number] => {
  const [x, cy, z] = byId[id].position;
  return [x, y ?? cy, z];
};

/* ------------------------------------------------ interactive cyber terrain */

function UndulatingTerrain({ mousePos }: { mousePos: React.MutableRefObject<{ x: number; y: number }> }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const segments = 44;
  const size = 26;

  const originalPositions = useMemo(() => {
    const geom = new THREE.PlaneGeometry(size, size, segments, segments);
    return new Float32Array(geom.attributes.position.array);
  }, []);

  useFrame(({ clock }) => {
    const mesh = meshRef.current;
    if (!mesh) return;

    const attr = mesh.geometry.attributes.position as THREE.BufferAttribute;
    const pos = attr.array as Float32Array;
    const t = clock.getElapsedTime() * 0.85;

    // Convert mouse screen coordinates to approximate 3D ground world range
    const mx = mousePos.current.x * 6;
    const my = -mousePos.current.y * 6;

    const vertexCount = (segments + 1) * (segments + 1);
    for (let i = 0; i < vertexCount; i++) {
      const idx = i * 3;
      const ox = originalPositions[idx];
      const oy = originalPositions[idx + 1];

      // Base undulating ripples
      const wave1 = Math.sin(ox * 0.35 + t * 1.1) * Math.cos(oy * 0.35 + t * 0.9) * 0.28;
      const wave2 = Math.sin((ox + oy) * 0.2 + t * 0.6) * 0.16;

      // Interactive mouse ripple: elevates dynamically near cursor
      const dx = ox - mx;
      const dy = oy - my;
      const distSq = dx * dx + dy * dy;
      const mouseInfluence = Math.exp(-distSq / 14) * 0.65;

      pos[idx + 2] = wave1 + wave2 + mouseInfluence;
    }

    attr.needsUpdate = true;
  });

  return (
    <group position={[0, -0.95, 0]} rotation={[-Math.PI / 2, 0, 0]}>
      <mesh ref={meshRef}>
        <planeGeometry args={[size, size, segments, segments]} />
        <meshStandardMaterial
          color={GRID_DEEP}
          emissive={GRID_COLOR}
          emissiveIntensity={0.25}
          wireframe
          transparent
          opacity={0.42}
          roughness={0.6}
          metalness={0.2}
        />
      </mesh>
    </group>
  );
}

/* ------------------------------------------------ interactive mouse light */

function InteractiveMouseLight({ mousePos }: { mousePos: React.MutableRefObject<{ x: number; y: number }> }) {
  const lightRef = useRef<THREE.PointLight>(null);

  useFrame(() => {
    if (!lightRef.current) return;
    const targetX = mousePos.current.x * 7;
    const targetZ = -mousePos.current.y * 5 + 1;
    lightRef.current.position.x += (targetX - lightRef.current.position.x) * 0.1;
    lightRef.current.position.z += (targetZ - lightRef.current.position.z) * 0.1;
  });

  return (
    <pointLight
      ref={lightRef}
      position={[0, 1.2, 0]}
      color={TEAL}
      intensity={7}
      distance={11}
      decay={2}
    />
  );
}

/* ------------------------------------------------ kinetic orbital node */

function KineticNode({ node }: { node: NodeSpec }) {
  const groupRef = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);
  const ring1Ref = useRef<THREE.Mesh>(null);
  const ring2Ref = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    if (coreRef.current) {
      coreRef.current.rotation.y = t * 0.8;
      coreRef.current.rotation.x = t * 0.4;
      const beat = node.beat ? 0.82 + 0.28 * Math.pow(Math.sin(t * 3.4), 2) : 1;
      const pulse = node.pulse ? 1 + Math.sin(t * 4.2) * 0.14 : 1;
      const hoverScale = hovered ? 1.35 : 1;
      coreRef.current.scale.setScalar(beat * pulse * hoverScale);
    }

    if (ring1Ref.current) {
      ring1Ref.current.rotation.x = t * 1.2;
      ring1Ref.current.rotation.y = t * 0.7;
    }
    if (ring2Ref.current) {
      ring2Ref.current.rotation.z = -t * 1.0;
      ring2Ref.current.rotation.y = -t * 0.5;
    }
  });

  const [x, y, z] = node.position;

  return (
    <group ref={groupRef}>
      {/* Vertical beam connecting to terrain */}
      <Line
        points={[
          [x, -0.95, z],
          [x, y - 0.2, z],
        ]}
        color={node.color}
        lineWidth={1.2}
        transparent
        opacity={0.35}
      />

      <group
        position={node.position}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        {/* Central Core Octahedron */}
        <mesh ref={coreRef}>
          <octahedronGeometry args={[0.22, 0]} />
          <meshStandardMaterial
            color={node.color}
            emissive={node.color}
            emissiveIntensity={hovered ? 2.5 : node.pulse ? 1.6 : 1.3}
            roughness={0.2}
            metalness={0.8}
          />
        </mesh>

        {/* Inner Gyro Ring */}
        <mesh ref={ring1Ref}>
          <torusGeometry args={[0.34, 0.012, 16, 32]} />
          <meshBasicMaterial
            color={node.color}
            transparent
            opacity={0.65}
            blending={THREE.AdditiveBlending}
          />
        </mesh>

        {/* Outer Gyro Ring */}
        <mesh ref={ring2Ref}>
          <torusGeometry args={[0.42, 0.009, 16, 32]} />
          <meshBasicMaterial
            color={node.color}
            transparent
            opacity={0.45}
            blending={THREE.AdditiveBlending}
          />
        </mesh>

        {/* Soft volumetric glow aura */}
        <mesh scale={2.4}>
          <sphereGeometry args={[0.2, 16, 16]} />
          <meshBasicMaterial
            color={node.color}
            transparent
            opacity={hovered ? 0.35 : 0.16}
            blending={THREE.AdditiveBlending}
            depthWrite={false}
          />
        </mesh>

        {/* Label */}
        <Html
          center
          position={node.labelOffset ?? [0, 0.65, 0]}
          zIndexRange={[20, 0]}
          style={{ pointerEvents: "none" }}
        >
          <div className="w-max whitespace-nowrap rounded-md border border-line/70 bg-[#060d11]/85 px-2 py-1 backdrop-blur-md transition-all duration-200">
            <div
              className="mono text-[9px] font-bold tracking-[0.14em]"
              style={{ color: node.color, textShadow: `0 0 10px ${node.color}88` }}
            >
              {node.title}
            </div>
            {node.sub && (
              <div className="mono mt-0.5 text-[7px] tracking-[0.12em] text-ink/70">
                {node.sub}
              </div>
            )}
          </div>
        </Html>
      </group>
    </group>
  );
}

/* ------------------------------------------------ high-velocity energy flows */

function EnergyStream({
  from,
  to,
  count = 18,
  color = "#ffffff",
  speed = 0.25,
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
      // Parabolic arc for energy leaping
      const arc = Math.sin(t * Math.PI) * 0.45;
      array[index * 3] = from[0] + (to[0] - from[0]) * t;
      array[index * 3 + 1] = from[1] + (to[1] - from[1]) * t + arc;
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
        size={0.075}
        color={color}
        transparent
        opacity={0.95}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/* ------------------------------------------------ radar ground heartbeat */

function RadarPulse({
  at,
  color,
  speed = 0.5,
  reach = 2.4,
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
    mesh.scale.setScalar(0.2 + t * reach);
    const material = mesh.material as THREE.MeshBasicMaterial;
    material.opacity = Math.pow(1 - t, 1.8) * 0.45;
  });

  return (
    <mesh ref={ring} position={[at[0], -0.93, at[2]]} rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[0.92, 1, 64]} />
      <meshBasicMaterial
        color={color}
        transparent
        opacity={0.4}
        side={THREE.DoubleSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  );
}

/* ------------------------------------------------ interactive star nebula */

function FloatingNebula({ count = 350 }: { count?: number }) {
  const points = useRef<THREE.Points>(null);

  const { positions, colors, velocities } = useMemo(() => {
    const position = new Float32Array(count * 3);
    const colour = new Float32Array(count * 3);
    const velocity = new Float32Array(count * 3);
    const palette = [TEAL, PURPLE, AMBER, GREEN, "#38bdf8"];

    for (let i = 0; i < count; i++) {
      position[i * 3] = (Math.random() - 0.5) * 24;
      position[i * 3 + 1] = Math.random() * 7 - 1;
      position[i * 3 + 2] = (Math.random() - 0.5) * 16;

      const swatch = new THREE.Color(palette[i % palette.length]);
      colour[i * 3] = swatch.r;
      colour[i * 3 + 1] = swatch.g;
      colour[i * 3 + 2] = swatch.b;

      velocity[i * 3] = (Math.random() - 0.5) * 0.04;
      velocity[i * 3 + 1] = 0.03 + Math.random() * 0.08;
      velocity[i * 3 + 2] = (Math.random() - 0.5) * 0.04;
    }

    return { positions: position, colors: colour, velocities: velocity };
  }, [count]);

  useFrame((_, delta) => {
    const attr = points.current?.geometry.getAttribute("position") as
      | THREE.BufferAttribute
      | undefined;
    if (!attr) return;
    const array = attr.array as Float32Array;

    for (let i = 0; i < count; i++) {
      array[i * 3] += velocities[i * 3] * delta;
      array[i * 3 + 1] += velocities[i * 3 + 1] * delta;
      array[i * 3 + 2] += velocities[i * 3 + 2] * delta;

      if (array[i * 3 + 1] > 6) {
        array[i * 3] = (Math.random() - 0.5) * 24;
        array[i * 3 + 1] = -0.8;
        array[i * 3 + 2] = (Math.random() - 0.5) * 16;
      }
    }
    attr.needsUpdate = true;
  });

  return (
    <points ref={points}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.065}
        vertexColors
        transparent
        opacity={0.8}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/* ------------------------------------------------ camera rig with inertia */

function SmoothRig({ mousePos }: { mousePos: React.MutableRefObject<{ x: number; y: number }> }) {
  const { camera } = useThree();
  const target = useRef({ x: 9.0, y: 7.2, z: 12.0 });

  useEffect(() => {
    camera.lookAt(0, 0.4, 0);
  }, [camera]);

  useFrame((_, delta) => {
    const dt = Math.min(delta, 0.05);
    // Smooth camera orbit tilt based on mouse
    target.current.x = 9.0 + mousePos.current.x * 2.2;
    target.current.y = 7.2 - mousePos.current.y * 1.5;
    camera.position.x += (target.current.x - camera.position.x) * dt * 2.8;
    camera.position.y += (target.current.y - camera.position.y) * dt * 2.8;
    camera.lookAt(0, 0.4, 0);
  });

  return null;
}

/* ------------------------------------------------ scene composition */

function Scene({
  mousePos,
  drift,
}: {
  mousePos: React.MutableRefObject<{ x: number; y: number }>;
  drift: boolean;
}) {
  const worldRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (!drift || !worldRef.current) return;
    worldRef.current.rotation.y += 0.0004 * Math.min(delta, 0.05) * 60;
  });

  return (
    <>
      <fog attach="fog" args={[BG, 14, 38]} />
      <ambientLight intensity={1.4} />
      <directionalLight position={[6, 9, 7]} intensity={1.8} color="#e0f2fe" />
      <pointLight position={[-4, 2.5, 1]} intensity={8} distance={12} color={TEAL} />
      <pointLight position={[4, 2.5, 2]} intensity={7} distance={12} color={AMBER} />
      <pointLight position={[0, 3, -2]} intensity={6} distance={10} color={PURPLE} />

      <InteractiveMouseLight mousePos={mousePos} />
      <FloatingNebula count={350} />

      <group ref={worldRef}>
        <UndulatingTerrain mousePos={mousePos} />

        {/* Dependency arteries: blood -> heart -> lungs -> organs */}
        {[
          ["blood", "heart"],
          ["heart", "lungs"],
          ["lungs", "organs"],
        ].map(([a, b]) => (
          <group key={`${a}-${b}`}>
            <Line
              points={[at(a), at(b)]}
              color={ORANGE}
              lineWidth={1.8}
              transparent
              opacity={0.8}
            />
            <EnergyStream from={at(a)} to={at(b)} count={18} color="#ffffff" speed={0.24} />
          </group>
        ))}

        {/* Impassable corridor */}
        <Line
          points={[at("lungs"), at("organs")]}
          color={RED}
          lineWidth={1.4}
          dashed
          dashSize={0.2}
          gapSize={0.14}
          transparent
          opacity={0.65}
        />

        {/* A* Optimal detour */}
        <Line
          points={[at("lungs"), at("bypass"), at("organs")]}
          color={GREEN}
          lineWidth={1.8}
          transparent
          opacity={0.85}
        />
        <EnergyStream from={at("lungs")} to={at("bypass")} count={12} color={GREEN} speed={0.28} />
        <EnergyStream from={at("bypass")} to={at("organs")} count={12} color={GREEN} speed={0.28} />

        {/* Nodes */}
        {NODES.map((node) => (
          <KineticNode key={node.id} node={node} />
        ))}

        {/* Radar heartbeat & hazard pulses */}
        <RadarPulse at={at("heart")} color={PURPLE} speed={0.45} reach={2.6} />
        <RadarPulse at={at("blocked")} color={RED} speed={0.8} reach={1.8} />
      </group>
    </>
  );
}

/* ------------------------------------------------ export default */

export default function RunningGridBackground() {
  const [reduced, setReduced] = useState(false);
  const mousePos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const onChange = () => setReduced(query.matches);
    query.addEventListener?.("change", onChange);

    const onMouseMove = (e: MouseEvent) => {
      mousePos.current.x = (e.clientX / window.innerWidth - 0.5) * 2;
      mousePos.current.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMouseMove);

    return () => {
      query.removeEventListener?.("change", onChange);
      window.removeEventListener("mousemove", onMouseMove);
    };
  }, []);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      {/* 3D Canvas with enhanced opacity & vibrancy */}
      <div className="absolute inset-0 opacity-[0.55] transition-opacity duration-700">
        <Canvas
          style={{ width: "100%", height: "100%", display: "block" }}
          dpr={[1, 1.5]}
          camera={{ position: [9.0, 7.2, 12.0], fov: 38, near: 0.1, far: 70 }}
          gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        >
          <ClampDelta />
          <SmoothRig mousePos={mousePos} />
          <Scene mousePos={mousePos} drift={!reduced} />
        </Canvas>
      </div>

      {/* Modern cinematic vignette: focused dark core with glowing cyber horizon */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_50%,transparent_0%,rgba(4,9,13,0.35)_50%,rgba(4,9,13,0.85)_100%)]" />
      {/* Ethereal floor glow */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_100%,rgba(45,212,191,0.08),transparent_60%)]" />
    </div>
  );
}
