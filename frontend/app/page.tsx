export const dynamic = 'force-dynamic'

import StoriesBrowser from './StoriesBrowser'

const API_URL = process.env.API_URL || 'http://localhost:8000'

interface Stats {
  total_articles: number
  total_stories: number
  stories_today: number
}

interface CoverageReport {
  created_at: string
  legacy_only_count: number
  independent_only_count: number
  both_count: number
  gap_analysis: string
}

async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_URL}/stats`, { cache: 'no-store' })
  if (!res.ok) return { total_articles: 0, total_stories: 0, stories_today: 0 }
  return res.json()
}

async function getCoverageReport(): Promise<CoverageReport | null> {
  const res = await fetch(`${API_URL}/coverage-report`, { cache: 'no-store' })
  if (!res.ok) return null
  return res.json()
}

export default async function Home() {
  const [stats, report] = await Promise.all([getStats(), getCoverageReport()])

  return (
    <main style={{ maxWidth: '780px', margin: '0 auto', padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.5rem', borderBottom: '2px solid #1a1a1a', paddingBottom: '1rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: '700' }}>Internet State</h1>
        <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.4rem' }}>
          <Stat label="stories today" value={stats.stories_today} />
          <Stat label="total stories" value={stats.total_stories} />
          <Stat label="articles" value={stats.total_articles} />
        </div>
      </header>

      {report && (
        <details style={{
          background: '#f8f8f0', border: '1px solid #e8e8d0', borderRadius: '8px',
          marginBottom: '1.5rem', overflow: 'hidden',
        }}>
          <summary style={{
            padding: '0.75rem 1rem', cursor: 'pointer', listStyle: 'none',
            display: 'flex', alignItems: 'center', gap: '0.75rem',
          }}>
            <span style={{ fontSize: '0.75rem', fontWeight: '700', color: '#666' }}>COVERAGE GAP ANALYSIS</span>
            <span style={{ fontSize: '0.75rem', color: '#aaa' }}>
              {report.legacy_only_count} legacy-only · {report.independent_only_count} independent-only · {report.both_count} both
            </span>
          </summary>
          <p style={{ margin: 0, padding: '0 1rem 0.85rem', fontSize: '0.87rem', color: '#555', lineHeight: '1.7' }}>
            {report.gap_analysis}
          </p>
        </details>
      )}

      <StoriesBrowser />
    </main>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <span style={{ fontSize: '0.85rem', color: '#666' }}>
      <strong style={{ color: '#111', fontWeight: '700' }}>{value.toLocaleString()}</strong>{' '}{label}
    </span>
  )
}
