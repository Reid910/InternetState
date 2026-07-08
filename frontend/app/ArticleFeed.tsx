'use client'

import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'

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
  return new Date(dateStr).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
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

function Pager({ page, totalPages, goToPage }: {
  page: number; totalPages: number; goToPage: (p: number) => void
}) {
  const display = totalPages < 1 ? 1 : totalPages
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
      <button onClick={() => goToPage(page - 1)} disabled={page === 1}
        style={{ padding: '0.35rem 0.7rem', borderRadius: '4px', border: '1px solid #ddd', background: page === 1 ? '#f5f5f5' : '#fff', cursor: page === 1 ? 'default' : 'pointer', color: '#444', fontSize: '0.85rem' }}>
        ←
      </button>
      <span style={{ fontSize: '0.82rem', color: '#666' }}>{page} / {display}</span>
      <button onClick={() => goToPage(page + 1)} disabled={page === totalPages}
        style={{ padding: '0.35rem 0.7rem', borderRadius: '4px', border: '1px solid #ddd', background: page === totalPages ? '#f5f5f5' : '#fff', cursor: page === totalPages ? 'default' : 'pointer', color: '#444', fontSize: '0.85rem' }}>
        →
      </button>
    </div>
  )
}

export default function ArticleFeed() {
  const router = useRouter()
  const pathname = usePathname()
  const page = parseInt(pathname.slice(1)) || 1

  const [source, setSource] = useState('')
  const [data, setData] = useState<ArticlesResponse | null>(null)
  const [sources, setSources] = useState<Source[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/sources`).then(r => r.json()).then(setSources).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    window.scrollTo(0, 0)
    const params = new URLSearchParams({ page: String(page), limit: String(PAGE_SIZE) })
    if (source) params.set('source', source)
    fetch(`${API}/articles?${params}`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [page, source])

  function handleSourceChange(val: string) {
    setSource(val)
    router.push('/')
  }

  function goToPage(newPage: number) {
    router.push(newPage === 1 ? '/' : `/${newPage}`)
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  return (
    <>
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <select value={source} onChange={e => handleSourceChange(e.target.value)}
          style={{ fontSize: '0.85rem', padding: '0.35rem 0.6rem', borderRadius: '5px', border: '1px solid #ddd', background: '#fff', color: '#444', cursor: 'pointer' }}>
          <option value="">All sources</option>
          {sources.map(s => (
            <option key={s.source_domain} value={s.source_domain}>
              {s.source_domain} ({s.article_count})
            </option>
          ))}
        </select>
        {data && <span style={{ fontSize: '0.82rem', color: '#aaa' }}>{data.total.toLocaleString()} articles</span>}
        <div style={{ marginLeft: 'auto' }}>
          <Pager page={page} totalPages={totalPages} goToPage={goToPage} />
        </div>
      </div>

      {loading && <p style={{ color: '#aaa', fontSize: '0.9rem' }}>Loading...</p>}
      {!loading && data?.articles.length === 0 && <p style={{ color: '#aaa', fontSize: '0.9rem' }}>No articles yet.</p>}

      {data?.articles.map(article => (
        <ArticleCard key={article.id} article={article} />
      ))}

      <Pager page={page} totalPages={totalPages} goToPage={goToPage} />
    </>
  )
}
