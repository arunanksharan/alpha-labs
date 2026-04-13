"use client";

import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Text, Grid } from "@react-three/drei";
import * as THREE from "three";

import type { FC } from "react";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const STRIKES = 20; // x-axis points
const EXPIRIES = 12; // y-axis points
const MONEYNESS_MIN = 0.8;
const MONEYNESS_MAX = 1.2;
const EXPIRY_MIN = 1; // months
const EXPIRY_MAX = 12;

// color stops
const COLOR_LOW = new THREE.Color("#06b6d4"); // cyan
const COLOR_MID = new THREE.Color("#8b5cf6"); // violet
const COLOR_HIGH = new THREE.Color("#ef4444"); // red

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateDemoData(): { strike: number; expiry: number; iv: number }[] {
  const pts: { strike: number; expiry: number; iv: number }[] = [];
  for (let ey = 0; ey < EXPIRIES; ey++) {
    const expiry = EXPIRY_MIN + (ey / (EXPIRIES - 1)) * (EXPIRY_MAX - EXPIRY_MIN);
    for (let sx = 0; sx < STRIKES; sx++) {
      const moneyness =
        MONEYNESS_MIN + (sx / (STRIKES - 1)) * (MONEYNESS_MAX - MONEYNESS_MIN);
      const noise = (Math.random() - 0.5) * 0.015;
      const iv =
        0.2 +
        0.1 * Math.pow(moneyness - 1, 2) +
        0.01 * expiry +
        noise;
      pts.push({ strike: moneyness, expiry, iv });
    }
  }
  return pts;
}

function ivToColor(iv: number): THREE.Color {
  // map iv 0.1..0.5 -> 0..1
  const t = THREE.MathUtils.clamp((iv - 0.1) / 0.4, 0, 1);
  if (t < 0.5) {
    return COLOR_LOW.clone().lerp(COLOR_MID, t * 2);
  }
  return COLOR_MID.clone().lerp(COLOR_HIGH, (t - 0.5) * 2);
}

// ---------------------------------------------------------------------------
// Surface mesh component
// ---------------------------------------------------------------------------

interface SurfaceMeshProps {
  data: { strike: number; expiry: number; iv: number }[];
}

function SurfaceMesh({ data }: SurfaceMeshProps) {
  const meshRef = useRef<THREE.Mesh>(null!);
  const timeRef = useRef(0);

  // Build geometry once, then animate
  const { geometry, basePositions } = useMemo(() => {
    const geo = new THREE.PlaneGeometry(6, 4, STRIKES - 1, EXPIRIES - 1);
    const pos = geo.attributes.position;
    const colors = new Float32Array(pos.count * 3);

    for (let ey = 0; ey < EXPIRIES; ey++) {
      for (let sx = 0; sx < STRIKES; sx++) {
        const idx = ey * STRIKES + sx;
        const d = data[idx];
        if (!d) continue;

        // map to spatial coords
        const x = ((d.strike - MONEYNESS_MIN) / (MONEYNESS_MAX - MONEYNESS_MIN) - 0.5) * 6;
        const z = ((d.expiry - EXPIRY_MIN) / (EXPIRY_MAX - EXPIRY_MIN) - 0.5) * 4;
        const y = ((d.iv - 0.1) / 0.4) * 3; // height scale

        pos.setXYZ(idx, x, y, z);

        const c = ivToColor(d.iv);
        colors[idx * 3] = c.r;
        colors[idx * 3 + 1] = c.g;
        colors[idx * 3 + 2] = c.b;
      }
    }

    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    geo.computeVertexNormals();

    // store base positions for animation
    const base = new Float32Array(pos.array);

    return { geometry: geo, basePositions: base };
  }, [data]);

  // Gentle wave animation
  useFrame((_, delta) => {
    timeRef.current += delta;
    const t = timeRef.current;
    const pos = geometry.attributes.position as THREE.BufferAttribute;

    for (let i = 0; i < pos.count; i++) {
      const bx = basePositions[i * 3];
      const bz = basePositions[i * 3 + 2];
      const by = basePositions[i * 3 + 1];
      const wave = Math.sin(bx * 1.2 + t * 0.8) * Math.cos(bz * 1.0 + t * 0.6) * 0.06;
      pos.setY(i, by + wave);
    }

    pos.needsUpdate = true;
  });

  return (
    <mesh ref={meshRef} geometry={geometry} rotation={[-Math.PI * 0.15, 0, 0]}>
      <meshStandardMaterial
        vertexColors
        side={THREE.DoubleSide}
        metalness={0.1}
        roughness={0.55}
        transparent
        opacity={0.92}
      />
    </mesh>
  );
}

