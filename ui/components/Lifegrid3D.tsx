"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { COLORS, lifeline } from "@/lib/lifeline";
import { useLocale } from "./LocaleProvider";

type NodeId = "depot" | "heart" | "lungs" | "organs";

const LITRES = {
  depot: lifeline.organs.fuel_depot?.litres ?? 100,
  heart: lifeline.organs.hospital?.litres ?? 70,
  lungs: lifeline.organs.water_pump?.litres ?? 30,
  organs: lifeline.organs.shelters?.people ?? 200,
};

const POSITIONS: Record<NodeId, [number, number, number]> = {
  depot: [-3.1, 0.1, 0],
  heart: [2.1, 1.55, 0],
  lungs: [2.1, -1.5, 0],
  organs: [-0.4, -2.15, 1.1],
};

/** Arteries: depot to heart, depot to lungs, heart to the organs it feeds. */
function useCurves() {
  return useMemo(
    () => ({
      heart: new THREE.CatmullRomCurve3([
        new THREE.Vector3(...POSITIONS.depot),
        new THREE.Vector3(-1.7, 1.5, 0.7),
        new THREE.Vector3(0.3, 1.9, 0.35),
        new THREE.Vector3(...POSITIONS.heart),
      ]),
      lungs: new THREE.CatmullRomCurve3([
        new THREE.Vector3(...POSITIONS.depot),
        new THREE.Vector3(-1.6, -1.2, 0.6),
        new THREE.Vector3(0.4, -1.9, 0.3),
        new THREE.Vector3(...POSITIONS.lungs),
      ]),
      organs: new THREE.CatmullRomCurve3([
        new THREE.Vector3(...POSITIONS.heart),
        new THREE.Vector3(0.6, 0.2, 1.0),
        new THREE.Vector3(...POSITIONS.organs),
      ]),
    }),
    [],
  );
}

function Artery({
  curve,
  color,
  radius,
  opacity,
}: {
  curve: THREE.CatmullRomCurve3;
  color: string;
  radius: number;
  opacity: number;
}) {
  const geometry = useMemo(
    () => new THREE.TubeGeometry(curve, 96, radius, 10, false),
    [curve, radius],
  );
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.55}
        transparent
        opacity={opacity}
        roughness={0.4}
        metalness={0.1}
      />
    </mesh>
  );
}

/** Diesel as blood: 260 particles running the arteries, 70/30 of the flow. */
function Bloodflow({ count = 260 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null);
  const curves = useCurves();
  const t = useRef(0);

  const { positions, seeds } = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const seeds = Array.from({ length: count }, (_, i) => ({
      curve: i % 10 < 7 ? "heart" : "lungs",
      offset: Math.random(),
      speed: 0.55 + Math.random() * 0.5,
      size: 0.6 + Math.random() * 0.8,
    }));
    return { positions, seeds };
  }, [count]);

  useFrame((_, delta) => {
    if (!ref.current) return;
    t.current = (t.current + delta * 0.11) % 1;
    const attr = ref.current.geometry.getAttribute("position") as THREE.BufferAttribute;
    const point = new THREE.Vector3();
    seeds.forEach((seed, i) => {
      const curve = seed.curve === "heart" ? curves.heart : curves.lungs;
      const u = (t.current * seed.speed + seed.offset) % 1;
      curve.getPointAt(u, point);
      // slight scatter so it reads as flow, not a wire
      attr.setXYZ(
        i,
        point.x + Math.sin(u * 31 + i) * 0.035,
        point.y + Math.cos(u * 27 + i) * 0.035,
        point.z + Math.sin(u * 19 + i) * 0.06,
      );
    });
    attr.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        color={COLORS.blood}
        size={0.075}
        sizeAttenuation
        transparent
        opacity={0.9}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

function Heart({ active, onSelect }: { active: boolean; onSelect: () => void }) {
  const ref = useRef<THREE.Mesh>(null);
  const glow = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    const s = state.clock.elapsedTime;
    const beat = 1 + 0.075 * Math.sin(s * 7.2) + 0.035 * Math.sin(s * 14.4);
    if (ref.current) {
      ref.current.scale.setScalar(beat * (active ? 1.08 : 1));
      ref.current.rotation.y = s * 0.25;
    }
    if (glow.current) {
      glow.current.scale.setScalar(beat * 1.5 * (active ? 1.12 : 1));
    }
  });
  return (
    <group position={POSITIONS.heart} onClick={onSelect} onPointerOver={onSelect}>
      <mesh ref={glow}>
        <sphereGeometry args={[0.62, 24, 24]} />
        <meshBasicMaterial color={COLORS.blood} transparent opacity={0.12} />
      </mesh>
      <mesh ref={ref}>
        <icosahedronGeometry args={[0.62, 3]} />
        <meshStandardMaterial
          color={COLORS.blood}
          emissive={COLORS.blood}
          emissiveIntensity={active ? 1.1 : 0.65}
          roughness={0.25}
          metalness={0.15}
        />
      </mesh>
    </group>
  );
}

