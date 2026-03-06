'use client'

import React from 'react'

export default function TestPage() {
    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'radial-gradient(circle at center, #1a1a1a 0%, #000000 100%)',
            color: '#ffffff',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            padding: '2rem',
            textAlign: 'center'
        }}>
            <div style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '300px',
                height: '300px',
                background: 'rgba(0, 255, 157, 0.1)',
                filter: 'blur(100px)',
                borderRadius: '50%',
                zIndex: 0
            }}></div>

            <div style={{ zIndex: 1, animation: 'fadeIn 1s ease-out' }}>
                <h1 className="gradient-text" style={{
                    fontSize: '5rem',
                    fontWeight: '800',
                    letterSpacing: '-0.02em',
                    marginBottom: '1rem',
                    background: 'linear-gradient(135deg, #ffffff 0%, #00ff9d 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    lineHeight: '1.2'
                }}>
                    Test Successful
                </h1>

                <p style={{
                    fontSize: '1.25rem',
                    color: 'rgba(255, 255, 255, 0.6)',
                    maxWidth: '600px',
                    margin: '0 auto 2.5rem',
                    lineHeight: '1.6'
                }}>
                    This is a beautiful test page served by your backend logic.
                    Everything is working exactly as expected.
                </p>

                <div style={{
                    display: 'inline-flex',
                    padding: '1px',
                    background: 'linear-gradient(135deg, rgba(255,255,255,0.2), rgba(0, 255, 157, 0.2))',
                    borderRadius: '12px'
                }}>
                    <button
                        onClick={() => window.location.href = '/'}
                        style={{
                            padding: '0.75rem 2rem',
                            background: '#ffffff',
                            color: '#000000',
                            borderRadius: '11px',
                            fontSize: '1rem',
                            fontWeight: '600',
                            transition: 'transform 0.2s ease',
                            cursor: 'pointer'
                        }}
                        onMouseOver={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
                        onMouseOut={(e) => e.currentTarget.style.transform = 'scale(1)'}
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>

            <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
        </div>
    )
}
