"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars, Html } from "@react-three/drei";
import { useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { COLORS, lifeline } from "@/lib/lifeline";
import { useVisible } from "@/lib/useVisible";
import { ClampDelta } from "./ClampDelta";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";

type NodeId = "depot" | "heart" | "lungs" | "organs";

const LITRES = {
  depot: lifeline.organs.fuel_depot?.litres ?? 100,
  heart: lifeline.organs.hospital?.litres ?? 70,
  lungs: lifeline.organs.water_pump?.litres ?? 30,
  organs: lifeline.organs.shelters?.people ?? 200,
};

const POSITIONS: Record<NodeId, [number, number, number]> = {
  depot: [-3.2, 0.0, 0],
  heart: [2.0, 1.6, 0],
  lungs: [2.0, -1.55, 0],
  organs: [-0.5, -2.25, 1.15],
};

function useCurves() {
  return useMemo(
    () => ({
      heart: new THREE.CatmullRomCurve3([
        new THREE.Vector3(...POSITIONS.depot),
        new THREE.Vector3(-1.8, 1.45, 0.75),
        new THREE.Vector3(0.25, 1.95, 0.4),
        new THREE.Vector3(...POSITIONS.heart),
      ]),
      lungs: new THREE.CatmullRomCurve3([
        new THREE.Vector3(...POSITIONS.depot),
        new THREE.Vector3(-1.7, -1.25, 0.65),
        new THREE.Vector3(0.35, -1.9, 0.3),
        new THREE.Vector3(...POSITIONS.lungs),
      ]),
      organs: new THREE.CatmullRomCurve3([
        new THREE.Vector3(...POSITIONS.heart),
        new THREE.Vector3(0.55, 0.15, 1.05),
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
}: {
  curve: THREE.CatmullRomCurve3;
  color: string;
  radius: number;
}) {
  const geometry = useMemo(
    () => new THREE.TubeGeometry(curve, 128, radius, 12, false),
    [curve, radius],
  );
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color={color}
        emissive={color}
        emissiveIntensity={0.7}
        transparent
        opacity={0.32}
        roughness={0.35}
        metalness={0.15}
      />
    </mesh>
  );
}

/** Diesel as blood: particles running the arteries, 70/30 split. */
function Bloodflow({ count = 320 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null);
  const curves = useCurves();
  const t = useRef(0);

  const { seeds } = useMemo(() => {
    const seeds = Array.from({ length: count }, (_, i) => ({
      curve: i % 10 < 7 ? "heart" : "lungs",
      offset: Math.random(),
      speed: 0.5 + Math.random() * 0.55,
      size: 0.7 + Math.random() * 0.9,
    }));
    return { seeds };
  }, [count]);

  const positions = useMemo(() => new Float32Array(count * 3), [count]);
  const sizes = useMemo(() => {
    const s = new Float32Array(count);
    seeds.forEach((seed, i) => (s[i] = seed.size));
    return s;
  }, [seeds]);

  useFrame((_, delta) => {
    if (!ref.current) return;
    t.current = (t.current + delta * 0.12) % 1;
    const attr = ref.current.geometry.getAttribute("position") as THREE.BufferAttribute;
    const point = new THREE.Vector3();
    seeds.forEach((seed, i) => {
      const curve = seed.curve === "heart" ? curves.heart : curves.lungs;
      const u = (t.current * seed.speed + seed.offset) % 1;
      curve.getPointAt(u, point);
      attr.setXYZ(
        i,
        point.x + Math.sin(u * 31 + i) * 0.04,
        point.y + Math.cos(u * 27 + i) * 0.04,
        point.z + Math.sin(u * 19 + i) * 0.07,
      );
    });
    attr.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-size" args={[sizes, 1]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.06}
        sizeAttenuation
        vertexColors={false}
        color="#f5b942"
        transparent
        opacity={0.9}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/** Beating heart: two lobes + apex, fleshy subsurface material, pulse ring. */
function Heart({ position }: { position: [number, number, number] }) {
  const group = useRef<THREE.Group>(null);
  const lobeL = useRef<THREE.Mesh>(null);
  const lobeR = useRef<THREE.Mesh>(null);
  const apex = useRef<THREE.Mesh>(null);
  const ring = useRef<THREE.Mesh>(null);
  const t = useRef(0);

  useFrame((_, delta) => {
    t.current += delta;
    const beat = 1 + Math.sin(t.current * Math.PI * 2.2) * 0.09 + Math.sin(t.current * Math.PI * 4.4) * 0.03;
    if (group.current) group.current.scale.setScalar(beat);
    if (ring.current) {
      const pulse = (t.current * 0.6) % 1;
      ring.current.scale.setScalar(1 + pulse * 0.9);
      const m = ring.current.material as THREE.MeshBasicMaterial;
      m.opacity = 0.35 * (1 - pulse);
    }
  });

  const flesh = (
    <meshPhysicalMaterial
      color="#8b1a2b"
      emissive="#5a0f1a"
      emissiveIntensity={0.6}
      roughness={0.35}
      metalness={0.05}
      clearcoat={1.0}
      clearcoatRoughness={0.25}
      transmission={0.12}
      thickness={0.6}
      attenuationColor="#6b0f1a"
      attenuationDistance={0.4}
      ior={1.4}
    />
  );

  return (
    <group ref={group} position={position}>
      {/* left lobe */}
      <mesh ref={lobeL} position={[-0.22, 0.18, 0.05]}>
        <sphereGeometry args={[0.34, 48, 48]} />
        {flesh}
      </mesh>
      {/* right lobe */}
      <mesh ref={lobeR} position={[0.22, 0.18, -0.05]}>
        <sphereGeometry args={[0.34, 48, 48]} />
        {flesh}
      </mesh>
      {/* body */}
      <mesh position={[0, -0.05, 0]}>
        <sphereGeometry args={[0.4, 48, 48]} />
        {flesh}
      </mesh>
      {/* apex */}
      <mesh ref={apex} position={[0, -0.55, 0.05]} rotation={[Math.PI, 0, 0]}>
        <coneGeometry args={[0.22, 0.45, 32]} />
        {flesh}
      </mesh>
      {/* aorta */}
      <mesh position={[0.05, 0.55, 0.05]} rotation={[0.3, 0, 0.2]}>
        <cylinderGeometry args={[0.07, 0.09, 0.45, 16]} />
        {flesh}
      </mesh>
      {/* pulse ring */}
      <mesh ref={ring} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.7, 0.025, 12, 64]} />
        <meshBasicMaterial color="#ff4d6d" transparent opacity={0.35} />
      </mesh>
      <pointLight color="#ff4d6d" intensity={1.8} distance={4.5} decay={2} />
    </group>
  );
}

/** Breathing lungs: three lobes each, fleshy material. */
function Lungs({ position }: { position: [number, number, number] }) {
  const group = useRef<THREE.Group>(null);
  const t = useRef(0);

  useFrame((_, delta) => {
    t.current += delta;
    const breath = 1 + Math.sin(t.current * 1.4) * 0.05;
    if (group.current) group.current.scale.setScalar(breath);
  });

  const flesh = (color: string) => (
    <meshPhysicalMaterial
      color={color}
      emissive={color}
      emissiveIntensity={0.5}
      roughness={0.4}
      metalness={0.05}
      clearcoat={0.8}
      clearcoatRoughness={0.3}
      transmission={0.08}
      thickness={0.5}
      attenuationColor={color}
      attenuationDistance={0.4}
      ior={1.35}
    />
  );

  return (
    <group ref={group} position={position}>
      {/* left lung lobes */}
      <mesh position={[-0.3, 0.15, 0.15]}>
        <sphereGeometry args={[0.32, 32, 32]} />
        {flesh(COLORS.lung)}
      </mesh>
      <mesh position={[-0.15, -0.15, 0.05]} scale={[1, 0.85, 1]}>
        <sphereGeometry args={[0.28, 32, 32]} />
        {flesh(COLORS.lung)}
      </mesh>
      <mesh position={[-0.4, -0.05, -0.1]}>
        <sphereGeometry args={[0.26, 32, 32]} />
        {flesh(COLORS.lung)}
      </mesh>
      {/* right lung lobes */}
      <mesh position={[0.3, 0.1, -0.1]}>
        <sphereGeometry args={[0.34, 32, 32]} />
        {flesh(COLORS.lung)}
      </mesh>
      <mesh position={[0.15, -0.2, 0.05]} scale={[1, 0.8, 1]}>
        <sphereGeometry args={[0.28, 32, 32]} />
        {flesh(COLORS.lung)}
      </mesh>
      <mesh position={[0.4, -0.05, 0.15]}>
        <sphereGeometry args={[0.24, 32, 32]} />
        {flesh(COLORS.lung)}
      </mesh>
      {/* trachea */}
      <mesh position={[0, 0.55, 0]} rotation={[0, 0, 0]}>
        <cylinderGeometry args={[0.05, 0.06, 0.5, 12]} />
        {flesh("#a8d8e8")}
      </mesh>
      <pointLight color={COLORS.lung} intensity={1.0} distance={3.5} decay={2} />
    </group>
  );
}

/** Fuel depot: a glowing cylinder with a rotating ring. */
function Depot({ position }: { position: [number, number, number] }) {
  const ring = useRef<THREE.Mesh>(null);
  useFrame((_, delta) => {
    if (ring.current) ring.current.rotation.z += delta * 0.6;
  });
  return (
    <group position={position}>
      <mesh>
        <cylinderGeometry args={[0.42, 0.42, 0.9, 32]} />
        <meshStandardMaterial color={COLORS.teal} emissive={COLORS.teal} emissiveIntensity={1.1} roughness={0.3} metalness={0.2} />
      </mesh>
      <mesh ref={ring} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.72, 0.03, 12, 64]} />
        <meshBasicMaterial color={COLORS.teal} transparent opacity={0.55} />
      </mesh>
      <pointLight color={COLORS.teal} intensity={1.2} distance={4} decay={2} />
    </group>
  );
}

/** Shelters: small amber orbs representing the 200 people. */
function Organs({ position }: { position: [number, number, number] }) {
  const group = useRef<THREE.Group>(null);
  useFrame((_, delta) => {
    if (group.current) group.current.rotation.y += delta * 0.25;
  });
  const orbs = useMemo(() => Array.from({ length: 12 }, (_, i) => {
    const a = (i / 12) * Math.PI * 2;
    const r = 0.55 + (i % 3) * 0.12;
    return [Math.cos(a) * r, (i % 4) * 0.18 - 0.27, Math.sin(a) * r] as [number, number, number];
  }), []);
  return (
    <group ref={group} position={position}>
      {orbs.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.09, 16, 16]} />
          <meshStandardMaterial color={COLORS.amber} emissive={COLORS.amber} emissiveIntensity={1.0} roughness={0.4} />
        </mesh>
      ))}
      <pointLight color={COLORS.amber} intensity={0.7} distance={3} decay={2} />
    </group>
  );
}

