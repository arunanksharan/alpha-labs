"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, RoundedBox } from "@react-three/drei";
import * as THREE from "three";

import type { FC } from "react";

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "GOOG", "TSLA", "META"];

// Realistic tech-stock correlation matrix (symmetric, diagonal = 1)
const DEFAULT_CORRELATIONS: number[][] = [
  // AAPL   MSFT   NVDA   GOOG   TSLA   META
  [1.0,   0.78,  0.68,  0.72,  0.38,  0.65],  // AAPL
  [0.78,  1.0,   0.72,  0.76,  0.35,  0.69],  // MSFT
  [0.68,  0.72,  1.0,   0.65,  0.42,  0.58],  // NVDA
  [0.72,  0.76,  0.65,  1.0,   0.33,  0.71],  // GOOG
  [0.38,  0.35,  0.42,  0.33,  1.0,   0.29],  // TSLA
  [0.65,  0.69,  0.58,  0.71,  0.29,  1.0],   // META
];

// ---------------------------------------------------------------------------
// Animated bar component
// ---------------------------------------------------------------------------

interface BarProps {
  position: [number, number, number];
  targetHeight: number;
  color: string;
  opacity: number;
  delay: number; // stagger entrance
}

function Bar({ position, targetHeight, color, opacity, delay }: BarProps) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const progressRef = useRef(0);
  const startedRef = useRef(false);
  const elapsedRef = useRef(0);

  useFrame((_, delta) => {
    elapsedRef.current += delta;

    // Wait for delay before starting animation
    if (elapsedRef.current < delay) return;

    if (!startedRef.current) {
      startedRef.current = true;
    }

    if (progressRef.current < 1) {
      // Ease-out cubic
      progressRef.current = Math.min(1, progressRef.current + delta * 1.8);
      const eased = 1 - Math.pow(1 - progressRef.current, 3);
      const h = Math.max(0.02, targetHeight * eased);

      meshRef.current.scale.y = eased;
      meshRef.current.position.y = h / 2;
    }
  });

  const h = Math.max(0.02, targetHeight);

  return (
    <group position={position}>
      <RoundedBox
        ref={meshRef}
        args={[0.65, h, 0.65]}
        radius={0.06}
        smoothness={4}
        position={[0, h / 2, 0]}
        scale={[1, 0.001, 1]}
      >
        <meshStandardMaterial
          color={color}
          transparent
          opacity={opacity}
          metalness={0.15}
          roughness={0.5}
        />
      </RoundedBox>
    </group>
  );
}

// ---------------------------------------------------------------------------
// Labels
// ---------------------------------------------------------------------------

interface LabelProps {
  tickers: string[];
  gridSize: number;
  spacing: number;
}

function Labels({ tickers, gridSize, spacing }: LabelProps) {
  const offset = ((gridSize - 1) * spacing) / 2;

  return (
    <group>
      {/* X-axis labels (along x) */}
      {tickers.map((t, i) => (
        <Text
          key={`x-${t}`}
          position={[i * spacing - offset, -0.15, offset + 0.9]}
          fontSize={0.24}
          color="#a1a1aa"
          anchorX="center"
          anchorY="middle"
          rotation={[-Math.PI * 0.3, 0, 0]}
        >
          {t}
        </Text>
      ))}

      {/* Z-axis labels (along z) */}
      {tickers.map((t, i) => (
        <Text
          key={`z-${t}`}
          position={[-offset - 0.9, -0.15, i * spacing - offset]}
          fontSize={0.24}
          color="#a1a1aa"
          anchorX="center"
          anchorY="middle"
          rotation={[-Math.PI * 0.3, Math.PI * 0.25, 0]}
        >
          {t}
        </Text>
      ))}

      {/* Y-axis label */}
      <Text
        position={[-offset - 1.5, 1.5, -offset - 1.5]}
        fontSize={0.2}
        color="#71717a"
        rotation={[0, Math.PI / 4, Math.PI / 2]}
      >
        |Correlation|
      </Text>
    </group>
  );
}

// ---------------------------------------------------------------------------
// Floor plane
// ---------------------------------------------------------------------------

function FloorGrid({ size }: { size: number }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.02, 0]} receiveShadow>
      <planeGeometry args={[size + 2, size + 2]} />
      <meshStandardMaterial color="#18181b" transparent opacity={0.6} />
    </mesh>
  );
}

// ---------------------------------------------------------------------------
// Main scene export
// ---------------------------------------------------------------------------

interface SceneProps {
  tickers?: string[];
  correlations?: number[][];
}

const CorrelationHeatmapScene: FC<SceneProps> = ({ tickers, correlations }) => {
  const tickerList = tickers ?? DEFAULT_TICKERS;
  const corrMatrix = correlations ?? DEFAULT_CORRELATIONS;
  const n = tickerList.length;
  const spacing = 1.0;

  const bars = useMemo(() => {
    const items: {
      key: string;
      position: [number, number, number];
      height: number;
      color: string;
      opacity: number;
      delay: number;
    }[] = [];

    const offset = ((n - 1) * spacing) / 2;

    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        // Skip diagonal (correlation with self is always 1, not interesting)
        if (i === j) continue;

        const corr = corrMatrix[i]?.[j] ?? 0;
        const absCorr = Math.abs(corr);
        const height = absCorr * 3; // scale to max 3 units

        const color = corr >= 0 ? "#22c55e" : "#ef4444";
        const opacity = 0.4 + absCorr * 0.55; // 0.4 min to 0.95

        items.push({
          key: `${i}-${j}`,
          position: [i * spacing - offset, 0, j * spacing - offset],
          height,
          color,
          opacity,
          delay: (i * n + j) * 0.03, // stagger
        });
      }
    }

    return items;
  }, [n, corrMatrix, spacing]);

  const gridExtent = n * spacing;

  return (
    <Canvas
      camera={{ position: [6, 5, 6], fov: 42 }}
      style={{ background: "transparent" }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
    >
      {/* Lighting */}
      <ambientLight intensity={0.45} />
      <directionalLight position={[6, 10, 6]} intensity={0.7} color="#f4f4f5" />
      <directionalLight position={[-4, 6, -4]} intensity={0.25} color="#22c55e" />
      <pointLight position={[0, 5, 0]} intensity={0.3} color="#8b5cf6" />

      {/* Floor */}
      <FloorGrid size={gridExtent} />

      {/* Bars */}
      {bars.map((b) => (
        <Bar
          key={b.key}
          position={b.position}
          targetHeight={b.height}
          color={b.color}
          opacity={b.opacity}
          delay={b.delay}
        />
      ))}

      {/* Labels */}
      <Labels tickers={tickerList} gridSize={n} spacing={spacing} />

      {/* Controls */}
      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        autoRotate
        autoRotateSpeed={0.5}
        minDistance={4}
        maxDistance={18}
        maxPolarAngle={Math.PI * 0.45}
      />
    </Canvas>
  );
};

export default CorrelationHeatmapScene;
