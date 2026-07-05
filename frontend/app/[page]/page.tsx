import { notFound, redirect } from 'next/navigation'
import Home from '../page'

export default async function PageN({ params }: { params: { page: string } }) {
  const page = parseInt(params.page)
  if (isNaN(page) || page < 1) notFound()
  if (page === 1) redirect('/')
  return <Home />
}
