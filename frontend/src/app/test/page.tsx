'use client'

import React, { useEffect, useRef } from 'react'

export default function TestPage() {
    const canvasRef = useRef<HTMLCanvasElement>(null)

    useEffect(() => {
        if (typeof window !== 'undefined' && canvasRef.current) {
            // Setup Emscripten Module parameters expected by cpp-web.js
            ; (window as any).Module = {
                canvas: canvasRef.current,
                locateFile: function (path: string) {
                    if (path.endsWith('.wasm')) return '/' + path;
                    return path;
                },
                print: (...args: any[]) => console.log('WASM:', ...args),
                printErr: (...args: any[]) => console.error('WASM ERROR:', ...args),
                onRuntimeInitialized: () => {
                    console.log('WebAssembly runtime initialized successfully.')
                }
            }

            // Dynamically load the cpp-web.js script
            const script = document.createElement('script')
            script.src = '/cpp-web.js'
            script.async = true
            document.body.appendChild(script)

            return () => {
                // Cleanup if the component unmounts
                if (script.parentNode) {
                    script.parentNode.removeChild(script)
                }
                delete (window as any).Module
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
            {/* Custom Header Navigation */}
            <div style={{
                padding: '1rem 2rem',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                zIndex: 10
            }}>
                <h1 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>C++ Simulation Canvas</h1>
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

            {/* Canvas Container */}
            <div style={{ flex: 1, display: 'flex', position: 'relative', overflow: 'hidden' }}>
                <canvas
                    ref={canvasRef}
                    id="canvas"
                    // Need to capture pointer events correctly for Emscripten SDL apps
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
        </div>
    )
}