// ---------------------------------------------------------------------------
// Wireframe overlay for visual depth
// ---------------------------------------------------------------------------

function SurfaceWireframe({ data }: SurfaceMeshProps) {
  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(6, 4, STRIKES - 1, EXPIRIES - 1);
    const pos = geo.attributes.position;

    for (let ey = 0; ey < EXPIRIES; ey++) {
      for (let sx = 0; sx < STRIKES; sx++) {
        const idx = ey * STRIKES + sx;
        const d = data[idx];
        if (!d) continue;

        const x = ((d.strike - MONEYNESS_MIN) / (MONEYNESS_MAX - MONEYNESS_MIN) - 0.5) * 6;
        const z = ((d.expiry - EXPIRY_MIN) / (EXPIRY_MAX - EXPIRY_MIN) - 0.5) * 4;
        const y = ((d.iv - 0.1) / 0.4) * 3;

        pos.setXYZ(idx, x, y, z);
      }
    }

    geo.computeVertexNormals();
    return geo;
  }, [data]);

  return (
    <lineSegments rotation={[-Math.PI * 0.15, 0, 0]}>
      <wireframeGeometry args={[geometry]} />
      <lineBasicMaterial color="#a1a1aa" transparent opacity={0.08} />
    </lineSegments>
  );
}

// ---------------------------------------------------------------------------
// Axis labels
// ---------------------------------------------------------------------------

function AxisLabels() {
  const baseProps = {
    fontSize: 0.22,
    color: "#a1a1aa",
    anchorX: "center" as const,
    anchorY: "middle" as const,
  };

  return (
    <group>
      {/* X axis label */}
      <Text position={[0, -0.6, 2.8]} {...baseProps}>
        Strike (Moneyness)
      </Text>
      {/* Z axis label */}
      <Text position={[3.8, -0.6, 0]} rotation={[0, -Math.PI / 2, 0]} {...baseProps}>
        Expiry (Months)
      </Text>
      {/* Y axis label */}
      <Text position={[-3.8, 1.2, 0]} rotation={[0, 0, Math.PI / 2]} {...baseProps}>
        Implied Vol
      </Text>

      {/* X tick marks */}
      {[0.8, 0.9, 1.0, 1.1, 1.2].map((v) => {
        const x = ((v - MONEYNESS_MIN) / (MONEYNESS_MAX - MONEYNESS_MIN) - 0.5) * 6;
        return (
          <Text key={`x-${v}`} position={[x, -0.4, 2.4]} fontSize={0.16} color="#71717a">
            {v.toFixed(1)}
          </Text>
        );
      })}

      {/* Z tick marks */}
      {[1, 3, 6, 9, 12].map((m) => {
        const z = ((m - EXPIRY_MIN) / (EXPIRY_MAX - EXPIRY_MIN) - 0.5) * 4;
        return (
          <Text
            key={`z-${m}`}
            position={[3.4, -0.4, z]}
            fontSize={0.16}
            color="#71717a"
            rotation={[0, -Math.PI / 2, 0]}
          >
            {m}M
          </Text>
        );
      })}
    </group>
  );
}

// ---------------------------------------------------------------------------
// Main scene export
// ---------------------------------------------------------------------------

interface SceneProps {
  data?: { strike: number; expiry: number; iv: number }[];
}

const VolSurfaceScene: FC<SceneProps> = ({ data }) => {
  const surfaceData = useMemo(() => data ?? generateDemoData(), [data]);

  return (
    <Canvas
      camera={{ position: [5, 4, 5], fov: 45 }}
      style={{ background: "transparent" }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
    >
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 8, 5]} intensity={0.8} color="#f4f4f5" />
      <directionalLight position={[-3, 4, -3]} intensity={0.3} color="#06b6d4" />

      {/* Grid floor */}
      <Grid
        args={[12, 12]}
        position={[0, -0.5, 0]}
        cellSize={0.5}
        cellThickness={0.3}
        cellColor="#27272a"
        sectionSize={2}
        sectionThickness={0.6}
        sectionColor="#3f3f46"
        fadeDistance={14}
        infiniteGrid
      />

      {/* The surface */}
      <SurfaceMesh data={surfaceData} />
      <SurfaceWireframe data={surfaceData} />

      {/* Labels */}
      <AxisLabels />

      {/* Controls */}
      <OrbitControls
        enablePan
        enableZoom
        enableRotate
        autoRotate
        autoRotateSpeed={0.5}
        minDistance={4}
        maxDistance={16}
        maxPolarAngle={Math.PI * 0.48}
      />
    </Canvas>
  );
};

export default VolSurfaceScene;
