import { useEffect, useState } from 'react'
import api from '../lib/api'

interface Props {
  url: string
  alt?: string
  className?: string
}

export default function AuthImage({ url, alt = '', className }: Props) {
  const [src, setSrc] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string
    api.get(url, { responseType: 'blob' })
      .then((r) => {
        objectUrl = URL.createObjectURL(r.data)
        setSrc(objectUrl)
      })
      .catch(() => setSrc(null))
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [url])

  if (!src) return null
  return <img src={src} alt={alt} className={className} />
}
