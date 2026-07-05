import { notFound, redirect } from 'next/navigation'
import Home from '../page'

export default async function PageN({ params }: { params: Promise<{ page: string }> }) {
  const { page: pageStr } = await params
  const page = parseInt(pageStr)
  if (isNaN(page) || page < 1) notFound()
  if (page === 1) redirect('/')
  return <Home />
}
