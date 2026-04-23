/**
 * frontend/src/components/TypologyBadge.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * A colour-coded badge showing an AML typology label.
 *
 * Each of the 6 typologies has a distinct colour to make them immediately
 * recognisable in lists and tables, similar to GitHub's label system.
 *
 * Used in:
 *   - AccountDetail page (account's typology)
 *   - Queue table rows (typology column)
 *   - Search results dropdown
 *
 * Null-safe: if typology is null/undefined (benign account), renders nothing.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React from 'react';

// ─── Typology colour mapping ──────────────────────────────────────────────────

interface TypologyStyle {
  bg:    string; // Tailwind bg class
  text:  string; // Tailwind text class
  border: string; // Tailwind border class
  label: string; // Human-readable label
  icon:  string; // Emoji icon
}

const TYPOLOGY_STYLES: Record<string, TypologyStyle> = {
  structuring: {
    bg:     'bg-red-950',
    text:   'text-red-300',
    border: 'border-red-800',
    label:  'Structuring',
    icon:   '🏦',
  },
  layering: {
    bg:     'bg-orange-950',
    text:   'text-orange-300',
    border: 'border-orange-800',
    label:  'Layering',
    icon:   '⛓️',
  },
  funnel: {
    bg:     'bg-yellow-950',
    text:   'text-yellow-300',
    border: 'border-yellow-800',
    label:  'Funnel',
    icon:   '🔽',
  },
  round_trip: {
    bg:     'bg-purple-950',
    text:   'text-purple-300',
    border: 'border-purple-800',
    label:  'Round-Trip',
    icon:   '🔄',
  },
  shell_company: {
    bg:     'bg-blue-950',
    text:   'text-blue-300',
    border: 'border-blue-800',
    label:  'Shell Company',
    icon:   '🫧',
  },
  velocity: {
    bg:     'bg-cyan-950',
    text:   'text-cyan-300',
    border: 'border-cyan-800',
    label:  'Velocity',
    icon:   '⚡',
  },
};

const DEFAULT_STYLE: TypologyStyle = {
  bg:     'bg-gray-800',
  text:   'text-gray-400',
  border: 'border-gray-700',
  label:  'Unknown',
  icon:   '❓',
};

// ─── Component ────────────────────────────────────────────────────────────────

interface TypologyBadgeProps {
  /** Typology string from the database (e.g., "structuring"). Null-safe. */
  typology: string | null | undefined;
  /** If true, shows a larger badge with more padding. Default false. */
  large?: boolean;
}

export default function TypologyBadge({ typology, large = false }: TypologyBadgeProps) {
  if (!typology) return null;

  const style = TYPOLOGY_STYLES[typology] ?? DEFAULT_STYLE;

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-full border font-medium
        ${style.bg} ${style.text} ${style.border}
        ${large ? 'text-sm px-3 py-1' : 'text-xs px-2 py-0.5'}
      `}
      title={`AML Typology: ${style.label}`}
    >
      <span role="img" aria-label={style.label}>{style.icon}</span>
      {style.label}
    </span>
  );
}
