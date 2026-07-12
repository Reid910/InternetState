import Link from 'next/link'
import ThemeToggle from '../../ThemeToggle'
import BackButton from './BackButton'

const API_URL = process.env.API_URL || 'http://localhost:8000'

interface Article {
  id: number
  url: string
  title: string | null
  source_domain: string | null
  article_date: string | null
  summary: string | null
}

interface Story {
  id: number
  headline: string
  summary: string
  article_count: number
  updated_at: string
  created_at: string
  articles: Article[]
}

async function getStory(id: string): Promise<Story | null> {
  try {
    const res = await fetch(`${API_URL}/stories/${id}`, { next: { revalidate: 300 } })
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export default async function StoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const story = await getStory(id)

  if (!story) {
    return (
      <main className="page-main">
        <p style={{ color: 'var(--text-muted)' }}>Story not found.</p>
        <Link href="/" style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>← back to stories</Link>
      </main>
    )
  }

  return (
    <main className="page-main">
      <header className="site-header">
        <div className="site-title">
          <a href="/"><h1>Internet State</h1></a>
          <ThemeToggle />
        </div>
        <div className="header-meta">
          <BackButton />
        </div>
      </header>

      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-meta)', marginBottom: '0.5rem', display: 'flex', gap: '0.5rem' }}>
          <span>{story.article_count} sources</span>
          <span>·</span>
          <span>updated {formatDate(story.updated_at)}</span>
        </div>
        <h2 style={{ margin: '0 0 0.75rem', fontSize: '1.4rem', fontWeight: '700', color: 'var(--text-primary)', lineHeight: '1.35' }}>
          {story.headline}
        </h2>
        {story.summary && (
          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: '1.7' }}>
            {story.summary}
          </p>
        )}
      </div>

      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '1.25rem' }}>
        <h3 style={{ margin: '0 0 0.75rem', fontSize: '0.82rem', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Sources
        </h3>
        {story.articles.map(article => (
          <div key={article.id} className="card">
            <div style={{ fontSize: '0.73rem', color: 'var(--text-meta)', marginBottom: '0.3rem', display: 'flex', gap: '0.4rem' }}>
              <span>{article.source_domain}</span>
              {article.article_date && <><span>·</span><span>{formatDate(article.article_date)}</span></>}
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
        ))}
      </div>
    </main>
  )
}
