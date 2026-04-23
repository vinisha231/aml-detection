/**
 * frontend/src/pages/AnalyticsPage.tsx
 * ─────────────────────────────────────────────────────────────────────────────
 * Analytics dashboard page showing system-level AML performance metrics.
 *
 * Displays:
 *   1. False Positive Rate by signal type (horizontal bar chart)
 *   2. Typology breakdown (count + avg score per AML typology)
 *   3. Score distribution histogram (how many accounts fall in each bucket)
 *   4. Daily escalation trend (line chart for past 30 days)
 *
 * This page is for AML managers and compliance teams to monitor system health,
 * not for individual account investigation. Key questions answered:
 *   - Which rules produce the most false positives?
 *   - Which typologies are we catching vs. missing?
 *   - Is escalation volume trending up or down?
 *   - Are scores well-calibrated or clustering near 0 or 100?
 * ─────────────────────────────────────────────────────────────────────────────
 */

import React, { useEffect, useState } from 'react';
import axios from 'axios';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';

// ─── Types ────────────────────────────────────────────────────────────────────

interface FPREntry {
  signal_type:         string;
  escalated_count:     number;
  dismissed_count:     number;
  total_dispositioned: number;
  false_positive_rate: number;
}

interface TypologyEntry {
  typology:  string;
  count:     number;
  avg_score: number;
  max_score: number;
  min_score: number;
}

interface ScoreBucket {
  bucket:     string;
  bucket_min: number;
  count:      number;
}

interface DailyCount {
  date:  string;
  count: number;
}

// ─── Colour helpers ───────────────────────────────────────────────────────────

/** Red for high FPR, green for low — colour-coded severity */
function fprColour(fpr: number): string {
  if (fpr >= 0.6) return 'bg-red-500';
  if (fpr >= 0.3) return 'bg-orange-500';
  if (fpr >= 0.1) return 'bg-yellow-500';
  return 'bg-green-500';
}

/** Score bucket colour — mirrors risk tier colours */
function bucketColour(bucketMin: number): string {
  if (bucketMin >= 90) return 'bg-red-500';
  if (bucketMin >= 70) return 'bg-orange-500';
  if (bucketMin >= 40) return 'bg-yellow-500';
  return 'bg-gray-600';
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-gray-200">{title}</h2>
      <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [fpr,         setFpr]         = useState<FPREntry[]>([]);
  const [typologies,  setTypologies]  = useState<TypologyEntry[]>([]);
  const [distribution, setDistribution] = useState<ScoreBucket[]>([]);
  const [daily,       setDaily]       = useState<DailyCount[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      axios.get('/analytics/false-positive-rates'),
      axios.get('/analytics/typology-breakdown'),
      axios.get('/analytics/score-distribution'),
      axios.get('/analytics/daily-escalations'),
    ])
      .then(([fprRes, typRes, distRes, dailyRes]) => {
        setFpr(fprRes.data);
        setTypologies(typRes.data);
        setDistribution(distRes.data);
        setDaily(dailyRes.data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err?.message ?? 'Failed to load analytics.');
        setLoading(false);
      });
  }, []);

  if (loading) return <LoadingSpinner message="Loading analytics…" />;
  if (error)   return <ErrorBanner message={error} />;

  const maxCount = Math.max(...distribution.map((b) => b.count), 1);
  const maxDaily = Math.max(...daily.map((d) => d.count), 1);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-12">
      <h1 className="text-2xl font-bold text-gray-100">Analytics Dashboard</h1>

      {/* ── False Positive Rates ──────────────────────────────────────────── */}
      <section>
        <SectionHeader
          title="False Positive Rate by Signal"
          subtitle="Fraction of accounts with this signal that were dismissed (not escalated). Lower is better."
        />
        {fpr.length === 0 ? (
          <p className="text-gray-500 text-sm">No disposition data yet. Dismiss or escalate accounts to see FPR.</p>
        ) : (
          <div className="space-y-3">
            {fpr.map((entry) => (
              <div key={entry.signal_type} className="flex items-center gap-4">
                <span className="text-xs text-gray-400 w-36 text-right shrink-0 font-mono">
                  {entry.signal_type}
                </span>
                <div className="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${fprColour(entry.false_positive_rate)} transition-all`}
                    style={{ width: `${entry.false_positive_rate * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-12 shrink-0">
                  {(entry.false_positive_rate * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-gray-600 w-24 shrink-0">
                  {entry.total_dispositioned} reviews
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Typology Breakdown ────────────────────────────────────────────── */}
      <section>
        <SectionHeader
          title="Detection by Typology"
          subtitle="Average risk score assigned to accounts of each laundering typology."
        />
        {typologies.length === 0 ? (
          <p className="text-gray-500 text-sm">No scored accounts found. Run the detection pipeline first.</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {typologies.map((t) => (
              <div key={t.typology} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
                <div className="text-xs text-gray-500 uppercase tracking-wide mb-1">{t.typology}</div>
                <div className="text-2xl font-bold text-orange-400">{t.avg_score}</div>
                <div className="text-xs text-gray-600 mt-1">avg score · {t.count} accounts</div>
                <div className="text-xs text-gray-700 mt-0.5">
                  Range: {t.min_score}–{t.max_score}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Score Distribution ────────────────────────────────────────────── */}
      <section>
        <SectionHeader
          title="Score Distribution"
          subtitle="How many accounts fall into each risk score bucket."
        />
        {distribution.length === 0 ? (
          <p className="text-gray-500 text-sm">No scored accounts found.</p>
        ) : (
          <div className="flex items-end gap-2 h-40">
            {distribution.map((bucket) => (
              <div key={bucket.bucket} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-xs text-gray-600">{bucket.count}</span>
                <div
                  className={`w-full rounded-t-sm ${bucketColour(bucket.bucket_min)} transition-all`}
                  style={{ height: `${(bucket.count / maxCount) * 100}%`, minHeight: bucket.count > 0 ? 4 : 0 }}
                />
                <span className="text-xs text-gray-600 rotate-45 origin-left mt-2 whitespace-nowrap">
                  {bucket.bucket}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Daily Escalations ─────────────────────────────────────────────── */}
      <section>
        <SectionHeader
          title="Daily SAR Escalations (Past 30 Days)"
          subtitle="Number of accounts escalated for SAR filing each day."
        />
        <div className="flex items-end gap-0.5 h-24 border-b border-gray-800">
          {daily.map((day) => (
            <div
              key={day.date}
              className="flex-1 bg-blue-500 rounded-t-sm hover:bg-blue-400 transition-colors cursor-default"
              style={{ height: `${(day.count / maxDaily) * 100}%`, minHeight: day.count > 0 ? 2 : 0 }}
              title={`${day.date}: ${day.count} escalation(s)`}
            />
          ))}
        </div>
        <div className="flex justify-between text-xs text-gray-600 mt-1">
          <span>{daily[0]?.date}</span>
          <span>{daily[daily.length - 1]?.date}</span>
        </div>
      </section>
    </div>
  );
}
