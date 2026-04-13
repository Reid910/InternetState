'use client'

import { useState, useEffect } from 'react'

interface Story {
  id: number
  headline: string
  summary: string | null
  last_seen: string
  article_count: number
  coverage_tiers: string | null
  media_comparison: string | null
}

interface Article {
  id: number
  url: string
  title: string | null
  summary: string | null
  article_date: string | null
  source_domain: string | null
  ingest_status: string | null
}

interface Angle {
  id: number | null
  title: string | null
  summary: string | null
  articles: Article[]
}

interface StoriesResponse {
  total: number
  page: number
  limit: number
  stories: Story[]
}

const PAGE_SIZE = 50

function getDomain(url: string): string {
  try { return new URL(url).hostname.replace('www.', '') } catch { return url }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function ArticleRow({ article }: { article: Article }) {
  const domain = article.source_domain || getDomain(article.url)
  const isPartial = article.ingest_status === 'fetch_failed' || article.ingest_status === 'extract_short'
  return (
    <div style={{ padding: '0.85rem 1.25rem', borderBottom: '1px solid #f7f7f7' }}>
      <div style={{ fontSize: '0.73rem', color: '#bbb', marginBottom: '0.2rem', display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
        <span>{domain}</span>
        <span>·</span>
        <span>{formatDate(article.article_date)}</span>
        {isPartial && (
          <span style={{ fontSize: '0.65rem', color: '#ccc', background: '#f5f5f5', borderRadius: '3px', padding: '1px 4px' }}>
            {article.ingest_status === 'fetch_failed' ? 'rss only' : 'brief'}
          </span>
        )}
      </div>
      <a href={article.url} target="_blank" rel="noopener noreferrer"
        style={{ fontSize: '0.93rem', fontWeight: '600', color: '#222', textDecoration: 'none' }}>
        {article.title || article.url}
      </a>
      {article.summary && (
        <p style={{ margin: '0.35rem 0 0', color: '#666', fontSize: '0.85rem', lineHeight: '1.6' }}>
          {article.summary}
        </p>
      )}
    </div>
  )
}

function AngleSection({ angle }: { angle: Angle }) {
  if (!angle.title) {
    return (
      <>
        {angle.articles.map(a => <ArticleRow key={a.id} article={a} />)}
      </>
    )
  }
  return (
    <details style={{ borderBottom: '1px solid #ececec' }}>
      <summary style={{
        padding: '0.6rem 1.25rem', cursor: 'pointer', listStyle: 'none',
        display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#fafafa',
      }}>
        <span style={{ fontSize: '0.78rem', fontWeight: '700', color: '#555' }}>{angle.title}</span>
        <span style={{ fontSize: '0.72rem', color: '#bbb' }}>
          {angle.articles.length} {angle.articles.length === 1 ? 'article' : 'articles'}
        </span>
      </summary>
      {angle.summary && (
        <p style={{ margin: 0, padding: '0.5rem 1.25rem', background: '#fafafa', fontSize: '0.82rem', color: '#777', borderBottom: '1px solid #f0f0f0' }}>
          {angle.summary}
        </p>
      )}
      <div>{angle.articles.map(a => <ArticleRow key={a.id} article={a} />)}</div>
    </details>
  )
}

function TierBadge({ label, color }: { label: string; color: string }) {
  return (
    <span style={{
      fontSize: '0.65rem', fontWeight: '700', color, border: `1px solid ${color}`,
      borderRadius: '3px', padding: '1px 5px', letterSpacing: '0.03em',
    }}>
      {label}
    </span>
  )
}

function StoryCard({ story }: { story: Story }) {
  const apiUrl = '/api-proxy'
  const [angles, setAngles] = useState<Angle[] | null>(null)
  const [open, setOpen] = useState(false)

  function handleToggle(e: React.MouseEvent<HTMLDetailsElement>) {
    const isNowOpen = (e.currentTarget as HTMLDetailsElement).open
    setOpen(isNowOpen)
    if (isNowOpen && angles === null) {
      fetch(`${apiUrl}/stories/${story.id}/angles`)
        .then(r => r.json())
        .then(setAngles)
        .catch(() => setAngles([]))
    }
  }

  const hasAngles = angles !== null && angles.some(a => a.id !== null)

  return (
    <details style={{
      background: '#fff', borderRadius: '8px', marginBottom: '1rem',
      boxShadow: '0 1px 3px rgba(0,0,0,0.07)', overflow: 'hidden',
    }} onToggle={handleToggle as any}>
      <summary style={{
        padding: '1rem 1.25rem', cursor: 'pointer', listStyle: 'none',
        display: 'flex', alignItems: 'flex-start', gap: '0.75rem',
      }}>
        <span style={{
          flexShrink: 0, fontSize: '0.7rem', fontWeight: '700',
          color: '#fff', background: '#222', borderRadius: '3px',
          padding: '2px 6px', marginTop: '3px',
        }}>
          {story.article_count} {story.article_count === 1 ? 'source' : 'sources'}
        </span>
        <span style={{ flex: 1 }}>
          <span style={{ fontSize: '1rem', fontWeight: '600', color: '#111', lineHeight: '1.4', display: 'block' }}>
            {story.headline}
          </span>
          {story.summary && (
            <span style={{ fontSize: '0.87rem', color: '#555', lineHeight: '1.6', marginTop: '0.3rem', display: 'block' }}>
              {story.summary}
            </span>
          )}
          <span style={{ display: 'flex', gap: '0.4rem', marginTop: '0.3rem', flexWrap: 'wrap', alignItems: 'center' }}>
            {story.coverage_tiers === 'both' && (
              <TierBadge label="legacy + independent" color="#2a6" />
            )}
            {story.coverage_tiers === 'legacy_only' && (
              <TierBadge label="legacy only" color="#888" />
            )}
            {story.coverage_tiers === 'independent_only' && (
              <TierBadge label="independent only" color="#a62" />
            )}
            {hasAngles && (
              <span style={{ fontSize: '0.72rem', color: '#aaa' }}>
                {angles!.filter(a => a.id !== null).map(a => a.title).join(' · ')}
              </span>
            )}
          </span>
        </span>
        <span style={{ flexShrink: 0, fontSize: '0.75rem', color: '#bbb', marginTop: '3px' }}>
          {formatDate(story.last_seen)}
        </span>
      </summary>
      <div style={{ borderTop: '1px solid #f0f0f0' }}>
        {story.media_comparison && (
          <div style={{
            padding: '0.75rem 1.25rem', background: '#f6faf6',
            borderBottom: '1px solid #e8f0e8', fontSize: '0.84rem',
            color: '#446644', lineHeight: '1.65',
          }}>
            <span style={{ fontWeight: '700', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Framing comparison · {' '}
            </span>
            {story.media_comparison}
          </div>
        )}
        {open && angles === null && (
          <p style={{ padding: '1rem 1.25rem', color: '#bbb', fontSize: '0.85rem', margin: 0 }}>Loading...</p>
        )}
        {angles !== null && angles.map((angle, i) => (
          <AngleSection key={angle.id ?? `u-${i}`} angle={angle} />
        ))}
      </div>
    </details>
  )
}

export default function StoriesBrowser() {
  // Use the Next.js rewrite proxy so the browser never talks directly to api:8000
  const apiUrl = '/api-proxy'
  const [page, setPage] = useState(1)
  const [data, setData] = useState<StoriesResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`${apiUrl}/stories?page=${page}&limit=${PAGE_SIZE}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [page, apiUrl])

  if (loading) return <p style={{ color: '#888' }}>Loading stories...</p>
  if (!data || data.stories.length === 0) return <p style={{ color: '#888' }}>No stories yet.</p>

  const totalPages = Math.ceil(data.total / PAGE_SIZE)

  return (
    <>
    
      {totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '0 0 1rem' }}>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{ padding: '0.4rem 0.9rem', borderRadius: '4px', border: '1px solid #ddd', background: page === 1 ? '#f5f5f5' : '#fff', cursor: page === 1 ? 'default' : 'pointer', color: '#444' }}
          >
            ← prev
          </button>
          <span style={{ fontSize: '0.85rem', color: '#666' }}>
            page {page} of {totalPages} &nbsp;·&nbsp; {data.total.toLocaleString()} stories
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            style={{ padding: '0.4rem 0.9rem', borderRadius: '4px', border: '1px solid #ddd', background: page === totalPages ? '#f5f5f5' : '#fff', cursor: page === totalPages ? 'default' : 'pointer', color: '#444' }}
          >
            next →
          </button>
        </div>
      )}
      
      {data.stories.map(story => (
        <StoryCard key={story.id} story={story} />
      ))}

      {totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '1rem 0 2rem' }}>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{ padding: '0.4rem 0.9rem', borderRadius: '4px', border: '1px solid #ddd', background: page === 1 ? '#f5f5f5' : '#fff', cursor: page === 1 ? 'default' : 'pointer', color: '#444' }}
          >
            ← prev
          </button>
          <span style={{ fontSize: '0.85rem', color: '#666' }}>
            page {page} of {totalPages} &nbsp;·&nbsp; {data.total.toLocaleString()} stories
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            style={{ padding: '0.4rem 0.9rem', borderRadius: '4px', border: '1px solid #ddd', background: page === totalPages ? '#f5f5f5' : '#fff', cursor: page === totalPages ? 'default' : 'pointer', color: '#444' }}
          >
            next →
          </button>
        </div>
      )}
    </>
  )
}
