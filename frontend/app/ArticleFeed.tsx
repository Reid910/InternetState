'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

interface Article {
  id: number
  url: string
  title: string | null
  summary: string | null
  article_date: string | null
  fetched_at: string | null
  source_domain: string | null
}

interface ArticlesResponse {
  total: number
  page: number
  limit: number
  articles: Article[]
}

interface Source {
  source_domain: string
  article_count: number
}

const PAGE_SIZE = 30
const API = '/api-proxy'

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function ArticleCard({ article }: { article: Article }) {
  const date = article.article_date || article.fetched_at
  return (
    <div style={{
      background: '#fff', borderRadius: '8px', padding: '1rem 1.25rem',
      marginBottom: '0.75rem', boxShadow: '0 1px 3px rgba(0,0,0,0.07)',
    }}>
      <div style={{ fontSize: '0.73rem', color: '#bbb', marginBottom: '0.3rem', display: 'flex', gap: '0.4rem' }}>
        <span>{article.source_domain}</span>
        {date && <><span>·</span><span>{formatDate(date)}</span></>}
      </div>
      <a href={article.url} target="_blank" rel="noopener noreferrer"
        style={{ fontSize: '0.97rem', fontWeight: '600', color: '#111', textDecoration: 'none', lineHeight: '1.4', display: 'block' }}>
        {article.title || article.url}
      </a>
      {article.summary && (
        <p style={{ margin: '0.4rem 0 0', color: '#555', fontSize: '0.86rem', lineHeight: '1.65' }}>
          {article.summary}
        </p>
      )}
    </div>
  )
}

function Pagination({ page, totalPages }: { page: number; totalPages: number }) {
  const router = useRouter()
  const searchParams = useSearchParams()

  function go(newPage: number) {
    const params = new URLSearchParams(searchParams.toString())
    params.set('page', String(newPage))
    router.push(`?${params.toString()}`)
  }

  if (totalPages <= 1) return null

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', padding: '1rem 0 2rem' }}>
      <button onClick={() => go(page - 1)} disabled={page === 1}
        style={{ padding: '0.4rem 0.9rem', borderRadius: '4px', border: '1px solid #ddd', background: page === 1 ? '#f5f5f5' : '#fff', cursor: page === 1 ? 'default' : 'pointer', color: '#444' }}>
        ← prev
      </button>
      <span style={{ fontSize: '0.85rem', color: '#666' }}>page {page} of {totalPages}</span>
      <button onClick={() => go(page + 1)} disabled={page === totalPages}
        style={{ padding: '0.4rem 0.9rem', borderRadius: '4px', border: '1px solid #ddd', background: page === totalPages ? '#f5f5f5' : '#fff', cursor: page === totalPages ? 'default' : 'pointer', color: '#444' }}>
        next →
      </button>
    </div>
  )
}

export default function ArticleFeed() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const page = Number(searchParams.get('page') || '1')
  const source = searchParams.get('source') || ''

  const [data, setData] = useState<ArticlesResponse | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/sources`).then(r => r.json()).then(setSources).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE) })
    if (source) params.set('source', source)
    fetch(`${API}/articles?${params}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [page, source])

  function handleSourceChange(val: string) {
    const params = new URLSearchParams(searchParams.toString())
    if (val) params.set('source', val)
    else params.delete('source')
    params.delete('page')
    router.push(`?${params.toString()}`)
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <>
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <select
          value={source}
          onChange={e => handleSourceChange(e.target.value)}
          style={{
            fontSize: '0.85rem', padding: '0.35rem 0.6rem', borderRadius: '5px',
            border: '1px solid #ddd', background: '#fff', color: '#444', cursor: 'pointer',
          }}
        >
          <option value="">All sources</option>
          {sources.map(s => (
            <option key={s.source_domain} value={s.source_domain}>
              {s.source_domain} ({s.article_count})
            </option>
          ))}
        </select>
        {data && (
          <span style={{ fontSize: '0.82rem', color: '#aaa' }}>
            {data.total.toLocaleString()} articles
          </span>
        )}
      </div>

      {loading && <p style={{ color: '#aaa', fontSize: '0.9rem' }}>Loading...</p>}

      {!loading && data?.articles.length === 0 && (
        <p style={{ color: '#aaa', fontSize: '0.9rem' }}>No articles yet.</p>
      )}

      {data?.articles.map(article => (
        <ArticleCard key={article.id} article={article} />
      ))}

      <Pagination page={page} totalPages={totalPages} />
    </>
  )
}
