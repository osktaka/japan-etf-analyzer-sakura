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

/** HTML属性値をエスケープ */
const escapeHtmlAttr = (str: string) =>
  str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

/** 簡易frontmatterパーサー（content/notes/index.tsと同じロジック） */
function parseFrontmatter(raw: string): { meta: Record<string, string>; content: string } {
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/)
  if (!match) return { meta: {}, content: raw }
  const meta: Record<string, string> = {}
  match[1].split('\n').forEach((line) => {
    const colonIdx = line.indexOf(':')
    if (colonIdx > 0) {
      meta[line.slice(0, colonIdx).trim()] = line.slice(colonIdx + 1).trim()
    }
  })
  return { meta, content: match[2] }
}

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

/** ビルド時にノートページのOGPプリレンダーHTMLを生成するプラグイン */
function ogpPrerenderPlugin(): Plugin {
  return {
    name: 'ogp-prerender',
    writeBundle() {
      const siteUrl = 'https://kima3.net/japan-etf-analyzer'
      const outDir = path.resolve(__dirname, 'dist')
      const notesDir = path.resolve(__dirname, 'src/content/notes')
      const indexHtml = fs.readFileSync(path.resolve(outDir, 'index.html'), 'utf-8')

      // notesディレクトリが存在しない場合はスキップ
      if (!fs.existsSync(notesDir)) return

      // dist/notes ディレクトリ作成
      const notesOutDir = path.resolve(outDir, 'notes')
      if (!fs.existsSync(notesOutDir)) {
        fs.mkdirSync(notesOutDir, { recursive: true })
      }

      // OGPメタタグを注入したHTMLを生成するヘルパー
      const injectOgp = (html: string, title: string, description: string, url: string, type: 'article' | 'website' = 'article'): string => {
        const safeTitle = escapeHtmlAttr(title)
        const safeDesc = escapeHtmlAttr(description)
        const safeUrl = escapeHtmlAttr(url)

        const metaTags = [
          `<meta name="description" content="${safeDesc}" />`,
          `<meta property="og:title" content="${safeTitle}" />`,
          `<meta property="og:description" content="${safeDesc}" />`,
          `<meta property="og:type" content="${type}" />`,
          `<meta property="og:url" content="${safeUrl}" />`,
          `<meta property="og:site_name" content="Japan ETF Analyzer" />`,
          `<link rel="canonical" href="${safeUrl}" />`,
        ].join('\n    ')

        // <title>タグを置換
        let result = html.replace(/<title>[^<]*<\/title>/, `<title>${safeTitle}</title>`)
        // </head>の直前にメタタグを注入
        result = result.replace('</head>', `    ${metaTags}\n  </head>`)
        return result
      }

      // 各ノート記事のプリレンダーHTML生成
      const mdFiles = fs.readdirSync(notesDir).filter((f) => f.endsWith('.md'))
      let count = 0

      mdFiles.forEach((f) => {
        const slug = f.replace('.md', '')
        const raw = fs.readFileSync(path.resolve(notesDir, f), 'utf-8')
        const { meta } = parseFrontmatter(raw)
        const title = `${meta.title ?? slug} - Japan ETF Analyzer`
        const summary = meta.summary ?? ''
        const url = `${siteUrl}/notes/${slug}`
        const html = injectOgp(indexHtml, title, summary, url)
        fs.writeFileSync(path.resolve(notesOutDir, `${slug}.html`), html, 'utf-8')
        count++
      })

      // ノート一覧ページ用プリレンダーHTML生成
      const listTitle = 'ノート - Japan ETF Analyzer'
      const listDesc = 'ETF投資に役立つ知識やコラムをまとめたノート一覧です。'
      const listUrl = `${siteUrl}/notes`
      const listHtml = injectOgp(indexHtml, listTitle, listDesc, listUrl, 'website')
      fs.writeFileSync(path.resolve(notesOutDir, 'index.html'), listHtml, 'utf-8')
      count++

      console.log(`\u2713 OGP prerender HTML generated: ${count} files`)
    },
  }
}

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    ...(mode === 'production' ? [sitemapGeneratorPlugin(), ogpPrerenderPlugin()] : []),
  ],
  base: mode === 'production' ? '/japan-etf-analyzer/' : '/',
  server: {
    host: '0.0.0.0',
    port: 3902,
  },
}))
