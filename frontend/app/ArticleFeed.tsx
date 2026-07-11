'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'

interface Article {
  id: number
  url: string
  title: string | null
  summary: string | null
  article_date: string | null
  fetched_at: string | null
  source_domain: string | null
}

interface Source {
  source_domain: string
  article_count: number
}

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

function Pager({ page, totalPages, source }: { page: number; totalPages: number; source: string }) {
  const sourceParam = source ? `&source=${encodeURIComponent(source)}` : ''
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
      <Link href={`/feed?page=${page - 1}${sourceParam}`}
        aria-disabled={page === 1}
        onClick={e => page === 1 && e.preventDefault()}
        style={{ padding: '0.35rem 0.7rem', borderRadius: '4px', border: '1px solid #ddd', background: page === 1 ? '#f5f5f5' : '#fff', color: '#444', fontSize: '0.85rem', textDecoration: 'none', pointerEvents: page === 1 ? 'none' : 'auto' }}>
        ←
      </Link>
      <span style={{ fontSize: '0.82rem', color: '#666' }}>{page} / {totalPages}</span>
      <Link href={`/feed?page=${page + 1}${sourceParam}`}
        aria-disabled={page === totalPages}
        onClick={e => page === totalPages && e.preventDefault()}
        style={{ padding: '0.35rem 0.7rem', borderRadius: '4px', border: '1px solid #ddd', background: page === totalPages ? '#f5f5f5' : '#fff', color: '#444', fontSize: '0.85rem', textDecoration: 'none', pointerEvents: page === totalPages ? 'none' : 'auto' }}>
        →
      </Link>
    </div>
  )
}

export default function ArticleFeed({
  articles, total, page, totalPages, sources, source,
}: {
  articles: Article[]
  total: number
  page: number
  totalPages: number
  sources: Source[]
  source: string
}) {
  const router = useRouter()

  function handleSourceChange(val: string) {
    const params = new URLSearchParams()
    if (val) params.set('source', val)
    params.set('page', '1')
    router.push(`/feed?${params}`)
  }

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
        <span style={{ fontSize: '0.82rem', color: '#aaa' }}>{total.toLocaleString()} articles</span>
        <div style={{ marginLeft: 'auto' }}>
          <Pager page={page} totalPages={totalPages} source={source} />
        </div>
      </div>

      {articles.length === 0 && <p style={{ color: '#aaa', fontSize: '0.9rem' }}>No articles yet.</p>}

      {articles.map(article => <ArticleCard key={article.id} article={article} />)}

      {articles.length > 0 && <Pager page={page} totalPages={totalPages} source={source} />}
    </>
  )
}
