/**
 * frontend/src/components/ScoreCircle.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Animated SVG circle that shows a risk score (0–100).
 *
 * Visual design:
 *   - Outer circle = full range (0–100)
 *   - Inner arc    = score fill, colour-coded by tier
 *   - Center text  = numeric score
 *
 * The arc is drawn using SVG stroke-dasharray / stroke-dashoffset — a common
 * technique for circular progress indicators:
 *   dasharray  = circumference (total length of the path)
 *   dashoffset = circumference × (1 – score/100)
 *   → When offset = 0, the full arc is drawn (score 100)
 *   → When offset = circumference, nothing is drawn (score 0)
 *
 * The component animates from 0 to the final score on mount.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useEffect, useState } from 'react';

// ─── Tier colours ─────────────────────────────────────────────────────────────

/** Returns the stroke colour for the arc based on the risk score. */
function arcColour(score: number): string {
  if (score >= 90) return '#ef4444'; // red-500:    critical
  if (score >= 70) return '#f97316'; // orange-500: high
  if (score >= 40) return '#eab308'; // yellow-500: medium
  return '#22c55e';                  // green-500:  low
}

/** Returns a label string for the score tier. */
function tierLabel(score: number): string {
  if (score >= 90) return 'CRITICAL';
  if (score >= 70) return 'HIGH';
  if (score >= 40) return 'MEDIUM';
  return 'LOW';
}

// ─── Props ────────────────────────────────────────────────────────────────────

interface ScoreCircleProps {
  /** Risk score 0–100. */
  score: number;
  /** Diameter of the SVG in pixels. Default 160. */
  size?: number;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function ScoreCircle({ score, size = 160 }: ScoreCircleProps) {
  // Animated display score — starts at 0, animates to `score`
  const [displayScore, setDisplayScore] = useState(0);

  // Animate the score upward over ~600ms on mount or when `score` changes
  useEffect(() => {
    const steps = 30;                    // number of animation frames
    const increment = score / steps;     // how much to add per frame
    let current = 0;
    let frame = 0;

    const timer = setInterval(() => {
      frame += 1;
      current = Math.min(score, increment * frame);
      setDisplayScore(Math.round(current));
      if (frame >= steps) clearInterval(timer);
    }, 20); // 20ms per frame ≈ 50fps

    return () => clearInterval(timer); // cleanup if component unmounts mid-animation
  }, [score]);

  // ── SVG geometry ────────────────────────────────────────────────────────────
  const center = size / 2;
  const strokeWidth = size * 0.075;          // ~12px for size=160
  const radius = center - strokeWidth;        // radius of the arc path
  const circumference = 2 * Math.PI * radius; // total arc length

  // How much of the arc to leave unfilled (the "empty" portion)
  const offset = circumference * (1 - displayScore / 100);

  const colour = arcColour(score);

  return (
    <div className="flex flex-col items-center gap-2">
      {/* SVG circle */}
      <svg width={size} height={size} className="-rotate-90">
        {/* Background ring — always full circle, dark gray */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#1f2937" // gray-800
          strokeWidth={strokeWidth}
        />
        {/* Score arc — fills proportionally to the score */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={colour}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.05s linear' }}
        />
        {/* Score text — rotate back to upright since the SVG is rotated -90° */}
        <text
          x={center}
          y={center}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={colour}
          fontSize={size * 0.22}
          fontWeight="bold"
          fontFamily="monospace"
          style={{ transform: `rotate(90deg)`, transformOrigin: `${center}px ${center}px` }}
        >
          {displayScore}
        </text>
      </svg>

      {/* Tier label below the circle */}
      <span
        className="text-xs font-bold tracking-widest px-3 py-1 rounded-full border"
        style={{
          color: colour,
          borderColor: colour,
          backgroundColor: colour + '1a', // 10% opacity background
        }}
      >
        {tierLabel(score)}
      </span>
    </div>
  );
}
