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
    // Read document ID from query param: /documents/modify?id=...
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
                if (!factory) throw new Error('EditorModule not found on window')

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

                editor.setContent('')

                if (!cancelled) {
                    editorRef.current = editor
                    setWasmReady(true)
                }
            } catch (err: any) {
                if (!cancelled) {
                    console.error('WASM load error:', err)
                    setWasmError(err.message || 'Failed to load editor')
                }
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
                const res = await fetch(`${API_BASE}/api/documents/${driveFileId}/content`, {
                    credentials: 'include',
                })

                if (!res.ok) {
                    if (res.status === 401) throw new Error('Not authorized. Please log in.')
                    throw new Error(`Failed to fetch document content (${res.status})`)
                }

                const data = await res.json()

                if (!cancelled && editorRef.current) {
                    editorRef.current.setContent(data.content || '')
                    setEditorContent(editorRef.current.getContent())
                    setCursorPos(editorRef.current.getCursor())
                }
            } catch (err: any) {
                if (!cancelled) {
                    console.error('Content fetch error:', err)
                    setLoadError(err.message)
                }
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

        if (e.key === 'Tab') {
            e.preventDefault()
            ed.insertStr('    ')
            syncFromWasm()
            return
        }
        if (e.key === 'Backspace') {
            e.preventDefault()
            ed.deleteChar()
            syncFromWasm()
            return
        }
        if (e.key === 'Delete') {
            e.preventDefault()
            ed.deleteForward()
            syncFromWasm()
            return
        }
        if (e.key === 'ArrowLeft') {
            e.preventDefault()
            ed.moveLeft()
            syncFromWasm()
            return
        }
        if (e.key === 'ArrowRight') {
            e.preventDefault()
            ed.moveRight()
            syncFromWasm()
            return
        }
        if (e.key === 'Enter') {
            e.preventDefault()
            ed.insertStr('\n')
            syncFromWasm()
            return
        }
        if (e.key === 'Home') {
            e.preventDefault()
            const content = ed.getContent()
            const cursor = ed.getCursor()
            let lineStart = content.lastIndexOf('\n', cursor - 1)
            lineStart = lineStart === -1 ? 0 : lineStart + 1
            ed.setCursor(lineStart)
            syncFromWasm()
            return
        }
        if (e.key === 'End') {
            e.preventDefault()
            const content = ed.getContent()
            const cursor = ed.getCursor()
            let lineEnd = content.indexOf('\n', cursor)
            if (lineEnd === -1) lineEnd = content.length
            ed.setCursor(lineEnd)
            syncFromWasm()
            return
        }
        if (e.ctrlKey || e.metaKey) return
        if (e.key.length !== 1) return

        e.preventDefault()
        ed.insert(e.key.charCodeAt(0))
        syncFromWasm()
    }, [syncFromWasm])

    /* ---------------------------------------------------------------- */
    /*  Insert special character                                         */
    /* ---------------------------------------------------------------- */
    const insertSpecialChar = useCallback((char: string) => {
        const ed = editorRef.current
        if (!ed) return
        ed.insertStr(char)
        syncFromWasm()
        editorAreaRef.current?.focus()
    }, [syncFromWasm])

    /* ---------------------------------------------------------------- */
    /*  Save handler — updates existing Drive file                       */
    /* ---------------------------------------------------------------- */
    const handleSave = useCallback(async () => {
        const ed = editorRef.current
        if (!ed || saving) return

        setSaving(true)
        setSaveStatus('saving')

        try {
            const content = ed.getContent()
            let docId = localDocId

            if (!docId) {
                const createRes = await fetch(`${API_BASE}/api/documents/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ title, content, drive_file_id: driveFileId || undefined }),
                })
                if (!createRes.ok) throw new Error(`Create failed: ${await createRes.text()}`)
                const doc = await createRes.json()
                docId = doc.id
                setLocalDocId(docId)
            } else {
                const updateRes = await fetch(`${API_BASE}/api/documents/${docId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ title, content }),
                })
                if (!updateRes.ok) throw new Error(`Update failed: ${await updateRes.text()}`)
            }

            const driveRes = await fetch(`${API_BASE}/api/documents/${docId}/drive`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
            })
            if (!driveRes.ok) throw new Error(`Drive sync failed: ${await driveRes.text()}`)

            setSaveStatus('saved')
            setTimeout(() => setSaveStatus('idle'), 3000)
        } catch (err: any) {
            console.error('Save error:', err)
            setSaveStatus('error')
            setTimeout(() => setSaveStatus('idle'), 4000)
        } finally {
            setSaving(false)
        }
    }, [saving, localDocId, title])

    /* ---------------------------------------------------------------- */
    /*  Render cursor inside text                                        */
    /* ---------------------------------------------------------------- */
    const renderEditorContent = () => {
        const before = editorContent.slice(0, cursorPos)
        const after = editorContent.slice(cursorPos)
        return (
            <>
                <span>{before}</span>
                <span style={{
                    display: 'inline',
                    borderLeft: cursorVisible ? '2px solid #00ff9d' : '2px solid transparent',
                    marginLeft: '-1px', marginRight: '-1px',
                }} />
                <span>{after || ' '}</span>
            </>
        )
    }

    const isReady = wasmReady && !loadingContent && !loadError

    /* ---------------------------------------------------------------- */
    /*  JSX                                                              */
    /* ---------------------------------------------------------------- */
    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            background: 'radial-gradient(circle at center, #1a1a1a 0%, #000000 100%)',
            color: '#ffffff',
            fontFamily: 'system-ui, -apple-system, sans-serif',
        }}>
            {/* Background glow */}
            <div style={{
                position: 'fixed', top: '30%', left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '800px', height: '800px',
                background: 'rgba(0, 255, 157, 0.03)',
                filter: 'blur(150px)', borderRadius: '50%',
                zIndex: 0, pointerEvents: 'none',
            }} />

            {/* ========== MENU BAR ========== */}
            <header style={{
                position: 'sticky', top: 0, zIndex: 100,
                display: 'flex', alignItems: 'center', gap: '1rem',
                padding: '0.75rem 1.5rem',
                background: 'rgba(10, 10, 10, 0.85)',
                backdropFilter: 'blur(20px)',
                borderBottom: '1px solid rgba(255,255,255,0.08)',
            }}>
                <a href="/documents"
                    style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.85rem', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.3rem', transition: 'color 0.2s' }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#00ff9d')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'rgba(255,255,255,0.5)')}
                >← Documents</a>

                <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.1)' }} />

                <span style={{
                    padding: '0.25rem 0.6rem', borderRadius: '6px',
                    background: 'rgba(0,255,157,0.1)', color: '#00ff9d',
                    fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em',
                }}>Editing</span>

                <input type="text" value={title}
                    onChange={e => setTitle(e.target.value)}
                    placeholder="Document title..."
                    style={{
                        flex: 1, background: 'transparent', border: '1px solid transparent',
                        borderRadius: '8px', padding: '0.5rem 0.75rem',
                        color: '#ffffff', fontSize: '1rem', fontWeight: 600, outline: 'none',
                        transition: 'border-color 0.2s, background 0.2s',
                    }}
                    onFocus={e => { e.currentTarget.style.borderColor = 'rgba(0,255,157,0.3)'; e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
                    onBlur={e => { e.currentTarget.style.borderColor = 'transparent'; e.currentTarget.style.background = 'transparent' }}
                />

                {saveStatus === 'saved' && <span style={{ color: '#00ff9d', fontSize: '0.85rem', fontWeight: 500 }}>✓ Saved</span>}
                {saveStatus === 'error' && <span style={{ color: '#ff3b30', fontSize: '0.85rem', fontWeight: 500 }}>✗ Error</span>}

                <button onClick={handleSave} disabled={saving || !isReady}
                    style={{
                        padding: '0.5rem 1.5rem', background: saving ? 'rgba(0,255,157,0.3)' : '#00ff9d',
                        color: '#000000', border: 'none', borderRadius: '8px',
                        fontWeight: 600, fontSize: '0.9rem',
                        cursor: saving ? 'not-allowed' : 'pointer',
                        transition: 'all 0.2s', opacity: isReady ? 1 : 0.4,
                    }}
                    onMouseEnter={e => { if (!saving) { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,255,157,0.3)' } }}
                    onMouseLeave={e => { e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none' }}
                >{saving ? '⟳ Saving...' : '💾 Save'}</button>
            </header>

            {/* ========== SPECIAL CHARACTER BAR ========== */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.5rem 1.5rem',
                background: 'rgba(255,255,255,0.02)',
                borderBottom: '1px solid rgba(255,255,255,0.05)',
                zIndex: 10, position: 'relative', overflowX: 'auto',
            }}>
                <span style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.05em', marginRight: '0.5rem', whiteSpace: 'nowrap' }}>Insert:</span>
                {SPECIAL_CHARS.map((sc) => (
                    <button key={sc.char} title={sc.title} onClick={() => insertSpecialChar(sc.char)} disabled={!isReady}
                        style={{
                            padding: '0.35rem 0.75rem', background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.08)', borderRadius: '6px',
                            color: '#ffffff', fontSize: '1rem',
                            cursor: isReady ? 'pointer' : 'not-allowed',
                            transition: 'all 0.2s', opacity: isReady ? 1 : 0.4,
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,255,157,0.15)'; e.currentTarget.style.borderColor = 'rgba(0,255,157,0.4)'; e.currentTarget.style.color = '#00ff9d' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#ffffff' }}
                    >{sc.label}</button>
                ))}
            </div>

            {/* ========== EDITOR AREA ========== */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '1.5rem', position: 'relative', zIndex: 1 }}>
                {wasmError || loadError ? (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                        <div style={{
                            background: 'rgba(255, 59, 48, 0.1)', border: '1px solid rgba(255, 59, 48, 0.2)',
                            padding: '2rem 3rem', borderRadius: '16px', textAlign: 'center', maxWidth: '500px',
                        }}>
                            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>⚠️</div>
                            <h3 style={{ color: '#ff3b30', fontSize: '1.1rem', marginBottom: '0.5rem' }}>
                                {wasmError ? 'Editor Load Failed' : 'Content Load Failed'}
                            </h3>
                            <p style={{ color: 'rgba(255,255,255,0.7)', fontSize: '0.9rem' }}>{wasmError || loadError}</p>
                            {loadError?.includes('authorized') && (
                                <button onClick={() => window.location.href = 'http://localhost:8000/auth/google/login'}
                                    style={{ marginTop: '1.5rem', padding: '0.75rem 2rem', background: '#00ff9d', color: '#000', border: 'none', borderRadius: '8px', fontWeight: 600, cursor: 'pointer' }}
                                >Login with Google</button>
                            )}
                        </div>
                    </div>
                ) : !isReady ? (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                        <div style={{ width: '40px', height: '40px', border: '3px solid rgba(0,255,157,0.3)', borderTop: '3px solid #00ff9d', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.9rem' }}>
                            {!wasmReady ? 'Loading editor...' : 'Fetching document from Drive...'}
                        </p>
                    </div>
                ) : (
                    <div ref={editorAreaRef} tabIndex={0} onKeyDown={handleKeyDown}
                        onClick={() => editorAreaRef.current?.focus()}
                        style={{
                            flex: 1, background: 'rgba(255,255,255,0.02)',
                            border: '1px solid rgba(255,255,255,0.06)', borderRadius: '16px',
                            padding: '1.5rem',
                            fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace",
                            fontSize: '0.95rem', lineHeight: '1.7', color: 'rgba(255,255,255,0.9)',
                            outline: 'none', cursor: 'text', minHeight: '400px',
                            whiteSpace: 'pre-wrap', wordBreak: 'break-all', overflowY: 'auto',
                            transition: 'border-color 0.2s', position: 'relative',
                        }}
                        onFocus={e => { e.currentTarget.style.borderColor = 'rgba(0,255,157,0.2)' }}
                        onBlur={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)' }}
                    >
                        {editorContent.length === 0 && cursorPos === 0 ? (
                            <>
                                <span style={{ display: 'inline', borderLeft: cursorVisible ? '2px solid #00ff9d' : '2px solid transparent' }} />
                                <span style={{ color: 'rgba(255,255,255,0.2)' }}>Start typing...</span>
                            </>
                        ) : renderEditorContent()}
                    </div>
                )}
            </div>

            {/* ========== STATUS BAR ========== */}
            <footer style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '0.4rem 1.5rem',
                background: 'rgba(10, 10, 10, 0.85)', borderTop: '1px solid rgba(255,255,255,0.05)',
                fontSize: '0.75rem', color: 'rgba(255,255,255,0.35)', zIndex: 10,
            }}>
                <span>
                    {isReady
                        ? <><span style={{ color: '#00ff9d' }}>●</span> WASM Editor Ready</>
                        : <><span style={{ color: '#ff9500' }}>●</span> Loading...</>}
                </span>
                <span>
                    Ln {editorContent.slice(0, cursorPos).split('\n').length} ·
                    Col {(() => { const lines = editorContent.slice(0, cursorPos).split('\n'); return lines[lines.length - 1].length + 1 })()} ·
                    {editorContent.length} chars
                </span>
            </footer>

            <style jsx global>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    )
}
