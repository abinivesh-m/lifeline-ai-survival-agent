"use client";

import { Canvas } from "@react-three/fiber";
import { Html, OrbitControls } from "@react-three/drei";
import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { COLORS, lifeline } from "@/lib/lifeline";
import { useVisible } from "@/lib/useVisible";
import { ClampDelta } from "./ClampDelta";

type Mode = "offline" | "online";

const LINES: Record<Mode, [string, string][]> = {
  offline: [
    ["$ ipconfig /all  |  findstr Media", "Media State . . . . . . : Media disconnected"],
    ["$ nvidia-smi --query-gpu=name,memory.total", "NVIDIA GeForce RTX 3050 6GB Laptop GPU, 6144 MiB"],
    ["$ python agent.py --offline --yes", "8 steps, 0 network calls, 0 API keys read"],
    ["$ python a_star.py", "A* 4.2 km blocked -> 7.8 km found (40.0% saved)"],
    ["$ python allocator.py --mode policy", "70 L heart + 30 L lungs = 100 L, validator pass"],
    ["note", "the core is offline. no local model is claimed for Open Weight."],
  ],
  online: [
    [
      "$ python openweight.py",
      lifeline.openweight.available
        ? `${lifeline.openweight.valid_runs}/${lifeline.openweight.runs} runs valid · 70 L / 30 L · ${lifeline.openweight.latencies_s[0] ?? 0}s`
        : "no valid run on file - run openweight.py",
    ],
    ["$ python allocator.py --mode auto", "wonder-high returned 70 L / 30 L in 2.1 s"],
    ["$ python capture_sam.py", "9 frames, masks decoded, $0.02"],
    ["$ python capture_voice.py", "Tamil transcript, $0.000539"],
    ["note", "Glimmer is 18 GB. This 6 GB card cannot hold it: partner inference only."],
    ["status", "one partner-hosted open model, no fabricated local weights"],
  ],
};

function useScreenTexture(mode: Mode) {
  const [texture, setTexture] = useState<THREE.CanvasTexture | null>(null);

  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 640;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.fillStyle = "#04100f";
    ctx.fillRect(0, 0, 1024, 640);

    // scanlines
    ctx.fillStyle = "rgba(45,212,191,0.045)";
    for (let y = 0; y < 640; y += 4) ctx.fillRect(0, y, 1024, 1);

    ctx.fillStyle = mode === "offline" ? "#f5b942" : "#2dd4bf";
    ctx.font = "bold 26px Consolas, monospace";
    ctx.fillText(mode === "offline" ? "AIRPLANE MODE  ·  OFFLINE" : "PARTNER INFERENCE  ·  ONLINE", 36, 56);

    ctx.fillStyle = "#86a0ab";
    ctx.font = "19px Consolas, monospace";
    ctx.fillText("lifeline@kottur  rt x 3050  6 gb vram", 36, 92);

    let y = 150;
    for (const [cmd, out] of LINES[mode]) {
      ctx.fillStyle = "#2dd4bf";
      ctx.font = "21px Consolas, monospace";
      ctx.fillText(cmd.slice(0, 74), 36, y);
      ctx.fillStyle = "#e8f3f6";
      ctx.font = "19px Consolas, monospace";
      const text = out.slice(0, 84);
      ctx.fillText(text, 52, y + 30);
      y += 78;
    }

    ctx.fillStyle = mode === "offline" ? "#f5b942" : "#2dd4bf";
    ctx.font = "bold 20px Consolas, monospace";
    ctx.fillText("lifeline@kottur:~$ ", 36, 612);
    ctx.fillStyle = "#e8f3f6";
    ctx.fillRect(258, 590, 12, 26);

    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.needsUpdate = true;
    setTexture(tex);
    return () => tex.dispose();
  }, [mode]);

  return texture;
}