function Lungs({ active, onSelect }: { active: boolean; onSelect: () => void }) {
  const group = useRef<THREE.Group>(null);
  useFrame((state) => {
    const s = state.clock.elapsedTime;
    const breath = 1 + 0.05 * Math.sin(s * 1.1);
    if (group.current) group.current.scale.set(1, breath, breath * (active ? 1.08 : 1));
  });
  return (
    <group ref={group} position={POSITIONS.lungs} onClick={onSelect} onPointerOver={onSelect}>
      {[-0.34, 0.34].map((x) => (
        <mesh key={x} position={[x, 0, 0]}>
          <sphereGeometry args={[0.38, 24, 24]} />
          <meshStandardMaterial
            color={COLORS.lung}
            emissive={COLORS.lung}
            emissiveIntensity={active ? 1.0 : 0.55}
            transparent
            opacity={0.92}
            roughness={0.3}
          />
        </mesh>
      ))}
      <mesh position={[0, 0.34, 0]}>
        <cylinderGeometry args={[0.055, 0.075, 0.4, 12]} />
        <meshStandardMaterial color={COLORS.lung} emissive={COLORS.lung} emissiveIntensity={0.5} />
      </mesh>
    </group>
  );
}

function Depot({ active, onSelect }: { active: boolean; onSelect: () => void }) {
  const ring = useRef<THREE.Mesh>(null);
  useFrame((state) => {
    if (ring.current) ring.current.rotation.z = state.clock.elapsedTime * 0.4;
  });
  return (
    <group position={POSITIONS.depot} onClick={onSelect} onPointerOver={onSelect}>
      <mesh>
        <sphereGeometry args={[0.5, 28, 28]} />
        <meshStandardMaterial
          color={COLORS.teal}
          emissive={COLORS.teal}
          emissiveIntensity={active ? 1.0 : 0.5}
          transparent
          opacity={0.9}
          roughness={0.2}
          metalness={0.35}
        />
      </mesh>
      <mesh ref={ring} rotation={[Math.PI / 2.4, 0, 0]}>
        <torusGeometry args={[0.78, 0.012, 8, 64]} />
        <meshBasicMaterial color={COLORS.teal} transparent opacity={0.65} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.63, 0.006, 8, 64]} />
        <meshBasicMaterial color={COLORS.teal} transparent opacity={0.35} />
      </mesh>
    </group>
  );
}

/** 200 people, one small sphere each - not a number on a slide. */
function Organs({ active, onSelect }: { active: boolean; onSelect: () => void }) {
  const ref = useRef<THREE.InstancedMesh>(null);
  const dots = useMemo(() => {
    const list: THREE.Vector3[] = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < 96; i += 1) {
      const y = 1 - (i / 95) * 2;
      const radius = Math.sqrt(Math.max(0, 1 - y * y));
      const theta = golden * i;
      list.push(
        new THREE.Vector3(Math.cos(theta) * radius * 0.62, y * 0.5, Math.sin(theta) * radius * 0.62),
      );
    }
    return list;
  }, []);

  useFrame((state) => {
    if (!ref.current) return;
    const s = state.clock.elapsedTime;
    const dummy = new THREE.Object3D();
    dots.forEach((dot, i) => {
      const wobble = 1 + 0.03 * Math.sin(s * 1.6 + i * 0.7);
      dummy.position.copy(dot).multiplyScalar(wobble);
      const pulse = 0.016 + 0.006 * Math.sin(s * 2 + i);
      dummy.scale.setScalar(pulse);
      dummy.updateMatrix();
      ref.current!.setMatrixAt(i, dummy.matrix);
    });
    ref.current.instanceMatrix.needsUpdate = true;
    ref.current.rotation.y = s * 0.12;
  });

  return (
    <instancedMesh
      ref={ref}
      args={[
        undefined as unknown as THREE.BufferGeometry,
        undefined as unknown as THREE.Material,
        dots.length,
      ]}
      position={POSITIONS.organs}
      onClick={onSelect}
      onPointerOver={onSelect}
    >
      <sphereGeometry args={[1, 8, 8]} />
      <meshStandardMaterial
        color={COLORS.amber}
        emissive={COLORS.amber}
        emissiveIntensity={active ? 1.3 : 0.8}
        toneMapped={false}
      />
    </instancedMesh>
  );
}

function Rig() {
  const { camera } = useThree();
  useMemo(() => {
    camera.position.set(0.35, 0.55, 9.9);
  }, [camera]);
  return null;
}

