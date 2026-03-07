'use client'

import React, { useEffect, useState, useRef, useCallback } from 'react'

/* ------------------------------------------------------------------ */
/*  Types for the WASM editor module                                   */
/* ------------------------------------------------------------------ */
interface WasmEditor {
    insert: (ch: number) => void
    insertStr: (s: string) => void
    deleteChar: () => void
    deleteForward: () => void
    getContent: () => string
    setContent: (s: string) => void
    getCursor: () => number
    setCursor: (pos: number) => void
    moveLeft: () => void
    moveRight: () => void
}

const API_BASE = 'http://localhost:8000'

/* ------------------------------------------------------------------ */
/*  Special characters for the button bar                              */
/* ------------------------------------------------------------------ */
const SPECIAL_CHARS = [
    { label: 'Ω', char: 'Ω', title: 'Greek Capital Omega (U+03A9)' },
    { label: '∑', char: '∑', title: 'N-Ary Summation (U+2211)' },
    { label: 'Δ', char: 'Δ', title: 'Greek Capital Delta (U+0394)' },
    { label: 'π', char: 'π', title: 'Greek Small Pi (U+03C0)' },
    { label: '∞', char: '∞', title: 'Infinity (U+221E)' },
    { label: '√', char: '√', title: 'Square Root (U+221A)' },
    { label: '≠', char: '≠', title: 'Not Equal To (U+2260)' },
    { label: '≤', char: '≤', title: 'Less Than or Equal (U+2264)' },
    { label: '≥', char: '≥', title: 'Greater Than or Equal (U+2265)' },
    { label: '±', char: '±', title: 'Plus-Minus Sign (U+00B1)' },
]

