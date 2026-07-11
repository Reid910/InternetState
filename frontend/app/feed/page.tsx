import Link from 'next/link'
import ArticleFeed from '../ArticleFeed'
import ThemeToggle from '../ThemeToggle'
import InlineSearch from '../InlineSearch'

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

async function searchArticles(q: string) {
  try {
    const res = await fetch(`${API_URL}/search?q=${encodeURIComponent(q)}&type=articles&mode=text&limit=30`, { cache: 'no-store' })
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
  searchParams: Promise<{ page?: string; source?: string; q?: string }>
}) {
  const { page: pageStr, source = '', q = '' } = await searchParams
  const page = Math.max(1, parseInt(pageStr || '1') || 1)

  const [articlesData, sources, stats] = await Promise.all([
    q.trim() ? searchArticles(q.trim()) : getArticles(page, source),
    getSources(),
    getStats(),
  ])

  const totalPages = Math.ceil((articlesData.total ?? 0) / PAGE_SIZE) || 1

  return (
    <main className="page-main">
      <header className="site-header">
        <div className="site-title">
          <a href="/"><h1>Internet State</h1></a>
          <ThemeToggle />
        </div>
        <div className="header-meta">
          <span className="stat"><strong>{stats.articles_today.toLocaleString()}</strong> articles today</span>
          <span className="stat"><strong>{stats.total_articles.toLocaleString()}</strong> total articles</span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.25rem' }}>
            <Link href="/" className="nav-btn">Stories</Link>
            <Link href="/feed" className="nav-btn active">Articles</Link>
          </div>
        </div>
      </header>

      <InlineSearch basePath="/feed" type="articles" />

      {q.trim() ? (
        <>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
            {articlesData.total} result{articlesData.total !== 1 ? 's' : ''} for &ldquo;{q}&rdquo;
            {' · '}<a href="/feed" style={{ color: 'var(--text-muted)' }}>clear</a>
          </div>
          <ArticleFeed
            articles={articlesData.articles}
            total={articlesData.total}
            page={1}
            totalPages={1}
            sources={sources}
            source=""
          />
        </>
      ) : (
        <ArticleFeed
          articles={articlesData.articles}
          total={articlesData.total}
          page={page}
          totalPages={totalPages}
          sources={sources}
          source={source}
        />
      )}
    </main>
  )
}
