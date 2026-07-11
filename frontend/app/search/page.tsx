import Link from 'next/link'
import ThemeToggle from '../ThemeToggle'
import SearchBox from '../SearchBox'
import StoryCard, { type Story } from '../StoryCard'

const API_URL = process.env.API_URL || 'http://localhost:8000'

interface Article {
  id: number
  url: string
  title: string | null
  summary: string | null
  article_date: string | null
  fetched_at: string | null
  source_domain: string | null
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

async function doSearch(q: string, mode: string, type: string) {
  try {
    const params = new URLSearchParams({ q, mode, type, limit: '30' })
    const res = await fetch(`${API_URL}/search?${params}`, { cache: 'no-store' })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; mode?: string; type?: string }>
}) {
  const { q = '', mode = 'text', type = 'articles' } = await searchParams
  const data = q.trim() ? await doSearch(q.trim(), mode, type) : null

  const articles: Article[] = data?.articles ?? []
  const stories: Story[] = data?.stories ?? []
  const total = data?.total ?? 0

  return (
    <main className="page-main">
      <header className="site-header">
        <div className="site-title">
          <a href="/"><h1>Internet State</h1></a>
          <ThemeToggle />
        </div>
        <div className="header-meta">
          <Link href="/" className="header-link">← stories</Link>
          <Link href="/feed" className="header-link">all articles</Link>
        </div>
      </header>

      <SearchBox defaultQ={q} defaultMode={mode} defaultType={type} />

      {data && (
        <div style={{ marginBottom: '0.75rem', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
          {total} result{total !== 1 ? 's' : ''} for &ldquo;{q}&rdquo;
          {' '}({type === 'stories' ? 'stories' : 'articles'}, {mode})
        </div>
      )}

      {type === 'stories' && stories.map(story => (
        <StoryCard key={story.id} story={story} />
      ))}

      {type === 'articles' && articles.map(article => {
        const date = article.article_date || article.fetched_at
        return (
          <div key={article.id} className="card">
            <div style={{ fontSize: '0.73rem', color: 'var(--text-meta)', marginBottom: '0.3rem', display: 'flex', gap: '0.4rem' }}>
              <span>{article.source_domain}</span>
              {date && <><span>·</span><span>{formatDate(date)}</span></>}
            </div>
            <a href={article.url} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: '0.97rem', fontWeight: '600', color: 'var(--text-primary)', textDecoration: 'none', lineHeight: '1.4', display: 'block' }}>
              {article.title || article.url}
            </a>
            {article.summary && (
              <p style={{ margin: '0.4rem 0 0', color: 'var(--text-secondary)', fontSize: '0.86rem', lineHeight: '1.65' }}>
                {article.summary}
              </p>
            )}
          </div>
        )
      })}

      {data && total === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No results found.</p>
      )}

      {!data && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Enter a query above to search.</p>
      )}
    </main>
  )
}