export default function DocumentModifyPage() {
    const [driveFileId, setDriveFileId] = useState<string>('')
    const [title, setTitle] = useState('Loading...')
    const [saving, setSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
    const [localDocId, setLocalDocId] = useState<string | null>(null)
    const [editorContent, setEditorContent] = useState('')
    const [cursorPos, setCursorPos] = useState(0)
    const [wasmReady, setWasmReady] = useState(false)
    const [wasmError, setWasmError] = useState<string | null>(null)
    const [loadingContent, setLoadingContent] = useState(true)
    const [loadError, setLoadError] = useState<string | null>(null)

    const editorRef = useRef<WasmEditor | null>(null)
    const editorAreaRef = useRef<HTMLDivElement | null>(null)
    const [cursorVisible, setCursorVisible] = useState(true)

    /* ---------------------------------------------------------------- */
    /*  Read ?id= query param on mount                                   */
    /* ---------------------------------------------------------------- */
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const id = params.get('id') || ''
        const urlTitle = params.get('title') || 'Untitled'
        setDriveFileId(id)
        setTitle(urlTitle)
        if (!id) {
            setLoadError('No document ID provided in URL')
            setLoadingContent(false)
        }
    }, [])

    /* ---------------------------------------------------------------- */
    /*  Blink cursor                                                     */
    /* ---------------------------------------------------------------- */
    useEffect(() => {
        const timer = setInterval(() => setCursorVisible(v => !v), 530)
        return () => clearInterval(timer)
    }, [])

    /* ---------------------------------------------------------------- */
    /*  Load WASM module                                                 */
    /* ---------------------------------------------------------------- */
    useEffect(() => {
        let cancelled = false
        async function loadWasm() {
            try {
                const script = document.createElement('script')
                script.src = '/wasm/editor.js'
                script.async = true
                const loaded = new Promise<void>((resolve, reject) => {
                    script.onload = () => resolve()
                    script.onerror = () => reject(new Error('Failed to load WASM script'))
                })
                document.head.appendChild(script)
                await loaded

                const factory = (window as any).EditorModule
                const Module = await factory()

                const editor: WasmEditor = {
                    insert: Module.cwrap('editor_insert', null, ['number']),
                    insertStr: Module.cwrap('editor_insert_str', null, ['string']),
                    deleteChar: Module.cwrap('editor_delete', null, []),
                    deleteForward: Module.cwrap('editor_delete_forward', null, []),
                    getContent: Module.cwrap('editor_get_content', 'string', []),
                    setContent: Module.cwrap('editor_set_content', null, ['string']),
                    getCursor: Module.cwrap('editor_get_cursor', 'number', []),
                    setCursor: Module.cwrap('editor_set_cursor', null, ['number']),
                    moveLeft: Module.cwrap('editor_move_left', null, []),
                    moveRight: Module.cwrap('editor_move_right', null, []),
                }
                if (!cancelled) {
                    editorRef.current = editor
                    setWasmReady(true)
                }
            } catch (err: any) {
                if (!cancelled) setWasmError(err.message || 'Failed to load editor')
            }
        }
        loadWasm()
        return () => { cancelled = true }
    }, [])

    /* ---------------------------------------------------------------- */
    /*  Fetch document content from Google Drive                         */
    /* ---------------------------------------------------------------- */
    useEffect(() => {
        if (!wasmReady || !driveFileId) return
        let cancelled = false
        async function fetchContent() {
            try {
                const res = await fetch(`${API_BASE}/api/documents/${driveFileId}/content`, { credentials: 'include' })
                if (!res.ok) throw new Error(`Failed to fetch content (${res.status})`)
                const data = await res.json()
                if (!cancelled && editorRef.current) {
                    editorRef.current.setContent(data.content || '')
                    setEditorContent(editorRef.current.getContent())
                    setCursorPos(editorRef.current.getCursor())
                }
            } catch (err: any) {
                if (!cancelled) setLoadError(err.message)
            } finally {
                if (!cancelled) setLoadingContent(false)
            }
        }
        fetchContent()
        return () => { cancelled = true }
    }, [wasmReady, driveFileId])

    /* ---------------------------------------------------------------- */
    /*  Sync state from WASM                                             */
    /* ---------------------------------------------------------------- */
    const syncFromWasm = useCallback(() => {
        const ed = editorRef.current
        if (!ed) return
        setEditorContent(ed.getContent())
        setCursorPos(ed.getCursor())
    }, [])

    /* ---------------------------------------------------------------- */
    /*  Keyboard handler                                                 */
    /* ---------------------------------------------------------------- */
    const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
        const ed = editorRef.current
        if (!ed) return
        if (e.key === 'Tab') { e.preventDefault(); ed.insertStr('    '); syncFromWasm(); return }
        if (e.key === 'Backspace') { e.preventDefault(); ed.deleteChar(); syncFromWasm(); return }
        if (e.key === 'Delete') { e.preventDefault(); ed.deleteForward(); syncFromWasm(); return }
        if (e.key === 'ArrowLeft') { e.preventDefault(); ed.moveLeft(); syncFromWasm(); return }
        if (e.key === 'ArrowRight') { e.preventDefault(); ed.moveRight(); syncFromWasm(); return }
        if (e.key === 'Enter') { e.preventDefault(); ed.insertStr('\n'); syncFromWasm(); return }
        if (e.key === 'Home') {
            e.preventDefault()
            const content = ed.getContent(); const cursor = ed.getCursor(); let start = content.lastIndexOf('\n', cursor - 1);
            ed.setCursor(start === -1 ? 0 : start + 1); syncFromWasm(); return
        }
        if (e.key === 'End') {
            e.preventDefault()
            const content = ed.getContent(); const cursor = ed.getCursor(); let end = content.indexOf('\n', cursor);
            ed.setCursor(end === -1 ? content.length : end); syncFromWasm(); return
        }
        if (e.ctrlKey || e.metaKey) return
        if (e.key.length !== 1) return
        e.preventDefault(); ed.insert(e.key.charCodeAt(0)); syncFromWasm()
    }, [syncFromWasm])

    const insertSpecialChar = useCallback((char: string) => {
        const ed = editorRef.current
        if (!ed) return
        ed.insertStr(char); syncFromWasm(); editorAreaRef.current?.focus()
    }, [syncFromWasm])

    const handleSave = useCallback(async () => {
        const ed = editorRef.current
        if (!ed || saving) return
        setSaving(true); setSaveStatus('saving')
        try {
            const content = ed.getContent(); let docId = localDocId
            if (!docId) {
                const res = await fetch(`${API_BASE}/api/documents/`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ title, content, drive_file_id: driveFileId || undefined }),
                })
                if (!res.ok) throw new Error('Create failed')
                const doc = await res.json(); docId = doc.id; setLocalDocId(docId)
            } else {
                const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
                    method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
                    body: JSON.stringify({ title, content }),
                })
                if (!res.ok) throw new Error('Update failed')
            }
            const dr = await fetch(`${API_BASE}/api/documents/${docId}/drive`, { method: 'POST', credentials: 'include' })
            if (!dr.ok) throw new Error('Drive sync failed')
            setSaveStatus('saved'); setTimeout(() => setSaveStatus('idle'), 3000)
        } catch (err: any) {
            setSaveStatus('error'); setTimeout(() => setSaveStatus('idle'), 4000)
        } finally { setSaving(false) }
    }, [saving, localDocId, title, driveFileId])

    const renderEditorContent = () => {
        const before = editorContent.slice(0, cursorPos); const after = editorContent.slice(cursorPos)
        return <><span>{before}</span><span style={{ display: 'inline', borderLeft: cursorVisible ? '2px solid var(--primary)' : '2px solid transparent', marginLeft: '-1px', marginRight: '-1px' }} /><span>{after || ' '}</span></>
    }

    const isReady = wasmReady && !loadingContent && !loadError
    const lines = editorContent.split('\n')
    const currentLineIdx = editorContent.slice(0, cursorPos).split('\n').length - 1

    return (
        <div className="oscilloscope-grid" style={{
            minHeight: '100vh', display: 'flex', flexDirection: 'column',
            color: 'var(--foreground)', fontFamily: 'var(--font-inter), system-ui, sans-serif',
        }}>
            <div style={{ position: 'fixed', top: '10%', left: '10%', width: '800px', height: '600px', background: 'radial-gradient(ellipse at center, rgba(0,100,255,0.08) 0%, transparent 70%)', zIndex: 0, pointerEvents: 'none' }} />

            <header style={{
                position: 'sticky', top: 0, zIndex: 100, display: 'flex', alignItems: 'center', gap: '1rem', padding: '0 1.5rem', height: '52px',
                background: 'var(--secondary)', backdropFilter: 'blur(20px)', borderBottom: '1px solid var(--border)',
                boxShadow: '0 1px 0 rgba(0,170,255,0.1), 0 4px 20px rgba(0,0,0,0.4)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--primary)', fontWeight: 700, letterSpacing: '0.1em' }}><span style={{ fontSize: '1.2rem' }}>⚡</span> E-SIM</div>
                <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.1)', marginLeft: '0.5rem' }} />

                <a href="/documents" style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textDecoration: 'none' }} onMouseEnter={e => (e.currentTarget.style.color = 'var(--primary)')} onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>Projects</a>

                <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ padding: '0.2rem 0.5rem', background: 'var(--primary-dim)', color: 'var(--primary)', borderRadius: '4px', fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase' }}>EDITING</span>
                    <input type="text" value={title} onChange={e => setTitle(e.target.value)} style={{ width: '100%', maxWidth: '350px', background: 'var(--glass)', border: '1px solid var(--border)', borderRadius: '6px', padding: '0.4rem 0.75rem', color: 'var(--foreground)', fontSize: '0.95rem', fontWeight: 600, outline: 'none', textAlign: 'center' }} />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ fontSize: '0.8rem' }}>
                        {saveStatus === 'saving' && <span style={{ color: '#ffb300' }}>● Saving...</span>}
                        {saveStatus === 'saved' && <span style={{ color: 'var(--success)' }}>● Saved to Drive</span>}
                        {saveStatus === 'error' && <span style={{ color: 'var(--error)' }}>● Save failed</span>}
                    </div>
                    <button onClick={handleSave} disabled={saving || !isReady} style={{ padding: '8px 20px', background: saving ? 'rgba(0,170,255,0.3)' : 'linear-gradient(135deg, #0066cc 0%, #00aaff 100%)', color: '#ffffff', borderRadius: '8px', fontWeight: 600, fontSize: '0.85rem' }}>{saving ? 'Saving...' : 'Save to Drive'}</button>
                </div>
            </header>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0 1rem', height: '40px', background: '#060f1e', borderBottom: '1px solid rgba(0,170,255,0.12)', zIndex: 10 }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Symbols ▸</span>
                {SPECIAL_CHARS.map(sc => (
                    <button key={sc.char} onClick={() => insertSpecialChar(sc.char)} disabled={!isReady} style={{ width: '28px', height: '28px', background: 'rgba(0,170,255,0.08)', border: '1px solid rgba(0,170,255,0.25)', borderRadius: '5px', color: 'var(--primary)', fontFamily: 'monospace' }}>{sc.label}</button>
                ))}
            </div>

            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative', zIndex: 1 }}>
                <div style={{ width: '52px', background: 'rgba(0,0,0,0.3)', borderRight: '1px solid rgba(0,170,255,0.1)', display: 'flex', flexDirection: 'column', paddingTop: '16px' }}>
                    {lines.map((_, i) => (
                        <div key={i} style={{ fontSize: '0.85rem', color: i === currentLineIdx ? 'var(--primary)' : 'var(--text-muted)', textAlign: 'right', padding: '0 12px', lineHeight: '1.7', fontFamily: 'monospace' }}>{i + 1}</div>
                    ))}
                </div>

                {!isReady ? (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                        <div style={{ width: '40px', height: '40px', border: '3px solid rgba(0,170,255,0.3)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{!wasmReady ? 'Initializing WASM Engine...' : 'Fetching document from Drive...'}</p>
                    </div>
                ) : (
                    <div ref={editorAreaRef} tabIndex={0} onKeyDown={handleKeyDown} onClick={() => editorAreaRef.current?.focus()} style={{ flex: 1, padding: '16px 20px', outline: 'none', cursor: 'text', fontFamily: "'JetBrains Mono', 'Fira Code', monospace", fontSize: '14px', lineHeight: '1.7', color: 'var(--foreground)', whiteSpace: 'pre-wrap', overflowY: 'auto' }}>
                        {renderEditorContent()}
                    </div>
                )}
            </div>

            <footer style={{ height: '28px', background: '#000c1e', display: 'flex', alignItems: 'center', gap: '1.5rem', padding: '0 1rem', borderTop: '1px solid rgba(0,170,255,0.15)', fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'monospace', zIndex: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><span style={{ color: isReady ? 'var(--primary)' : '#ff9500' }}>●</span> {isReady ? 'CONNECTED' : 'STANDBY'}</div>
                <div>Ln {currentLineIdx + 1}, Col {(() => { const lines = editorContent.slice(0, cursorPos).split('\n'); return lines[lines.length - 1].length + 1 })()}</div>
                <div>{editorContent.length} chars</div>
                <div>UTF-8</div>
                <div style={{ marginLeft: 'auto' }}>E-SIM ENGINE V1.0 (WASM)</div>
            </footer>

            <style jsx global>{` @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } } `}</style>
        </div>
    )
}