function Laptop({ mode }: { mode: Mode }) {
  const texture = useScreenTexture(mode);
  return (
    <group rotation={[0, -0.18, 0]} position={[0, -0.5, 0]}>
      {/* base */}
      <mesh position={[0, -0.35, 0.55]} rotation={[-Math.PI / 2.6, 0, 0]}>
        <boxGeometry args={[3.5, 2.1, 0.08]} />
        <meshStandardMaterial color="#1b2b33" metalness={0.75} roughness={0.32} />
      </mesh>
      {/* keyboard hint */}
      <mesh position={[0, -0.3, 0.6]} rotation={[-Math.PI / 2.6, 0, 0]}>
        <planeGeometry args={[3.2, 1.8]} />
        <meshStandardMaterial color="#0b171d" roughness={0.9} />
      </mesh>
      {/* screen back */}
      <mesh position={[0, 0.72, -0.52]} rotation={[0.16, 0, 0]}>
        <boxGeometry args={[3.6, 2.16, 0.09]} />
        <meshStandardMaterial color="#16262e" metalness={0.7} roughness={0.35} />
      </mesh>
      {/* screen */}
      <mesh position={[0, 0.72, -0.462]} rotation={[0.16, 0, 0]}>
        <planeGeometry args={[3.4, 1.98]} />
        {texture ? (
          <meshBasicMaterial map={texture} toneMapped={false} />
        ) : (
          <meshBasicMaterial color="#04100f" />
        )}
      </mesh>
      <pointLight position={[0, 0.8, -0.1]} intensity={3} distance={4} color={mode === "offline" ? COLORS.amber : COLORS.teal} />
    </group>
  );
}

