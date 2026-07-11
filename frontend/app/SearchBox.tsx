'use client'

import { useState, useTransition } from 'react'
import { useRouter } from 'next/navigation'

export default function SearchBox({
  defaultQ = '',
  defaultMode = 'text',
  defaultType = 'articles',
}: {
  defaultQ?: string
  defaultMode?: string
  defaultType?: string
}) {
  const router = useRouter()
  const [q, setQ] = useState(defaultQ)
  const [mode, setMode] = useState(defaultMode)
  const [type, setType] = useState(defaultType)
  const [, startTransition] = useTransition()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!q.trim()) return
    startTransition(() => {
      router.push(`/search?q=${encodeURIComponent(q.trim())}&mode=${mode}&type=${type}`)
    })
  }

  return (
    <form onSubmit={submit} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
      <input
        type="search"
        value={q}
        onChange={e => setQ(e.target.value)}
        placeholder="Search…"
        autoFocus
        style={{
          flex: '1', minWidth: '200px', fontSize: '0.95rem',
          padding: '0.5rem 0.75rem', borderRadius: '6px',
          border: '1px solid var(--border)', background: 'var(--surface)',
          color: 'var(--text-primary)', outline: 'none',
        }}
      />
      <select value={type} onChange={e => setType(e.target.value)} className="source-select">
        <option value="articles">Articles</option>
        <option value="stories">Stories</option>
      </select>
      <select value={mode} onChange={e => setMode(e.target.value)} className="source-select">
        <option value="text">Full-text</option>
        <option value="semantic">Semantic</option>
      </select>
      <button
        type="submit"
        style={{
          padding: '0.5rem 1rem', borderRadius: '6px',
          border: '1px solid var(--border)', background: 'var(--surface)',
          color: 'var(--text-primary)', fontSize: '0.9rem', cursor: 'pointer',
        }}
      >
        Search
      </button>
    </form>
  )
}
