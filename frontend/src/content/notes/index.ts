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

/** publishedAtが現在日時以前かを判定（JST基準） */
function isPublished(publishedAt: string): boolean {
  // 現在の日時をJST文字列として取得（YYYY-MM-DD HH:mm:ss形式）
  const nowJST = new Date().toLocaleString('sv-SE', { timeZone: 'Asia/Tokyo' })
  // publishedAtを正規化（YYYY-MM-DDのみなら00:00:00、HH:mmなら:00を付与）
  const normalized = publishedAt.includes(' ')
    ? publishedAt + ':00'
    : publishedAt + ' 00:00:00'
  return nowJST >= normalized
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

/** 全ノートを公開日降順で取得（未公開記事を除外） */
export function getAllNotes(): Note[] {
  return [...notes]
    .filter((note) => isPublished(note.publishedAt))
    .sort((a, b) => {
      const timeA = new Date(a.publishedAt).getTime()
      const timeB = new Date(b.publishedAt).getTime()
      if (isNaN(timeA) || isNaN(timeB)) return 0
      return timeB - timeA
    })
}

/** スラッグでノートを検索（未公開記事はundefined） */
export function getNoteBySlug(slug: string): Note | undefined {
  const note = notes.find((n) => n.slug === slug)
  if (!note || !isPublished(note.publishedAt)) return undefined
  return note
}
