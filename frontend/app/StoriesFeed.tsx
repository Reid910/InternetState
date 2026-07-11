'use client'

import { useState } from 'react'
import Link from 'next/link'

interface Article {
  id: number
  url: string
  title: string | null
  source_domain: string | null
}

interface Story {
  id: number
  headline: string
  summary: string
  article_count: number
  updated_at: string
  articles: Article[]
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

function StoryCard({ story }: { story: Story }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div style={{
      background: '#fff', borderRadius: '8px', padding: '1rem 1.25rem',
      marginBottom: '0.75rem', boxShadow: '0 1px 3px rgba(0,0,0,0.07)',
    }}>
      <div style={{ fontSize: '0.73rem', color: '#bbb', marginBottom: '0.3rem', display: 'flex', gap: '0.4rem' }}>
        <span>{story.article_count} sources</span>
        <span>·</span>
        <span>{formatDate(story.updated_at)}</span>
      </div>

      <div style={{ fontSize: '0.97rem', fontWeight: '600', color: '#111', lineHeight: '1.4', marginBottom: '0.4rem' }}>
        {story.headline}
      </div>

      {story.summary && (
        <p style={{ margin: '0 0 0.6rem', color: '#555', fontSize: '0.86rem', lineHeight: '1.65' }}>
          {story.summary}
        </p>
      )}

      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          fontSize: '0.78rem', color: '#888', background: 'none', border: 'none',
          padding: 0, cursor: 'pointer', textDecoration: 'underline',
        }}
      >
        {expanded ? 'hide sources' : `show ${story.articles.length} sources`}
      </button>

      {expanded && (
        <div style={{ marginTop: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          {story.articles.map(a => (
            <a key={a.id} href={a.url} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: '0.83rem', color: '#444', textDecoration: 'none', display: 'flex', gap: '0.5rem', alignItems: 'baseline' }}>
              <span style={{ color: '#bbb', fontSize: '0.75rem', flexShrink: 0 }}>{a.source_domain}</span>
              <span style={{ color: '#333' }}>{a.title || a.url}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

function Pager({ page, totalPages }: { page: number; totalPages: number }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
      <Link href={`/?page=${page - 1}`}
        aria-disabled={page === 1}
        onClick={e => page === 1 && e.preventDefault()}
        style={{ padding: '0.35rem 0.7rem', borderRadius: '4px', border: '1px solid #ddd', background: page === 1 ? '#f5f5f5' : '#fff', color: '#444', fontSize: '0.85rem', textDecoration: 'none', pointerEvents: page === 1 ? 'none' : 'auto' }}>
        ←
      </Link>
      <span style={{ fontSize: '0.82rem', color: '#666' }}>{page} / {totalPages}</span>
      <Link href={`/?page=${page + 1}`}
        aria-disabled={page === totalPages}
        onClick={e => page === totalPages && e.preventDefault()}
        style={{ padding: '0.35rem 0.7rem', borderRadius: '4px', border: '1px solid #ddd', background: page === totalPages ? '#f5f5f5' : '#fff', color: '#444', fontSize: '0.85rem', textDecoration: 'none', pointerEvents: page === totalPages ? 'none' : 'auto' }}>
        →
      </Link>
    </div>
  )
}

export default function StoriesFeed({
  stories, total, page, totalPages,
}: {
  stories: Story[]
  total: number
  page: number
  totalPages: number
}) {
  return (
    <>
      <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <span style={{ fontSize: '0.82rem', color: '#aaa' }}>{total.toLocaleString()} stories</span>
        <div style={{ marginLeft: 'auto' }}>
          <Pager page={page} totalPages={totalPages} />
        </div>
      </div>

      {stories.length === 0 && (
        <p style={{ color: '#aaa', fontSize: '0.9rem' }}>No stories yet — clustering runs after each ingest cycle.</p>
      )}

      {stories.map(story => <StoryCard key={story.id} story={story} />)}

      {stories.length > 0 && <Pager page={page} totalPages={totalPages} />}
    </>
  )
}
