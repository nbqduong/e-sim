'use client'

import React, { useEffect, useRef, useState, useCallback } from 'react'

export default function TestPage() {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const [editorText, setEditorText] = useState('// Start typing your code here...\n')
    const [syncStatus, setSyncStatus] = useState<'idle' | 'pending' | 'synced'>('idle')
    const [wasmReady, setWasmReady] = useState(false)
    const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const syncingToWasmRef = useRef(false) // guard: prevents echo loop
    const lastVersionRef = useRef(0)

    // Push content from JS textarea to WASM
    const pushToWasm = useCallback((text: string) => {
        const M = (window as any).Module
        if (!M || !M.ccall) return
        syncingToWasmRef.current = true
        M.ccall('editor_set_content', null, ['string'], [text])
        syncingToWasmRef.current = false
        setSyncStatus('synced')
        setTimeout(() => setSyncStatus('idle'), 1500)
    }, [])

    // Handle JS textarea changes with 1s debounce
    const handleTextChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newText = e.target.value
        setEditorText(newText)
        setSyncStatus('pending')

        if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
        debounceTimerRef.current = setTimeout(() => {
            pushToWasm(newText)
        }, 1000)
    }, [pushToWasm])

    useEffect(() => {
        if (typeof window !== 'undefined' && canvasRef.current) {
            // Register WASM→JS callback before Module loads
            ;(window as any).onWasmContentChanged = (content: string, version: number) => {
                // Skip if this change originated from JS
                if (syncingToWasmRef.current) return
                if (version <= lastVersionRef.current) return
                lastVersionRef.current = version
                setEditorText(content)
                setSyncStatus('synced')
                setTimeout(() => setSyncStatus('idle'), 1500)
            }

            // Setup Emscripten Module parameters
            ;(window as any).Module = {
                canvas: canvasRef.current,
                locateFile: function (path: string) {
                    if (path.endsWith('.wasm')) return '/' + path
                    return path
                },
                print: (...args: any[]) => console.log('WASM:', ...args),
                printErr: (...args: any[]) => console.error('WASM ERROR:', ...args),
                onRuntimeInitialized: () => {
                    console.log('WebAssembly runtime initialized successfully.')
                    setWasmReady(true)

                    // Read initial content from WASM
                    const M = (window as any).Module
                    if (M && M.ccall) {
                        const ptr = M.ccall('editor_get_content', 'string', [], [])
                        if (ptr) setEditorText(ptr)
                    }
                }
            }

            // Dynamically load the cpp-web.js script
            const script = document.createElement('script')
            script.src = '/cpp-web.js'
            script.async = true
            document.body.appendChild(script)

            return () => {
                if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current)
                if (script.parentNode) script.parentNode.removeChild(script)
                delete (window as any).Module
                delete (window as any).onWasmContentChanged
            }
        }
    }, [])

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            background: '#000000',
            color: '#ffffff',
            fontFamily: 'system-ui, -apple-system, sans-serif'
        }}>
            {/* Header */}
            <div style={{
                padding: '1rem 2rem',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                zIndex: 10
            }}>
                <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>
                    C++ Simulation Canvas
                </h1>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{
                        fontSize: '0.8rem',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        background: syncStatus === 'synced'
                            ? 'rgba(0, 255, 157, 0.15)'
                            : syncStatus === 'pending'
                                ? 'rgba(255, 170, 0, 0.15)'
                                : 'rgba(255,255,255,0.05)',
                        color: syncStatus === 'synced'
                            ? '#00ff9d'
                            : syncStatus === 'pending'
                                ? '#ffaa00'
                                : '#888',
                        border: '1px solid',
                        borderColor: syncStatus === 'synced'
                            ? 'rgba(0,255,157,0.3)'
                            : syncStatus === 'pending'
                                ? 'rgba(255,170,0,0.3)'
                                : 'rgba(255,255,255,0.1)',
                        transition: 'all 0.3s ease',
                    }}>
                        {syncStatus === 'synced' ? '✓ Synced' : syncStatus === 'pending' ? '⏳ Pending...' : (wasmReady ? '● Connected' : '○ Loading...')}
                    </span>
                    <button
                        onClick={() => window.location.href = '/'}
                        style={{
                            padding: '0.5rem 1.5rem',
                            background: 'linear-gradient(135deg, #00ff9d 0%, #00b8ff 100%)',
                            color: '#000000',
                            border: 'none',
                            borderRadius: '8px',
                            fontWeight: '600',
                            cursor: 'pointer'
                        }}
                    >
                        Dashboard
                    </button>
                </div>
            </div>

            {/* Main content: Canvas + Text Editor side by side */}
            <div style={{
                flex: 1,
                display: 'flex',
                overflow: 'hidden',
            }}>
                {/* WASM Canvas */}
                <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
                    <canvas
                        ref={canvasRef}
                        id="canvas"
                        onContextMenu={(e) => e.preventDefault()}
                        tabIndex={-1}
                        style={{
                            width: '100%',
                            height: '100%',
                            border: 'none',
                            display: 'block',
                            outline: 'none'
                        }}
                    />
                </div>

                {/* JS Text Editor panel */}
                <div style={{
                    width: '400px',
                    borderLeft: '1px solid rgba(255,255,255,0.1)',
                    display: 'flex',
                    flexDirection: 'column',
                    background: '#0a0a0a',
                }}>
                    <div style={{
                        padding: '0.75rem 1rem',
                        borderBottom: '1px solid rgba(255,255,255,0.1)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                    }}>
                        <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ccc' }}>
                            JS Text Editor
                        </span>
                        <span style={{ fontSize: '0.7rem', color: '#666' }}>
                            {editorText.split('\n').length} lines | {editorText.length} chars
                        </span>
                    </div>
                    <textarea
                        value={editorText}
                        onChange={handleTextChange}
                        spellCheck={false}
                        style={{
                            flex: 1,
                            width: '100%',
                            background: '#111',
                            color: '#e0e0e0',
                            border: 'none',
                            outline: 'none',
                            padding: '1rem',
                            fontFamily: '"Fira Code", "Cascadia Code", "JetBrains Mono", monospace',
                            fontSize: '0.9rem',
                            lineHeight: '1.6',
                            resize: 'none',
                            tabSize: 4,
                        }}
                    />
                </div>
            </div>
        </div>
    )
}
