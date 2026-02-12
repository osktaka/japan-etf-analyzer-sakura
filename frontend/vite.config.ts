import * as fs from 'fs'
import * as path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig } from 'vite'
import type { Plugin } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/** XML特殊文字をエスケープ */
const escapeXml = (str: string) =>
  str.replace(/[<>&'"]/g, (c) =>
    ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', "'": '&apos;', '"': '&quot;' }[c] ?? c)
  )

/** ビルド時にsitemap.xmlを自動生成するプラグイン */
function sitemapGeneratorPlugin(): Plugin {
  return {
    name: 'sitemap-generator',
    writeBundle() {
      const siteUrl = 'https://kima3.net/japan-etf-analyzer'
      const staticPages = ['/', '/compare', '/market', '/notes']

      // content/notes/*.md からノートURLを収集
      const notesDir = path.resolve(__dirname, 'src/content/notes')
      const noteUrls: string[] = []
      if (fs.existsSync(notesDir)) {
        fs.readdirSync(notesDir)
          .filter((f) => f.endsWith('.md'))
          .forEach((f) => {
            const slug = f.replace('.md', '')
            noteUrls.push(`/notes/${slug}`)
          })
      }

      const allUrls = [...staticPages, ...noteUrls]
      const today = new Date().toISOString().split('T')[0]

      const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${allUrls.map((url) => `  <url>
    <loc>${escapeXml(siteUrl + url)}</loc>
    <lastmod>${today}</lastmod>
  </url>`).join('\n')}
</urlset>`

      const outDir = path.resolve(__dirname, 'dist')
      fs.writeFileSync(path.resolve(outDir, 'sitemap.xml'), sitemap, 'utf-8')
      console.log(`\u2713 sitemap.xml generated with ${allUrls.length} URLs`)
    },
  }
}

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    ...(mode === 'production' ? [sitemapGeneratorPlugin()] : []),
  ],
  base: mode === 'production' ? '/japan-etf-analyzer/' : '/',
  server: {
    host: '0.0.0.0',
    port: 3902,
  },
}))
