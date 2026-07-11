import Link from 'next/link'
import ArticleFeed from '../ArticleFeed'

const API_URL = process.env.API_URL || 'http://localhost:8000'
const PAGE_SIZE = 30

async function getArticles(page: number, source: string) {
  try {
    const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE) })
    if (source) params.set('source', source)
    const res = await fetch(`${API_URL}/articles?${params}`, { next: { revalidate: 300 } })
    if (!res.ok) return { total: 0, articles: [] }
    return res.json()
  } catch {
    return { total: 0, articles: [] }
  }
}

async function getSources() {
  try {
    const res = await fetch(`${API_URL}/sources`, { next: { revalidate: 300 } })
    if (!res.ok) return []
    return res.json()
  } catch {
    return []
  }
}

async function getStats() {
  try {
    const res = await fetch(`${API_URL}/stats`, { next: { revalidate: 300 } })
    if (!res.ok) return { total_articles: 0, articles_today: 0 }
    return res.json()
  } catch {
    return { total_articles: 0, articles_today: 0 }
  }
}

export default async function FeedPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; source?: string }>
}) {
  const { page: pageStr, source = '' } = await searchParams
  const page = Math.max(1, parseInt(pageStr || '1') || 1)

  const [articlesData, sources, stats] = await Promise.all([
    getArticles(page, source),
    getSources(),
    getStats(),
  ])

  const totalPages = Math.ceil(articlesData.total / PAGE_SIZE) || 1

  return (
    <main style={{ maxWidth: '780px', margin: '0 auto', padding: '2rem 1rem' }}>
      <header style={{ marginBottom: '1.5rem', borderBottom: '2px solid #1a1a1a', paddingBottom: '1rem' }}>
        <a href="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: '700' }}>Internet State</h1>
        </a>
        <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.4rem', alignItems: 'center' }}>
          <Stat label="articles today" value={stats.articles_today} />
          <Stat label="total articles" value={stats.total_articles} />
          <Link href="/" style={{ fontSize: '0.82rem', color: '#aaa', marginLeft: 'auto', textDecoration: 'none' }}>
            ← stories
          </Link>
        </div>
      </header>

      <ArticleFeed
        articles={articlesData.articles}
        total={articlesData.total}
        page={page}
        totalPages={totalPages}
        sources={sources}
        source={source}
      />
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
