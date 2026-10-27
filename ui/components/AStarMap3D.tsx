"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import * as THREE from "three";
import { COLORS, lifeline } from "@/lib/lifeline";

/** Real relative geography, scaled from the lat/lon in town.json. */
const ORIGIN = { lat: 11.0168, lon: 76.9558 };
const project = (lat: number, lon: number): [number, number, number] => [
  (lon - ORIGIN.lon) * 300 - 3,
  0.55,
  -(lat - ORIGIN.lat) * 300 + 2.5,
];

const DEPOT = project(11.0168, 76.9558);
const HOSPITAL = project(11.035, 76.972);
const PUMP = project(11.029, 76.986);
const SHELTERS = project(11.031, 76.992);

const TERRAIN = (x: number, z: number) =>
  Math.sin(x * 0.55) * Math.cos(z * 0.5) * 0.18 +
  Math.sin(x * 1.35 + z * 0.75) * 0.09 +
  Math.cos(z * 1.9) * 0.04;

function Terrain() {
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(26, 16, 72, 44);
    const position = geo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < position.count; i += 1) {
      const x = position.getX(i);
      const y = position.getY(i);
      position.setZ(i, TERRAIN(x, -y));
    }
    geo.computeVertexNormals();
    return geo;
  }, []);

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} geometry={geometry} receiveShadow>
      <meshStandardMaterial
        color="#12303a"
        emissive="#0c2028"
        emissiveIntensity={0.65}
        roughness={0.92}
        metalness={0.08}
      />
    </mesh>
  );
}

function TerrainWire() {
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(26, 16, 36, 22);
    const position = geo.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < position.count; i += 1) {
      const x = position.getX(i);
      const y = position.getY(i);
      position.setZ(i, TERRAIN(x, -y) + 0.01);
    }
    return geo;
  }, []);
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} geometry={geometry}>
      <meshBasicMaterial color="#1d4a56" wireframe transparent opacity={0.22} />
    </mesh>
  );
}

function Marker({
  at,
  color,
  label,
  value,
}: {
  at: [number, number, number];
  color: string;
  label: string;
  value: string;
}) {
  const ring = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (ring.current) {
      const s = 1 + Math.sin(state.clock.elapsedTime * 2 + at[0]) * 0.12;
      ring.current.scale.setScalar(s);
    }
  });
  return (
    <group position={at}>
      <mesh position={[0, 0.25, 0]}>
        <cylinderGeometry args={[0.035, 0.035, 0.5, 10]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.8} />
      </mesh>
      <mesh ref={ring} position={[0, 0.55, 0]}>
        <sphereGeometry args={[0.13, 20, 20]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={1.4} />
      </mesh>
      <mesh position={[0, 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.22, 0.27, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
      <Html center distanceFactor={7} position={[0, 1.05, 0]} zIndexRange={[10, 0]}>
        <div className="whitespace-nowrap rounded border border-white/15 bg-black/75 px-1.5 py-0.5 text-center backdrop-blur-sm">
          <div className="mono text-[7.5px] tracking-[0.12em]" style={{ color }}>
            {label}
          </div>
          <div className="mono text-[9px] font-semibold text-ink">{value}</div>
        </div>
      </Html>
    </group>
  );
}

/** The tanker that proves the route: one loop, then it repeats. */
function Tanker({ curve, paused }: { curve: THREE.CatmullRomCurve3; paused: boolean }) {
  const ref = useRef<THREE.Group>(null);
  const t = useRef(0);
  useFrame((_, delta) => {
    if (!ref.current) return;
    if (!paused) t.current = (t.current + delta * 0.09) % 1;
    const point = curve.getPointAt(t.current);
    const ahead = curve.getPointAt(Math.min(1, t.current + 0.01));
    ref.current.position.copy(point);
    ref.current.position.y += 0.16;
    ref.current.lookAt(ahead.x, point.y + 0.16, ahead.z);
  });
  return (
    <group ref={ref}>
      <mesh>
        <boxGeometry args={[0.42, 0.2, 0.22]} />
        <meshStandardMaterial color="#e8f3f6" emissive="#2dd4bf" emissiveIntensity={0.35} metalness={0.6} roughness={0.3} />
      </mesh>
      <mesh position={[-0.22, 0, 0]}>
        <boxGeometry args={[0.16, 0.16, 0.2]} />
        <meshStandardMaterial color="#2dd4bf" emissive="#2dd4bf" emissiveIntensity={0.8} />
      </mesh>
      <pointLight color="#2dd4bf" intensity={1.4} distance={2.4} />
    </group>
  );
}

function Rain({ intensity }: { intensity: number }) {
  const ref = useRef<THREE.Points>(null);
  const count = 900;
  const { positions, speeds } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const speeds = new Float32Array(count);
    for (let i = 0; i < count; i += 1) {
      positions[i * 3] = (Math.random() - 0.5) * 26;
      positions[i * 3 + 1] = Math.random() * 12;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 16;
      speeds[i] = 2.4 + Math.random() * 3.2;
    }
    return { positions, speeds };
  }, [count]);

  useFrame((_, delta) => {
    if (!ref.current || intensity <= 1) return;
    const attr = ref.current.geometry.getAttribute("position") as THREE.BufferAttribute;
    for (let i = 0; i < count; i += 1) {
      let y = attr.getY(i) - speeds[i] * delta * (0.35 + intensity / 100);
      if (y < 0) y = 12;
      attr.setY(i, y);
    }
    attr.needsUpdate = true;
  });

  if (intensity <= 1) return null;
  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color="#9fd9ff"
        size={0.035}
        transparent
        opacity={Math.min(0.75, 0.12 + intensity / 130)}
        depthWrite={false}
      />
    </points>
  );
}

