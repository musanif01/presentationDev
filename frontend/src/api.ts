export async function ingest(text: string, files: File[]): Promise<string> {
  const form = new FormData()
  form.append('text', text)
  for (const f of files) form.append('files', f)
  const res = await fetch('/api/ingest', { method: 'POST', body: form })
  if (!res.ok) throw new Error((await res.json()).detail || 'Ingest failed')
  const data = await res.json()
  return data.content
}

export async function analyze(content: string): Promise<string[]> {
  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error((await res.json()).detail || 'Analysis failed')
  const data = await res.json()
  return data.headings
}

export interface Slide {
  heading: string
  bullets: string[]
}

export async function generatePPT(title: string, slides: Slide[], content: string): Promise<Blob> {
  const res = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, slides, content }),
  })
  if (!res.ok) throw new Error((await res.json()).detail || 'Generation failed')
  return await res.blob()
}
