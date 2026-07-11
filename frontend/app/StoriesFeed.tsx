'use client'

import Link from 'next/link'
import StoryCard, { type Story } from './StoryCard'

function Pager({ page, totalPages }: { page: number; totalPages: number }) {
  return (
    <div className="pager">
      <Link href={`/?page=${page - 1}`} className="pager-btn" aria-disabled={page === 1}>←</Link>
      <span className="pager-label">{page} / {totalPages}</span>
      <Link href={`/?page=${page + 1}`} className="pager-btn" aria-disabled={page === totalPages}>→</Link>
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
      <div className="toolbar">
        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{total.toLocaleString()} stories</span>
        <div style={{ marginLeft: 'auto' }}>
          <Pager page={page} totalPages={totalPages} />
        </div>
      </div>

      {stories.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No stories yet — clustering runs after each ingest cycle.</p>
      )}

      {stories.map(story => <StoryCard key={story.id} story={story} />)}

      {stories.length > 0 && <Pager page={page} totalPages={totalPages} />}
    </>
  )
}
