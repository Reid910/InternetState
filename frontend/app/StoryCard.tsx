'use client'

import { useState } from 'react'
import Link from 'next/link'

export interface Article {
  id: number
  url: string
  title: string | null
  source_domain: string | null
}

export interface Story {
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

export default function StoryCard({ story }: { story: Story }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="card">
      <div style={{ fontSize: '0.73rem', color: 'var(--text-meta)', marginBottom: '0.3rem', display: 'flex', gap: '0.4rem' }}>
        <span>{story.article_count} sources</span>
        <span>·</span>
        <span>{formatDate(story.updated_at)}</span>
      </div>

      <Link href={`/stories/${story.id}`}
        style={{ fontSize: '0.97rem', fontWeight: '600', color: 'var(--text-primary)', lineHeight: '1.4', marginBottom: '0.4rem', display: 'block', textDecoration: 'none' }}>
        {story.headline}
      </Link>

      {story.summary && (
        <p style={{ margin: '0 0 0.6rem', color: 'var(--text-secondary)', fontSize: '0.86rem', lineHeight: '1.65' }}>
          {story.summary}
        </p>
      )}

      <button onClick={() => setExpanded(e => !e)} className="text-btn">
        {expanded ? 'hide sources' : `show ${story.articles.length} sources`}
      </button>

      {expanded && (
        <div style={{ marginTop: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
          {story.articles.map(a => (
            <a key={a.id} href={a.url} target="_blank" rel="noopener noreferrer"
              style={{ fontSize: '0.83rem', textDecoration: 'none', display: 'flex', gap: '0.5rem', alignItems: 'baseline' }}>
              <span style={{ color: 'var(--text-meta)', fontSize: '0.75rem', flexShrink: 0 }}>{a.source_domain}</span>
              <span style={{ color: 'var(--text-secondary)' }}>{a.title || a.url}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
