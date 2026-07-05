import { notFound } from 'next/navigation'
import Home from '../page'

export default async function PageN({ params }: { params: { page: string } }) {
  const page = parseInt(params.page)
  if (isNaN(page) || page < 2) notFound()
  return <Home pageNumber={page} />
}
