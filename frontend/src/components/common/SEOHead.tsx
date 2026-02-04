/** SEO Head component for managing document head */
import { Helmet } from 'react-helmet-async'

interface SEOHeadProps {
  title: string
  description?: string
}

export function SEOHead({ title, description }: SEOHeadProps) {
  return (
    <Helmet>
      <title>{title}</title>
      {description && <meta name="description" content={description} />}
    </Helmet>
  )
}
