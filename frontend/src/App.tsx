import { useState, useRef, DragEvent } from 'react'
import { ingest, analyze, generatePPT, Slide } from './api'

type Step = 'input' | 'analyzing' | 'headings' | 'generating' | 'done'

export default function App() {
  const [text, setText] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [step, setStep] = useState<Step>('input')
  const [content, setContent] = useState('')
  const [headings, setHeadings] = useState<string[]>([])
  const [title, setTitle] = useState('My Presentation')
  const [error, setError] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  function handleFileDrop(e: DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const dropped = Array.from(e.dataTransfer.files)
    setFiles(prev => [...prev, ...dropped])
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      setFiles(prev => [...prev, ...Array.from(e.target.files!)])
    }
  }

  function removeFile(i: number) {
    setFiles(prev => prev.filter((_, idx) => idx !== i))
  }

  async function handleAnalyze() {
    if (!text.trim() && files.length === 0) {
      setError('Enter text or upload files')
      return
    }
    setError('')
    setStep('analyzing')
    try {
      const c = await ingest(text, files)
      setContent(c)
      const h = await analyze(c)
      setHeadings(h)
      setStep('headings')
    } catch (e: any) {
      setError(e.message || 'Analysis failed')
      setStep('input')
    }
  }

  function updateHeading(i: number, val: string) {
    setHeadings(prev => prev.map((h, idx) => idx === i ? val : h))
  }

  async function handleGenerate() {
    const valid = headings.filter(h => h.trim())
    if (valid.length === 0) {
      setError('At least one heading required')
      return
    }
    setError('')
    setStep('generating')
    try {
      const slides: Slide[] = valid.map(h => ({ heading: h, bullets: [] }))
      const blob = await generatePPT(title, slides, content)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'presentation.pptx'
      a.click()
      URL.revokeObjectURL(url)
      setStep('done')
    } catch (e: any) {
      setError(e.message || 'Generation failed')
      setStep('headings')
    }
  }

  function handleReset() {
    setText('')
    setFiles([])
    setContent('')
    setHeadings([])
    setTitle('My Presentation')
    setError('')
    setStep('input')
  }

  return (
    <div className="app">
      <h1>AI Presentation Maker</h1>
      <p className="subtitle">Upload your content, get AI-generated slides in seconds</p>

      <div className="card">
        <h2><span className="step">1</span> Provide Your Content</h2>
        <textarea
          placeholder="Paste your text here, or upload files below..."
          value={text}
          onChange={e => setText(e.target.value)}
        />
        <div
          className={`upload-zone ${dragOver ? 'dragover' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleFileDrop}
          onClick={() => fileRef.current?.click()}
        >
          {files.length === 0 ? (
            <p>Drop PDF or image files here, or click to browse</p>
          ) : (
            <div className="files">
              {files.map((f, i) => (
                <span key={i} className="file-tag">
                  {f.name}
                  <button onClick={e => { e.stopPropagation(); removeFile(i) }}>&times;</button>
                </span>
              ))}
            </div>
          )}
        </div>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.gif,.bmp"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />
        <div className="actions">
          <button className="btn btn-primary" onClick={handleAnalyze} disabled={step === 'analyzing'}>
            {step === 'analyzing' ? (
              <span className="loading"><span className="spinner" /> Analyzing...</span>
            ) : (
              'Analyze Content'
            )}
          </button>
        </div>
      </div>

      {content && step !== 'input' && (
        <div className="card">
          <h2>Extracted Content</h2>
          <div className="extracted-content">{content.slice(0, 2000)}{content.length > 2000 ? '...' : ''}</div>
        </div>
      )}

      {(step === 'headings' || step === 'generating' || step === 'done') && (
        <div className="card">
          <h2><span className="step">2</span> Review & Edit Slide Headings</h2>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 13, color: '#888' }}>Presentation title</label>
            <input
              style={{
                width: '100%', marginTop: 4, padding: '8px 12px',
                background: '#12121f', border: '1px solid #2a2a3e',
                borderRadius: 6, color: '#e0e0e0', fontSize: 14,
              }}
              value={title}
              onChange={e => setTitle(e.target.value)}
            />
          </div>
          <div className="heading-list">
            {headings.map((h, i) => (
              <div className="heading-row" key={i}>
                <span className="num">{i + 1}</span>
                <input value={h} onChange={e => updateHeading(i, e.target.value)} />
              </div>
            ))}
          </div>
          <div className="actions">
            {step === 'headings' && (
              <button className="btn btn-success" onClick={handleGenerate}>
                Generate PowerPoint
              </button>
            )}
            {step === 'generating' && (
              <span className="loading"><span className="spinner" /> Generating slides...</span>
            )}
            {step === 'done' && (
              <>
                <span className="success-msg">Presentation downloaded!</span>
                <button className="btn btn-primary" onClick={handleReset}>Create Another</button>
              </>
            )}
          </div>
        </div>
      )}

      {error && <p className="error-msg">{error}</p>}
    </div>
  )
}
