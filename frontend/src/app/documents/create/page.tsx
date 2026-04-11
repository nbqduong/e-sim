'use client'

import React, { useEffect, useState, useRef, useCallback } from 'react'
import { backendUrl } from '../../../lib/backend'

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

interface Project {
    id: string
    title: string
    description: string
}

export default function DocumentCreatePage() {
    const [title, setTitle] = useState('Untitled')
    const [saving, setSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
    const [saveMessage, setSaveMessage] = useState('')
    const [documentId, setDocumentId] = useState<string | null>(null)
    const [editorContent, setEditorContent] = useState('')
    const [cursorPos, setCursorPos] = useState(0)
    const [wasmReady, setWasmReady] = useState(false)
    const [wasmError, setWasmError] = useState<string | null>(null)

    const [projects, setProjects] = useState<Project[]>([])
    const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
    const [projectsLoading, setProjectsLoading] = useState(true)

    const editorRef = useRef<WasmEditor | null>(null)
    const editorAreaRef = useRef<HTMLDivElement | null>(null)
    const [cursorVisible, setCursorVisible] = useState(true)

    /* ---------------------------------------------------------------- */
    /*  Blink cursor                                                     */
    /* ---------------------------------------------------------------- */
    useEffect(() => {
        const timer = setInterval(() => setCursorVisible(v => !v), 530)
        return () => clearInterval(timer)
    }, [])

    /* ---------------------------------------------------------------- */
    /*  Fetch projects on mount                                          */
    /* ---------------------------------------------------------------- */
    useEffect(() => {
        async function fetchProjects() {
            try {
                const res = await fetch(backendUrl('/api/projects/'), {
                    credentials: 'include',
                })
                if (!res.ok) return
                const data = await res.json()
                const list: Project[] = data.projects || []
                setProjects(list)
                if (list.length > 0) {
                    const params = new URLSearchParams(window.location.search)
                    const requestedProjectId = params.get('projectId')
                    const matchedProject = requestedProjectId
                        ? list.find((project) => project.id === requestedProjectId)
                        : null
                    setSelectedProjectId(matchedProject?.id ?? list[0].id)
                }
            } catch {
                // ignore
            } finally {
                setProjectsLoading(false)
            }
        }
        fetchProjects()
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
    /*  Save to database handler                                         */
    /* ---------------------------------------------------------------- */
    const handleSave = useCallback(async () => {
        const ed = editorRef.current
        if (!ed || saving) return
        if (!selectedProjectId) {
            setSaveStatus('error')
            setSaveMessage('Select a project first')
            setTimeout(() => setSaveStatus('idle'), 3000)
            return
        }

        setSaving(true)
        setSaveStatus('saving')
        setSaveMessage('Saving...')

        try {
            const content = ed.getContent()
            let docId = documentId

            if (!docId) {
                const createRes = await fetch(backendUrl('/api/documents/'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ title, content, project_id: selectedProjectId }),
                })
                if (!createRes.ok) throw new Error(`Create failed: ${await createRes.text()}`)
                const doc = await createRes.json()
                docId = doc.id
                setDocumentId(docId)
            } else {
                const updateRes = await fetch(backendUrl(`/api/documents/${docId}`), {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'include',
                    body: JSON.stringify({ title, content }),
                })
                if (!updateRes.ok) throw new Error(`Update failed: ${await updateRes.text()}`)
            }

            setSaveStatus('saved')
            setSaveMessage('Saved')
            setTimeout(() => setSaveStatus('idle'), 3000)
        } catch (err: any) {
            console.error('Save error:', err)
            setSaveStatus('error')
            setSaveMessage(err.message || 'Save failed')
            setTimeout(() => setSaveStatus('idle'), 4000)
        } finally {
            setSaving(false)
        }
    }, [saving, documentId, title, selectedProjectId])

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
                    borderLeft: cursorVisible ? '2px solid var(--primary)' : '2px solid transparent',
                    marginLeft: '-1px', marginRight: '-1px',
                }} />
                <span>{after || ' '}</span>
            </>
        )
    }

    /* ---------------------------------------------------------------- */
    /*  Line Numbers Helper                                              */
    /* ---------------------------------------------------------------- */
    const lines = editorContent.split('\n')
    const currentLineIdx = editorContent.slice(0, cursorPos).split('\n').length - 1

    /* ---------------------------------------------------------------- */
    /*  JSX                                                              */
    /* ---------------------------------------------------------------- */
    return (
        <div className="oscilloscope-grid" style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            color: 'var(--foreground)',
            fontFamily: 'var(--font-inter), system-ui, sans-serif',
        }}>
            {/* Background glow */}
            <div style={{
                position: 'fixed', top: '10%', left: '10%',
                width: '800px', height: '600px',
                background: 'radial-gradient(ellipse at center, rgba(0,100,255,0.08) 0%, transparent 70%)',
                zIndex: 0, pointerEvents: 'none',
            }} />

            {/* ========== MENU BAR ========== */}
            <header style={{
                position: 'sticky', top: 0, zIndex: 100,
                display: 'flex', alignItems: 'center', gap: '1rem',
                padding: '0 1.5rem', height: '52px',
                background: 'var(--secondary)',
                backdropFilter: 'blur(20px)',
                borderBottom: '1px solid var(--border)',
                boxShadow: '0 1px 0 rgba(0,170,255,0.1), 0 4px 20px rgba(0,0,0,0.4)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', color: 'var(--primary)', fontWeight: 700, letterSpacing: '0.1em' }}>
                    <span style={{ fontSize: '1.2rem' }}>⚡</span> E-SIM
                </div>

                <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.1)', marginLeft: '0.5rem' }} />

                <a href="/documents" style={{ color: 'var(--text-muted)', fontSize: '0.8rem', textDecoration: 'none', transition: 'color 0.2s' }}
                    onMouseEnter={e => (e.currentTarget.style.color = 'var(--primary)')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
                >Projects</a>

                <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
                    <input type="text" value={title}
                        onChange={e => setTitle(e.target.value)}
                        placeholder="Document title..."
                        style={{
                            width: '100%', maxWidth: '400px',
                            background: 'var(--glass)', border: '1px solid var(--border)',
                            borderRadius: '6px', padding: '0.4rem 0.75rem',
                            color: 'var(--foreground)', fontSize: '0.95rem', fontWeight: 600, outline: 'none',
                            transition: 'all 0.2s', textAlign: 'center',
                        }}
                        onFocus={e => { e.currentTarget.style.borderColor = 'rgba(0,170,255,0.6)'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(0,170,255,0.1)' }}
                        onBlur={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
                    />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    {/* Project selector */}
                    <select
                        value={selectedProjectId || ''}
                        onChange={e => setSelectedProjectId(e.target.value || null)}
                        disabled={!!documentId}
                        style={{
                            background: 'var(--glass)', border: '1px solid var(--border)',
                            borderRadius: '6px', padding: '0.35rem 0.5rem',
                            color: 'var(--foreground)', fontSize: '0.8rem', outline: 'none',
                            cursor: documentId ? 'not-allowed' : 'pointer',
                            opacity: documentId ? 0.6 : 1,
                        }}
                    >
                        {projectsLoading ? (
                            <option value="">Loading...</option>
                        ) : projects.length === 0 ? (
                            <option value="">No projects</option>
                        ) : (
                            projects.map(p => (
                                <option key={p.id} value={p.id}>{p.title}</option>
                            ))
                        )}
                    </select>

                    {/* Status indicator */}
                    <div style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        {saveStatus === 'saving' && <><span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ffb300' }} /> <span style={{ color: 'var(--text-muted)' }}>{saveMessage}</span></>}
                        {saveStatus === 'saved' && <><span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)' }} /> <span style={{ color: 'var(--success)' }}>{saveMessage}</span></>}
                        {saveStatus === 'error' && <><span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--error)' }} /> <span style={{ color: 'var(--error)' }}>{saveMessage}</span></>}
                    </div>

                    {/* Save to DB button */}
                    <button onClick={handleSave} disabled={saving || !wasmReady || !selectedProjectId}
                        style={{
                            padding: '8px 16px', background: saving || !selectedProjectId ? 'rgba(0,170,255,0.3)' : 'linear-gradient(135deg, #0066cc 0%, #00aaff 100%)',
                            color: '#ffffff', border: 'none', borderRadius: '8px',
                            fontWeight: 600, fontSize: '0.85rem',
                            cursor: saving || !selectedProjectId ? 'not-allowed' : 'pointer',
                            transition: 'all 0.2s', opacity: wasmReady && selectedProjectId ? 1 : 0.6,
                        }}
                        onMouseEnter={e => { if (!saving) { e.currentTarget.style.boxShadow = '0 0 20px rgba(0,170,255,0.4), 0 4px 12px rgba(0,100,200,0.3)'; e.currentTarget.style.transform = 'translateY(-1px)' } }}
                        onMouseLeave={e => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.transform = 'translateY(0)' }}
                    >{saving ? 'Saving...' : 'Save'}</button>
                </div>
            </header>

            {/* ========== SPECIAL CHARACTER BAR ========== */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0 1rem', height: '40px',
                background: '#060f1e',
                borderBottom: '1px solid rgba(0,170,255,0.12)',
                zIndex: 10, position: 'relative', overflowX: 'auto',
            }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.12em', marginRight: '0.5rem', whiteSpace: 'nowrap' }}>Symbols ▸</span>
                {SPECIAL_CHARS.map((sc) => (
                    <button key={sc.char} title={sc.title} onClick={() => insertSpecialChar(sc.char)} disabled={!wasmReady}
                        style={{
                            width: '28px', height: '28px',
                            background: 'rgba(0,170,255,0.08)',
                            border: '1px solid rgba(0,170,255,0.25)', borderRadius: '5px',
                            color: 'var(--primary)', fontSize: '1rem',
                            fontFamily: 'monospace',
                            cursor: wasmReady ? 'pointer' : 'not-allowed',
                            transition: 'all 0.2s', opacity: wasmReady ? 1 : 0.4,
                            display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(0,170,255,0.2)'; e.currentTarget.style.boxShadow = '0 0 8px rgba(0,170,255,0.3)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(0,170,255,0.08)'; e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.transform = 'translateY(0)' }}
                    >{sc.label}</button>
                ))}
            </div>

            {/* ========== EDITOR AREA ========== */}
            <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative', zIndex: 1 }}>

                {/* Line Gutter */}
                <div style={{
                    width: '52px', background: 'rgba(0,0,0,0.3)',
                    borderRight: '1px solid rgba(0,170,255,0.1)',
                    display: 'flex', flexDirection: 'column',
                    paddingTop: '16px', userSelect: 'none'
                }}>
                    {lines.map((_, i) => (
                        <div key={i} style={{
                            fontSize: '0.85rem', color: i === currentLineIdx ? 'var(--primary)' : 'var(--text-muted)',
                            textAlign: 'right', padding: '0 12px', lineHeight: '1.7',
                            fontFamily: 'monospace'
                        }}>{i + 1}</div>
                    ))}
                </div>

                {!wasmReady ? (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                        <div style={{
                            width: '40px', height: '40px',
                            border: '3px solid rgba(0,170,255,0.3)', borderTopColor: 'var(--primary)',
                            borderRadius: '50%', animation: 'spin 1s linear infinite'
                        }} />
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Initializing WASM Engine...</p>
                    </div>
                ) : wasmError ? (
                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <div style={{ background: 'rgba(255, 64, 96, 0.08)', border: '1px solid rgba(255, 64, 96, 0.25)', padding: '2rem', borderRadius: '12px', textAlign: 'center' }}>
                            <div style={{ fontSize: '2rem', color: 'var(--error)', marginBottom: '1rem' }}>⚠</div>
                            <p>{wasmError}</p>
                        </div>
                    </div>
                ) : (
                    <div ref={editorAreaRef} tabIndex={0} onKeyDown={handleKeyDown}
                        onClick={() => editorAreaRef.current?.focus()}
                        style={{
                            flex: 1, background: 'transparent',
                            outline: 'none', cursor: 'text', padding: '16px 20px',
                            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                            fontSize: '14px', lineHeight: '1.7', color: 'var(--foreground)',
                            whiteSpace: 'pre-wrap', wordBreak: 'break-all', overflowY: 'auto',
                        }}
                    >
                        {editorContent.length === 0 && cursorPos === 0 ? (
                            <>
                                <span style={{ display: 'inline', borderLeft: cursorVisible ? '2px solid var(--primary)' : '2px solid transparent' }} />
                                <span style={{ color: 'rgba(255,255,255,0.1)' }}>Write system description...</span>
                            </>
                        ) : renderEditorContent()}
                    </div>
                )}
            </div>

            {/* ========== STATUS BAR ========== */}
            <footer style={{
                height: '28px', background: '#000c1e',
                display: 'flex', alignItems: 'center', gap: '1.5rem',
                padding: '0 1rem', borderTop: '1px solid rgba(0,170,255,0.15)',
                fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'monospace', zIndex: 10,
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span style={{ color: wasmReady ? 'var(--primary)' : '#ff9500' }}>●</span>
                    {wasmReady ? 'CONNECTED' : 'STANDBY'}
                </div>
                <div>Ln {currentLineIdx + 1}, Col {(() => { const lines = editorContent.slice(0, cursorPos).split('\n'); return lines[lines.length - 1].length + 1 })()}</div>
                <div>{editorContent.length} chars</div>
                <div>UTF-8</div>
                <div style={{ marginLeft: 'auto' }}>E-SIM ENGINE V1.0 (WASM)</div>
            </footer>

            <style jsx global>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    )
}
