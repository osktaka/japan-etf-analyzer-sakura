/** ノート記事の型定義 */
export interface Note {
  slug: string
  title: string
  summary: string
  publishedAt: string
  updatedAt?: string
  content: string
}

/** 簡易frontmatterパーサー */
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

/** MDファイルを一括読み込み */
const mdModules = import.meta.glob('./*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

/** MDファイルからNote配列を構築 */
const notes: Note[] = Object.entries(mdModules).map(([path, raw]) => {
  const fileName = path.split('/').pop()?.replace('.md', '') ?? ''
  const { meta, content } = parseFrontmatter(raw)
  return {
    slug: fileName,
    title: meta.title ?? '',
    summary: meta.summary ?? '',
    publishedAt: meta.publishedAt ?? '',
    updatedAt: meta.updatedAt,
    content: content.trim(),
  }
})

/** 全ノートを公開日降順で取得 */
export function getAllNotes(): Note[] {
  return [...notes].sort((a, b) => {
    const timeA = new Date(a.publishedAt).getTime()
    const timeB = new Date(b.publishedAt).getTime()
    if (isNaN(timeA) || isNaN(timeB)) return 0
    return timeB - timeA
  })
}

/** スラッグでノートを検索 */
export function getNoteBySlug(slug: string): Note | undefined {
  return notes.find((note) => note.slug === slug)
}
