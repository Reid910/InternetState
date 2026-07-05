export const dynamic = 'force-dynamic'

import { Suspense } from 'react'
import ArticleFeed from './ArticleFeed'

const API_URL = process.env.API_URL || 'http://localhost:8000'

interface Stats {
  total_articles: number
  articles_today: number
}

async function getStats(): Promise<Stats> {
  try {
    const res = await fetch(`${API_URL}/stats`, { cache: 'no-store' })
    if (!res.ok) return { total_articles: 0, articles_today: 0 }
    return res.json()
  } catch {
    return { total_articles: 0, articles_today: 0 }
  }
}

export default async function Home({ pageNumber = 1 }: { pageNumber?: number }) {
  const stats = await getStats()

  return (
    <main style={{ maxWidth: '780px', margin: '0 auto', padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.5rem', borderBottom: '2px solid #1a1a1a', paddingBottom: '1rem' }}>
        <a href="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: '700' }}>Internet State</h1>
        </a>
        <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.4rem' }}>
          <Stat label="articles today" value={stats.articles_today} />
          <Stat label="total articles" value={stats.total_articles} />
        </div>
      </header>

      <Suspense fallback={<p style={{ color: '#aaa', fontSize: '0.9rem' }}>Loading...</p>}>
        <ArticleFeed page={pageNumber} />
      </Suspense>
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
