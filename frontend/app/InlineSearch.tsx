'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function InlineSearch({ basePath, type }: { basePath: string; type: string }) {
  const router = useRouter()
  const [q, setQ] = useState('')

  function submit(e: React.FormEvent) {
    e.preventDefault()
    if (!q.trim()) return
    router.push(`${basePath}?q=${encodeURIComponent(q.trim())}`)
  }

  return (
    <form onSubmit={submit} style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
      <input
        type="search"
        value={q}
        onChange={e => setQ(e.target.value)}
        placeholder={`Search ${type}…`}
        style={{
          flex: 1, fontSize: '0.9rem', padding: '0.45rem 0.75rem',
          borderRadius: '6px', border: '1px solid var(--border)',
          background: 'var(--surface)', color: 'var(--text-primary)', outline: 'none',
        }}
      />
      <button type="submit" style={{
        padding: '0.45rem 0.9rem', borderRadius: '6px',
        border: '1px solid var(--border)', background: 'var(--surface)',
        color: 'var(--text-primary)', fontSize: '0.9rem', cursor: 'pointer',
      }}>
        Search
      </button>
    </form>
  )
}