export default function Lifegrid3D() {
  const { t } = useLocale();
  const [selected, setSelected] = useState<NodeId>("heart");
  const curves = useCurves();

  const info: Record<NodeId, { label: string; value: string; note: string; color: string }> = {
    depot: {
      label: t("lifegrid.blood"),
      value: `${LITRES.depot} L`,
      note: t("lifegrid.fuel"),
      color: COLORS.teal,
    },
    heart: {
      label: t("lifegrid.heart"),
      value: `${LITRES.heart} L`,
      note: t("lifegrid.runtime", { hours: lifeline.organs.hospital?.runtime_hours ?? 4 }),
      color: COLORS.blood,
    },
    lungs: {
      label: t("lifegrid.lungs"),
      value: `${LITRES.lungs} L`,
      note: t("lifegrid.feeder"),
      color: COLORS.lung,
    },
    organs: {
      label: t("lifegrid.organs"),
      value: `${LITRES.organs}`,
      note: t("lifegrid.nowater", {
        hours: lifeline.town.crisis?.expected_clear_hours ?? 6,
      }),
      color: COLORS.amber,
    },
  };

  const order: NodeId[] = ["depot", "heart", "lungs", "organs"];

  return (
    <div className="relative h-full w-full">
      <Canvas
        dpr={[1, 1.75]}
        camera={{ position: [0.35, 0.55, 9.9], fov: 42 }}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      >
        <Rig />
        <ambientLight intensity={0.55} />
        <pointLight position={[-4, 3, 4]} intensity={28} color={COLORS.teal} distance={16} />
        <pointLight position={[3, 1, 5]} intensity={26} color={COLORS.blood} distance={16} />
        <pointLight position={[1, -4, 3]} intensity={18} color={COLORS.lung} distance={14} />
        <fog attach="fog" args={["#060d11", 9, 17]} />

        <gridHelper args={[26, 26, "#173540", "#0c1d25"]} position={[0, -3.6, 0]} />

        <Depot active={selected === "depot"} onSelect={() => setSelected("depot")} />
        <Heart active={selected === "heart"} onSelect={() => setSelected("heart")} />
        <Lungs active={selected === "lungs"} onSelect={() => setSelected("lungs")} />
        <Organs active={selected === "organs"} onSelect={() => setSelected("organs")} />

        <Artery curve={curves.heart} color={COLORS.blood} radius={0.038} opacity={0.3} />
        <Artery curve={curves.lungs} color={COLORS.lung} radius={0.03} opacity={0.28} />
        <Artery curve={curves.organs} color={COLORS.amber} radius={0.018} opacity={0.42} />
        <Bloodflow />

        <OrbitControls
          enablePan={false}
          enableZoom
          minDistance={6.5}
          maxDistance={12}
          autoRotate
          autoRotateSpeed={0.3}
          minAzimuthAngle={-0.7}
          maxAzimuthAngle={0.7}
          rotateSpeed={0.5}
          maxPolarAngle={Math.PI * 0.72}
          minPolarAngle={Math.PI * 0.3}
        />
      </Canvas>

      {/* labels are DOM, not 3D text: no font fetch, so this still renders offline */}
      <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="rounded-lg border border-teal/25 bg-black/35 px-3 py-2 backdrop-blur-sm">
            <div className="mono text-[10px] tracking-[0.22em] text-teal">{info[selected].label}</div>
            <div className="mt-0.5 flex items-baseline gap-2">
              <span className="text-2xl font-semibold" style={{ color: info[selected].color }}>
                {info[selected].value}
              </span>
              <span className="text-[11px] text-muted">{info[selected].note}</span>
            </div>
          </div>
          <div className="mono hidden text-right text-[10px] leading-relaxed text-muted/80 md:block">
            <div>11.0168 N 76.9558 E</div>
            <div>KOTTUR / POLLACHI / TAMIL NADU</div>
            <div className="text-teal/70">drag to rotate</div>
          </div>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-wrap gap-1.5">
            {order.map((id) => {
              const node = info[id];
              const on = selected === id;
              return (
                <button
                  key={id}
                  onClick={() => setSelected(id)}
                  className={`pointer-events-auto rounded-md border px-2.5 py-1.5 text-left transition ${
                    on ? "bg-white/5" : "border-transparent bg-black/30 hover:bg-white/5"
                  }`}
                  style={{ borderColor: on ? `${node.color}88` : "rgba(31,53,64,.6)" }}
                >
                  <div className="mono text-[9px] tracking-[0.16em]" style={{ color: node.color }}>
                    {node.label}
                  </div>
                  <div className="text-[13px] font-semibold text-ink">{node.value}</div>
                </button>
              );
            })}
          </div>
          <div className="mono rounded border border-line/70 bg-black/40 px-2 py-1 text-[9px] text-muted">
            procedural three.js / no external scene
          </div>
        </div>
      </div>
    </div>
  );
}
