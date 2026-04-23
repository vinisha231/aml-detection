/**
 * frontend/src/components/GraphViewer.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Interactive transaction network graph for an account.
 *
 * Renders a force-directed graph showing:
 *   - Nodes: accounts in the network (colored by risk tier)
 *   - Edges: money flows (thickness = transaction volume)
 *   - Focal node: the account being investigated (highlighted)
 *
 * Uses react-force-graph-2d under the hood, which wraps d3-force.
 * Force simulation pushes nodes apart until they find stable positions.
 *
 * Color coding:
 *   Red   → critical risk (score ≥ 90)
 *   Orange→ high risk     (score ≥ 70)
 *   Yellow→ medium risk   (score ≥ 40)
 *   Gray  → low risk / unknown
 *   Blue  → the focal account (center of investigation)
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useRef, useCallback, useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { GraphData } from '../api/client';

// ─── Props ────────────────────────────────────────────────────────────────────

interface GraphViewerProps {
  /** The graph data returned by GET /accounts/{id}/graph */
  data: GraphData;
  /** The account ID currently being investigated (will be highlighted) */
  focalAccountId: string;
  /** Width in pixels. Defaults to container width. */
  width?: number;
  /** Height in pixels. */
  height?: number;
}

// ─── Colour helpers ───────────────────────────────────────────────────────────

/**
 * Returns a hex colour string based on the node's risk score.
 *
 * @param score  - Risk score 0–100 (or undefined if not scored)
 * @param isFocal - Whether this is the central account being investigated
 */
function nodeColour(score: number | undefined, isFocal: boolean): string {
  if (isFocal) return '#3b82f6';       // blue-500: focal account stands out
  if (score === undefined) return '#6b7280'; // gray-500: unscored accounts

  if (score >= 90) return '#ef4444';   // red-500:    critical
  if (score >= 70) return '#f97316';   // orange-500: high
  if (score >= 40) return '#eab308';   // yellow-500: medium
  return '#6b7280';                    // gray-500:   low
}

/**
 * Returns node radius based on whether it's the focal account.
 * Bigger node = more visual weight = easier to find center.
 */
function nodeRadius(isFocal: boolean): number {
  return isFocal ? 10 : 6;
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function GraphViewer({
  data,
  focalAccountId,
  width = 800,
  height = 500,
}: GraphViewerProps) {
  // Reference to the ForceGraph2D component so we can call its methods
  // (e.g., zoom to fit after data loads)
  const graphRef = useRef<any>(null);

  // Tooltip state: which node is the user hovering over?
  const [hoveredNode, setHoveredNode] = useState<any>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // After data loads, zoom the camera to fit all nodes in view
  useEffect(() => {
    if (graphRef.current) {
      // Small delay lets the force simulation settle first
      setTimeout(() => graphRef.current?.zoomToFit(400, 40), 500);
    }
  }, [data]);

  // ── Node rendering ──────────────────────────────────────────────────────────
  // We draw nodes manually on canvas for full control over appearance.
  const drawNode = useCallback(
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isFocal = node.id === focalAccountId;
      const r = nodeRadius(isFocal);
      const colour = nodeColour(node.risk_score, isFocal);

      // Draw filled circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.fillStyle = colour;
      ctx.fill();

      // Draw white border for focal node to make it pop
      if (isFocal) {
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }

      // Draw account ID label (only when zoomed in enough to read it)
      if (globalScale >= 1.5) {
        ctx.font = `${10 / globalScale}px monospace`;
        ctx.fillStyle = '#e5e7eb'; // gray-200
        ctx.textAlign = 'center';
        ctx.fillText(node.id, node.x, node.y + r + 8 / globalScale);
      }
    },
    [focalAccountId]
  );

  // ── Link rendering ──────────────────────────────────────────────────────────
  // Link width scales with transaction volume (weight).
  // This makes high-volume flows visually thicker.
  const linkWidth = useCallback((link: any) => {
    const weight = link.weight ?? 0;
    // Log scale so $1M and $10k don't differ by 1000x in thickness
    return Math.max(1, Math.log10(weight / 1000 + 1) * 2);
  }, []);

  // ── Hover handlers ──────────────────────────────────────────────────────────
  const handleNodeHover = useCallback((node: any, prevNode: any) => {
    setHoveredNode(node);
  }, []);

  const handleNodeClick = useCallback((node: any) => {
    // Navigate to the account detail page on click
    window.location.href = `/accounts/${node.id}`;
  }, []);

  // ── Empty state ─────────────────────────────────────────────────────────────
  if (!data.nodes.length) {
    return (
      <div
        className="flex items-center justify-center bg-gray-900 rounded-xl border border-gray-800"
        style={{ width, height }}
      >
        <p className="text-gray-500 text-sm">No network data available.</p>
      </div>
    );
  }

  return (
    <div className="relative rounded-xl overflow-hidden border border-gray-800">
      {/* Force graph canvas */}
      <ForceGraph2D
        ref={graphRef}
        graphData={data}
        width={width}
        height={height}
        backgroundColor="#111827" // gray-900
        nodeCanvasObject={drawNode}
        nodeCanvasObjectMode={() => 'replace'}
        linkWidth={linkWidth}
        linkColor={() => '#374151'} // gray-700
        linkDirectionalArrowLength={6}
        linkDirectionalArrowRelPos={1}
        onNodeHover={handleNodeHover}
        onNodeClick={handleNodeClick}
        cooldownTicks={100}
      />

      {/* Hover tooltip */}
      {hoveredNode && (
        <div
          className="absolute pointer-events-none bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs shadow-xl"
          style={{ top: 16, right: 16, minWidth: 180 }}
        >
          <div className="font-mono text-blue-400 font-bold mb-1">
            {hoveredNode.id}
          </div>
          {hoveredNode.risk_score !== undefined && (
            <div className="text-gray-300">
              Risk Score:{' '}
              <span className="font-bold text-white">
                {hoveredNode.risk_score.toFixed(1)}
              </span>
            </div>
          )}
          {hoveredNode.typology && (
            <div className="text-gray-400 mt-1">
              Typology: <span className="text-yellow-400">{hoveredNode.typology}</span>
            </div>
          )}
          <div className="text-gray-600 mt-2 italic">Click to open account</div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-3 left-3 bg-gray-900 bg-opacity-90 rounded-lg p-2 text-xs space-y-1">
        {[
          { colour: '#3b82f6', label: 'Focal account' },
          { colour: '#ef4444', label: 'Critical (≥90)' },
          { colour: '#f97316', label: 'High (≥70)' },
          { colour: '#eab308', label: 'Medium (≥40)' },
          { colour: '#6b7280', label: 'Low / Unscored' },
        ].map(({ colour, label }) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full flex-shrink-0"
              style={{ backgroundColor: colour }}
            />
            <span className="text-gray-400">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