function Label({ position, title, value, color }: { position: [number, number, number]; title: string; value: string; color: string }) {
  return (
    <Html position={position} center distanceFactor={9} occlude>
      <div
        style={{
          color,
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
          fontSize: 10,
          letterSpacing: "0.12em",
          textTransform: "uppercase",
          background: "rgba(5,12,16,0.72)",
          border: `1px solid ${color}55`,
          padding: "3px 7px",
          borderRadius: 6,
          whiteSpace: "nowrap",
          backdropFilter: "blur(6px)",
          pointerEvents: "none",
        }}
      >
        <div style={{ opacity: 0.7, fontSize: 8 }}>{title}</div>
        <div style={{ fontWeight: 700 }}>{value}</div>
      </div>
    </Html>
  );
}

function Scene() {
  const curves = useCurves();
  return (
    <>
      <fog attach="fog" args={["#060d11", 6, 16]} />
      <ambientLight intensity={0.25} />
      <directionalLight position={[4, 6, 3]} intensity={0.9} color="#ffffff" />
      <pointLight position={[-4, -2, -2]} intensity={0.4} color={COLORS.teal} />

      <Stars radius={60} depth={40} count={1800} factor={3} saturation={0} fade speed={0.6} />

      <Artery curve={curves.heart} color={COLORS.blood} radius={0.05} />
      <Artery curve={curves.lungs} color={COLORS.lung} radius={0.045} />
      <Artery curve={curves.organs} color={COLORS.amber} radius={0.035} />

      <Bloodflow count={320} />

      <Depot position={POSITIONS.depot} />
      <Heart position={POSITIONS.heart} />
      <Lungs position={POSITIONS.lungs} />
      <Organs position={POSITIONS.organs} />

      <Label position={[POSITIONS.depot[0], POSITIONS.depot[1] + 0.95, POSITIONS.depot[2]]} title="depot" value={`${LITRES.depot} L`} color={COLORS.teal} />
      <Label position={[POSITIONS.heart[0], POSITIONS.heart[1] + 0.95, POSITIONS.heart[2]]} title="heart" value={`${LITRES.heart} L`} color={COLORS.blood} />
      <Label position={[POSITIONS.lungs[0], POSITIONS.lungs[1] - 0.85, POSITIONS.lungs[2]]} title="lungs" value={`${LITRES.lungs} L`} color={COLORS.lung} />
      <Label position={[POSITIONS.organs[0], POSITIONS.organs[1] - 0.95, POSITIONS.organs[2]]} title="organs" value={`${LITRES.organs} people`} color={COLORS.amber} />

      <OrbitControls
        enablePan={false}
        enableZoom={false}
        autoRotate
        autoRotateSpeed={0.6}
        minPolarAngle={Math.PI / 3.2}
        maxPolarAngle={Math.PI / 1.7}
        dampingFactor={0.08}
        enableDamping
      />
    </>
  );
}

export default function Lifegrid3D() {
  const { ref, visible } = useVisible<HTMLDivElement>("260px");
  return (
    <div ref={ref} className="h-full w-full">
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [0, 0.4, 7.2], fov: 46 }}
        frameloop={visible ? "always" : "never"}
        gl={{ antialias: true, alpha: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.05 }}
      >
        <ClampDelta />
        <Scene />
        <EffectComposer>
          <Bloom luminanceThreshold={0.25} luminanceSmoothing={0.85} intensity={1.1} mipmapBlur />
          <Vignette eskil={false} offset={0.12} darkness={0.55} />
        </EffectComposer>
      </Canvas>
    </div>
  );
}
