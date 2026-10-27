"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import { COLORS, lifeline, type WorldTown } from "@/lib/lifeline";

const TOWNS = lifeline.world.towns;
const ORIGIN = TOWNS.find((town) => town.data_class === "surveyed") ?? TOWNS[0];

/** lat/lon (degrees) -> point on a sphere of the given radius. */
function latLonToVec3(lat: number, lon: number, radius = 1): THREE.Vector3 {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lon + 180) * Math.PI) / 180;
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

/** Graticule: 12 meridians and 5 parallels, built once as line segments. */
function useGraticule() {
  return useMemo(() => {
    const points: number[] = [];
    const push = (a: THREE.Vector3, b: THREE.Vector3) => {
      points.push(a.x, a.y, a.z, b.x, b.y, b.z);
    };

    for (let lon = -180; lon < 180; lon += 30) {
      for (let lat = -90; lat < 90; lat += 5) {
        push(latLonToVec3(lat, lon, 1.001), latLonToVec3(lat + 5, lon, 1.001));
      }
    }
    for (let lat = -60; lat <= 60; lat += 30) {
      for (let lon = -180; lon < 180; lon += 5) {
        push(latLonToVec3(lat, lon, 1.001), latLonToVec3(lat, lon + 5, 1.001));
      }
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
    return geometry;
  }, []);
}

/** Great-circle arc between two towns, lifted off the surface. */
function useArc(from: THREE.Vector3, to: THREE.Vector3) {
  return useMemo(() => {
    const a = from.clone().normalize();
    const b = to.clone().normalize();
    const steps = 64;
    const points: THREE.Vector3[] = [];
    const quat = new THREE.Quaternion().setFromUnitVectors(a, b);
    for (let index = 0; index <= steps; index += 1) {
      const t = index / steps;
      const q = new THREE.Quaternion().slerp(quat, t);
      points.push(a.clone().applyQuaternion(q).multiplyScalar(1.02 + Math.sin(Math.PI * t) * 0.16));
    }
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [from, to]);
}

function Pin({
  town,
  active,
  onSelect,
}: {
  town: WorldTown;
  active: boolean;
  onSelect: (town: WorldTown) => void;
}) {
  const surveyed = town.data_class === "surveyed";
  const position = useMemo(() => latLonToVec3(town.lat, town.lon, 1.012), [town.lat, town.lon]);
  const halo = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!halo.current) return;
    const t = clock.getElapsedTime();
    const breathe = active ? 1.6 + Math.sin(t * 2.4) * 0.45 : 1;
    halo.current.scale.setScalar(breathe);
    const material = halo.current.material as THREE.MeshBasicMaterial;
    material.opacity = active ? 0.4 + Math.sin(t * 2.4) * 0.12 : 0.14;
  });

  return (
    <group position={position}>
      <mesh
        onClick={(event) => {
          event.stopPropagation();
          onSelect(town);
        }}
        onPointerOver={(event) => {
          event.stopPropagation();
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          document.body.style.cursor = "auto";
        }}
      >
        <sphereGeometry args={[surveyed ? 0.019 : 0.012, 12, 12]} />
        <meshBasicMaterial color={surveyed ? COLORS.teal : COLORS.amber} />
      </mesh>
      <mesh ref={halo}>
        <sphereGeometry args={[surveyed ? 0.034 : 0.024, 16, 16]} />
        <meshBasicMaterial
          color={surveyed ? COLORS.teal : COLORS.amber}
          transparent
          opacity={0.18}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
}

function Globe({
  focus,
  onSelect,
}: {
  focus: WorldTown;
  onSelect: (town: WorldTown) => void;
}) {
  const group = useRef<THREE.Group>(null);
  const graticule = useGraticule();

  const originVec = useMemo(() => latLonToVec3(ORIGIN.lat, ORIGIN.lon, 1), []);
  const focusVec = useMemo(() => latLonToVec3(focus.lat, focus.lon, 1), [focus.lat, focus.lon]);
  const arc = useArc(originVec, focusVec);

  const target = useMemo(() => {
    const q = new THREE.Quaternion();
    q.setFromUnitVectors(focusVec.clone().normalize(), new THREE.Vector3(0, 0, 1));
    return q;
  }, [focusVec]);

  useFrame((_, delta) => {
    if (!group.current) return;
    const smooth = 1 - Math.pow(0.001, delta);
    group.current.quaternion.slerp(target, Math.min(1, smooth * 0.9));
  });

  return (
    <group ref={group}>
      {/* ocean */}
      <mesh>
        <sphereGeometry args={[1, 64, 64]} />
        <meshStandardMaterial color="#071216" roughness={0.95} metalness={0.05} />
      </mesh>

      {/* graticule */}
      <lineSegments geometry={graticule}>
        <lineBasicMaterial color={COLORS.muted} transparent opacity={0.16} />
      </lineSegments>

      {/* rim light */}
      <mesh scale={1.045}>
        <sphereGeometry args={[1, 48, 48]} />
        <meshBasicMaterial color={COLORS.teal} transparent opacity={0.05} side={THREE.BackSide} />
      </mesh>

      {/* arcs: built in Kottur, applied anywhere */}
      <line>
        <primitive object={arc} attach="geometry" />
        <lineBasicMaterial color={COLORS.teal} transparent opacity={0.55} />
      </line>

      {TOWNS.map((town) => (
        <Pin
          key={town.id}
          town={town}
          active={town.id === focus.id}
          onSelect={onSelect}
        />
      ))}
    </group>
  );
}

export default function WorldGlobe3D({
  selected,
  onSelect,
  className = "",
}: {
  selected: WorldTown;
  onSelect: (town: WorldTown) => void;
  className?: string;
}) {
  return (
    <div className={`relative ${className}`}>
      <Canvas
        dpr={[1, 2]}
        camera={{ position: [0, 0, 3.05], fov: 42 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.9} />
        <directionalLight position={[2.5, 2, 3]} intensity={1.4} />
        <Globe focus={selected} onSelect={onSelect} />
        <OrbitControls
          enablePan={false}
          enableZoom
          minDistance={1.55}
          maxDistance={5}
          rotateSpeed={0.5}
          dampingFactor={0.08}
        />
      </Canvas>
      <div className="pointer-events-none absolute bottom-1 left-2 mono text-[8px] tracking-[0.14em] text-muted/70">
        DRAG TO ROTATE · CLICK A PIN
      </div>
    </div>
  );
}