function Holograms({ mode }: { mode: Mode }) {
  return (
    <group>
      {[
        { pos: [-3.1, 1.05, -0.7] as [number, number, number], label: "BASETEN", detail: "muse-spark-open-1026 · qualifying", colour: COLORS.teal },
        { pos: [3.0, 0.75, -0.9] as [number, number, number], label: "MODAL", detail: "glimmer · 18 GB · not deployed", colour: COLORS.amber },
        { pos: [2.6, -0.6, 0.6] as [number, number, number], label: "THIS LAPTOP", detail: "RTX 3050 6GB · core <1.2 GB", colour: COLORS.lung },
      ].map((holo) => {
        const active = mode === "online" ? holo.label !== "THIS LAPTOP" : holo.label === "THIS LAPTOP";
        return (
          <group key={holo.label} position={holo.pos}>
            <mesh rotation={[0, 0, 0]}>
              <icosahedronGeometry args={[0.34, 1]} />
              <meshBasicMaterial
                color={holo.colour}
                wireframe
                transparent
                opacity={active ? 0.85 : 0.18}
              />
            </mesh>
            <Html center distanceFactor={8} position={[0, 0.62, 0]}>
              <div
                className="whitespace-nowrap rounded border px-2 py-1 text-center backdrop-blur-sm"
                style={{
                  borderColor: active ? `${holo.colour}88` : "rgba(31,53,64,.7)",
                  background: "rgba(6,13,17,.7)",
                  opacity: active ? 1 : 0.45,
                }}
              >
                <div className="mono text-[9px] tracking-[0.16em]" style={{ color: holo.colour }}>
                  {holo.label}
                </div>
                <div className="mono text-[8px] text-muted">{holo.detail}</div>
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}

export default function OfflineProof3D() {
  const [mode, setMode] = useState<Mode>("offline");
  const options = useMemo(() => ["offline", "online"] as Mode[], []);
  const { ref: frameRef, visible } = useVisible<HTMLDivElement>();

  return (
    <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
      <div
        ref={frameRef}
        className="relative h-[430px] overflow-hidden rounded-xl border border-line bg-[#050c10]"
      >
        <Canvas
          frameloop={visible ? "always" : "never"}
          dpr={[1, 1.6]}
          camera={{ position: [0, 1.2, 6.4], fov: 42 }}
        >
          <ClampDelta />
          <ambientLight intensity={0.5} />
          <directionalLight position={[3, 5, 4]} intensity={1.1} />
          <pointLight position={[-4, 2, 3]} intensity={12} color={COLORS.blood} distance={12} />
          <Laptop mode={mode} />
          <Holograms mode={mode} />
          <OrbitControls enablePan={false} minDistance={5} maxDistance={9} maxPolarAngle={Math.PI * 0.62} />
        </Canvas>

        <div className="absolute left-4 top-4 rounded border border-line/70 bg-black/70 px-2 py-1 mono text-[9px] tracking-[0.18em] text-muted">
          RTX 3050 6GB LAPTOP GPU · CORE &lt;1.2 GB · AIRPLANE MODE · NO API KEY
        </div>
        <div
          className={`absolute right-4 top-4 rounded border px-2 py-1 mono text-[9px] ${
            mode === "offline"
              ? "border-amber/50 bg-amber/10 text-amber"
              : "border-teal/50 bg-teal/10 text-teal"
          }`}
        >
          {mode === "offline" ? "AIRPLANE MODE ON" : "NETWORK UP"}
        </div>
        <div className="absolute inset-x-4 bottom-4 rounded border border-line/70 bg-black/70 px-2 py-1 mono text-[8.5px] leading-relaxed text-muted">
          RTX 3050 6GB Laptop GPU · deterministic core &lt;1.2GB · LIFELINE_OFFLINE=1
          airplane mode · no API key
        </div>
      </div>

      <div className="flex flex-col gap-3">
        <div className="rounded-xl border border-line bg-panel/80 p-4">
          <div className="mono text-[10px] tracking-[0.18em] text-muted">TOGGLE THE WIRE</div>
          <div className="mt-2 flex gap-2">
            {options.map((option) => (
              <button
                key={option}
                onClick={() => setMode(option)}
                className={`flex-1 rounded-md border px-3 py-2 mono text-[10px] uppercase tracking-[0.12em] transition ${
                  mode === option
                    ? option === "offline"
                      ? "border-amber/60 bg-amber/10 text-amber"
                      : "border-teal/60 bg-teal/10 text-teal"
                    : "border-line text-muted hover:border-muted/60"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
          <p className="mt-3 text-[11.5px] leading-relaxed text-muted">
            {mode === "offline"
              ? "Wi-Fi off. LIFELINE_OFFLINE=1. The deterministic core — A*, Kahn sort, the 70/30 validator, the ledger — runs entirely in under 1.2 GB on this laptop. No API key is read."
              : "Partner inference is the qualifying path for Open Weight: muse-spark-open-1026 on Baseten, with the stored proof below. Muse Glimmer needs 18 GB of VRAM, so it is not claimed on this laptop."}
          </p>
        </div>

        <div className="rounded-xl border border-teal/25 bg-teal/5 p-4">
          <div className="mono text-[10px] tracking-[0.18em] text-teal">WHAT IS CLAIMED, AND WHERE</div>
          <div className="mt-2 space-y-2">
            <div className="flex gap-2">
              <span className="mono shrink-0 pt-0.5 text-[8px] tracking-[0.1em] text-teal">CLAIM</span>
              <p className="text-[11px] leading-relaxed text-ink/80">
                The Open Weight entry is{" "}
                <span className="mono text-teal">muse-spark-open-1026</span>, partner-hosted on
                Baseten. Those runs are stored verbatim, re-validated locally and counted above.
              </p>
            </div>
            <div className="flex gap-2">
              <span className="mono shrink-0 pt-0.5 text-[8px] tracking-[0.1em] text-muted">
                NOT CLAIMED
              </span>
              <p className="text-[11px] leading-relaxed text-muted">
                Any local model as the prize entry. This 6 GB laptop runs the deterministic core
                only. Glimmer&apos;s 18 GB does not fit, so it is partner inference or nothing.
              </p>
            </div>
          </div>
        </div>

        <div
          className={`rounded-xl border p-4 ${
            lifeline.openweight.available
              ? "border-teal/30 bg-teal/5"
              : "border-blood/30 bg-blood/5"
          }`}
        >
          <div className="flex items-baseline justify-between">
            <div className="mono text-[10px] tracking-[0.18em] text-teal">OPEN WEIGHT PROOF</div>
            <span className="mono text-[9px] text-muted">
              {lifeline.openweight.valid_runs}/{lifeline.openweight.runs} runs valid
            </span>
          </div>
          <div className="mono mt-1.5 text-[11px] text-ink">
            {lifeline.openweight.provider} · {lifeline.openweight.model}
          </div>
          <p className="mt-1 text-[10.5px] leading-relaxed text-muted">
            {lifeline.openweight.available
              ? `${lifeline.openweight.valid_runs}/${lifeline.openweight.runs} runs valid · ${lifeline.openweight.latencies_s.join(" s and ")} s · ${lifeline.openweight.allocation?.hospital} L / ${lifeline.openweight.allocation?.water_pump} L. Stored verbatim in artifacts/openweight_proof.json and re-validated locally, not trusted from the model.`
              : "No valid run on file yet. Run python openweight.py before recording the demo."}
          </p>
          <div className="mt-1.5 flex gap-1.5">
            <span className="rounded border border-line px-1.5 py-0.5 mono text-[8px] text-muted">
              reasoning tokens billed against max_tokens
            </span>
            <span className="rounded border border-line px-1.5 py-0.5 mono text-[8px] text-muted">
              Glimmer · not deployed
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

