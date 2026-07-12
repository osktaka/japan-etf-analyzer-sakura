/** SEO Head component for managing document head */
import { Helmet } from 'react-helmet-async'

const SITE_NAME = 'Japan ETF Analyzer'
const BASE_URL = 'https://kima3.net/japan-etf-analyzer'

interface SEOHeadProps {
  title: string
  description?: string
  path?: string
  type?: 'website' | 'article'
  publishedTime?: string
  modifiedTime?: string
}

export function SEOHead({
  title,
  description,
  path,
  type = 'website',
  publishedTime,
  modifiedTime,
}: SEOHeadProps) {
  const fullTitle = `${title} - ${SITE_NAME}`
  const url = path ? `${BASE_URL}${path}` : undefined
  const ogDescription =
    description || '日本のETF銘柄を検索・分析・比較できるWebアプリケーション'

  return (
    <Helmet>
      <title>{fullTitle}</title>
      {description && <meta name="description" content={description} />}
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={ogDescription} />
      <meta property="og:type" content={type} />
      <meta property="og:site_name" content={SITE_NAME} />
      {url && <meta property="og:url" content={url} />}
      {url && <link rel="canonical" href={url} />}
      {publishedTime && (
        <meta property="article:published_time" content={publishedTime} />
      )}
      {modifiedTime && (
        <meta property="article:modified_time" content={modifiedTime} />
      )}
    </Helmet>
  )
}