export default function AStarMap3D() {
  const [rain, setRain] = useState(0);
  const [running, setRunning] = useState(true);

  const blockedCurve = useMemo(
    () => new THREE.CatmullRomCurve3([new THREE.Vector3(...DEPOT), new THREE.Vector3(...HOSPITAL)]),
    [],
  );

  const bypass = useMemo(
    () =>
      new THREE.CatmullRomCurve3([
        new THREE.Vector3(...DEPOT),
        new THREE.Vector3(-2.4, 0.6, -1.4),
        new THREE.Vector3(0.2, 0.6, -4.4),
        new THREE.Vector3(3.1, 0.6, -5.0),
        new THREE.Vector3(...HOSPITAL),
      ]),
    [],
  );

  const blockedGeo = useMemo(() => new THREE.TubeGeometry(blockedCurve, 32, 0.045, 8, false), [blockedCurve]);
  const bypassGeo = useMemo(() => new THREE.TubeGeometry(bypass, 160, 0.055, 8, false), [bypass]);

  const km = lifeline.route.distance_km;
  const saved = lifeline.route.saving;

  return (
    <div className="grid gap-4 lg:grid-cols-[1.55fr_1fr]">
      <div className="relative h-[430px] overflow-hidden rounded-xl border border-line bg-[#061017]">
        <Canvas dpr={[1, 1.6]} camera={{ position: [0, 12, 13], fov: 40 }}>
          <color attach="background" args={["#061017"]} />
          <ambientLight intensity={0.6} />
          <directionalLight position={[6, 12, 6]} intensity={2.1} color="#cfe9ff" />
          <pointLight position={[...DEPOT]} intensity={8} color={COLORS.teal} distance={7} />
          <pointLight position={[...HOSPITAL]} intensity={10} color={COLORS.blood} distance={8} />
          <fog attach="fog" args={["#061017", 16, 34]} />

          <Terrain />
          <TerrainWire />
          <Rain intensity={rain} />

          {/* the 4.2 km corridor, blocked */}
          <mesh geometry={blockedGeo}>
            <meshStandardMaterial color={COLORS.blood} emissive={COLORS.blood} emissiveIntensity={0.6} transparent opacity={0.55} />
          </mesh>
          <group position={[(DEPOT[0] + HOSPITAL[0]) / 2, 0.72, (DEPOT[2] + HOSPITAL[2]) / 2]}>
            <mesh rotation={[0, Math.PI / 4, Math.PI / 4]}>
              <boxGeometry args={[0.5, 0.06, 0.06]} />
              <meshStandardMaterial color="#ff5f5f" emissive="#ff5f5f" emissiveIntensity={2} />
            </mesh>
            <mesh rotation={[0, Math.PI / 4, -Math.PI / 4]}>
              <boxGeometry args={[0.5, 0.06, 0.06]} />
              <meshStandardMaterial color="#ff5f5f" emissive="#ff5f5f" emissiveIntensity={2} />
            </mesh>
          </group>

          {/* the route A* actually found */}
          <mesh geometry={bypassGeo}>
            <meshStandardMaterial color={COLORS.teal} emissive={COLORS.teal} emissiveIntensity={0.9} />
          </mesh>
          <Tanker curve={bypass} paused={!running} />

          <Marker at={DEPOT} color={COLORS.teal} label="DEPOT" value="100 L" />
          <Marker at={HOSPITAL} color={COLORS.blood} label="HOSPITAL" value="70 L" />
          <Marker at={PUMP} color={COLORS.lung} label="PUMP" value="30 L" />
          <Marker at={SHELTERS} color={COLORS.amber} label="SHELTERS" value="200" />

          <OrbitControls
            enablePan={false}
            minDistance={9}
            maxDistance={24}
            maxPolarAngle={Math.PI * 0.46}
            minPolarAngle={Math.PI * 0.16}
            autoRotate
            autoRotateSpeed={0.22}
          />
        </Canvas>

        <div className="pointer-events-none absolute left-4 top-4 space-y-1">
          <div className="mono rounded border border-blood/40 bg-black/60 px-2 py-1 text-[10px] text-blood">
            NH-544 km 42 · 4.2 km BLOCKED
          </div>
          <div className="mono rounded border border-teal/40 bg-black/60 px-2 py-1 text-[10px] text-teal">
            A* BYPASS · {km} km
          </div>
        </div>

        <div className="absolute bottom-3 left-3 rounded border border-line bg-black/60 px-2 py-1 mono text-[9px] text-muted">
          terrain is schematic · distances are from the repo graph
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="rounded-xl border border-line bg-panel/80 p-4">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">ROUTE RESULT</div>
          <div className="mt-2 flex items-end gap-3">
            <div>
              <div className="mono text-[10px] text-muted">direct</div>
              <div className="text-xl font-semibold text-blood line-through decoration-2">4.2 km</div>
            </div>
            <div className="pb-1 text-muted">→</div>
            <div>
              <div className="mono text-[10px] text-muted">A* heapq</div>
              <div className="text-2xl font-semibold text-teal">{km} km</div>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            className="mt-3 rounded-lg border border-teal/40 bg-teal/5 p-3"
          >
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-teal">{saved.percent}%</span>
              <span className="text-[12px] text-muted">fuel saved vs the 13.0 km signposted bypass</span>
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-2 mono text-[10px] text-muted">
              <div>km saved <span className="text-ink">{saved.km}</span></div>
              <div>diesel saved <span className="text-ink">{saved.fuel_litres} L</span></div>
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-muted/80">
              Anchored to the 13.0 km detour, not to the blocked 4.2 km corridor. The
              second number would be a 40% saving that nobody could ever drive.
            </p>
          </motion.div>
        </div>

        <div className="rounded-xl border border-line bg-panel/80 p-4">
          <div className="flex items-center justify-between">
            <div className="mono text-[10px] tracking-[0.18em] text-muted">SCENARIO: RAINFALL</div>
            <span className="mono text-[11px] text-teal">{rain}%</span>
          </div>
          <input
            aria-label="rainfall scenario input"
            type="range"
            min={0}
            max={80}
            step={5}
            value={rain}
            onChange={(event) => setRain(Number(event.target.value))}
            className="mt-2 w-full accent-teal"
          />
          <p className="mt-1 text-[10px] text-muted/80">
            Scenario input, not a forecast. The agent consumes rain as a parameter;
            no weather API key is used or claimed.
          </p>
          {rain >= 60 && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-2 rounded border border-amber/40 bg-amber/5 p-2 text-[11px] text-amber"
            >
              At {rain}% the 7.8 km bypass itself is at risk. The agent re-runs A* with
              the flooded edge closed rather than driving into it.
            </motion.div>
          )}
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => setRunning((v) => !v)}
              className="rounded-md border border-line px-3 py-1.5 mono text-[10px] text-muted transition hover:border-teal/60 hover:text-teal"
            >
              {running ? "PAUSE TANKER" : "RUN TANKER"}
            </button>
            <button
              onClick={() => setRain(0)}
              className="rounded-md border border-line px-3 py-1.5 mono text-[10px] text-muted transition hover:border-teal/60 hover:text-teal"
            >
              CLEAR RAIN
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
