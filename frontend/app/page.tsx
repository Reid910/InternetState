import Link from 'next/link'
import StoriesFeed from './StoriesFeed'
import ThemeToggle from './ThemeToggle'
import InlineSearch from './InlineSearch'
import StoryCard, { type Story } from './StoryCard'

const API_URL = process.env.API_URL || 'http://localhost:8000'

async function getStories(page: number) {
  try {
    const res = await fetch(`${API_URL}/stories?page=${page}&limit=20`, { next: { revalidate: 300 } })
    if (!res.ok) return { total: 0, stories: [] }
    return res.json()
  } catch {
    return { total: 0, stories: [] }
  }
}

async function searchStories(q: string) {
  try {
    const res = await fetch(`${API_URL}/search?q=${encodeURIComponent(q)}&type=stories&mode=text&limit=30`, { cache: 'no-store' })
    if (!res.ok) return { total: 0, stories: [] }
    return res.json()
  } catch {
    return { total: 0, stories: [] }
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

export default async function Home({
  searchParams,
}: {
  searchParams: Promise<{ page?: string; q?: string }>
}) {
  const { page: pageStr, q = '' } = await searchParams
  const page = Math.max(1, parseInt(pageStr || '1') || 1)

  const [storiesData, stats] = await Promise.all([
    q.trim() ? searchStories(q.trim()) : getStories(page),
    getStats(),
  ])

  const totalPages = Math.ceil((storiesData.total ?? 0) / 20) || 1
  const stories: Story[] = storiesData.stories ?? []

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
            <Link href="/" className="nav-btn active">Stories</Link>
            <Link href="/feed" className="nav-btn">Articles</Link>
            <Link href="/about" className="nav-btn">About</Link>
          </div>
        </div>
      </header>

      <InlineSearch basePath="/" type="stories" />

      {q.trim() ? (
        <>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
            {stories.length} result{stories.length !== 1 ? 's' : ''} for &ldquo;{q}&rdquo;
            {' · '}<a href="/" style={{ color: 'var(--text-muted)' }}>clear</a>
          </div>
          {stories.length === 0 && <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No results found.</p>}
          {stories.map(story => <StoryCard key={story.id} story={story} />)}
        </>
      ) : (
        <StoriesFeed stories={stories} total={storiesData.total} page={page} totalPages={totalPages} />
      )}
    </main>
  )
}
