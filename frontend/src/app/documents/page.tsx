'use client'

import React, { useEffect, useState } from 'react'

interface Document {
    id: string;
    user_id: string;
    title: string;
    content: string;
    updated_at: string;
    drive_file_id: string | null;
    drive_file_url: string | null;
}

interface DocumentListResponse {
    documents: Document[];
}

export default function DocumentsPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchDocuments = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/documents/', {
                    method: 'GET',
                    credentials: 'include', // Includes the session_token cookie!
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        throw new Error('Not authorized. Please log in.');
                    }
                    throw new Error('Failed to fetch documents');
                }

                const data: DocumentListResponse = await response.json();
                setDocuments(data.documents);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchDocuments();
    }, []);

    return (
        <div style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            background: 'radial-gradient(circle at center, #1a1a1a 0%, #000000 100%)',
            color: '#ffffff',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            padding: '4rem 2rem',
        }}>
            {/* Background glowing effect */}
            <div style={{
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '600px',
                height: '600px',
                background: 'rgba(0, 255, 157, 0.05)',
                filter: 'blur(150px)',
                borderRadius: '50%',
                zIndex: 0,
                pointerEvents: 'none',
            }}></div>

            <main style={{ zIndex: 1, width: '100%', maxWidth: '1200px', animation: 'fadeIn 0.8s ease-out' }}>
                <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
                    <h1 style={{
                        fontSize: '3.5rem',
                        fontWeight: '800',
                        letterSpacing: '-0.02em',
                        marginBottom: '1rem',
                        background: 'linear-gradient(135deg, #ffffff 0%, #00ff9d 100%)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                    }}>
                        All projects
                    </h1>
                    <p style={{
                        fontSize: '1.2rem',
                        color: 'rgba(255, 255, 255, 0.6)',
                        maxWidth: '500px',
                        margin: '0 auto',
                    }}>
                        View and manage all your project sync with google drive.
                    </p>
                </header>

                {/* Create New Document button */}
                <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '2rem' }}>
                    <button
                        onClick={() => window.location.href = '/documents/create'}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem',
                            padding: '0.75rem 1.75rem',
                            background: '#00ff9d',
                            color: '#000000',
                            border: 'none',
                            borderRadius: '10px',
                            fontWeight: '600',
                            fontSize: '0.95rem',
                            cursor: 'pointer',
                            transition: 'all 0.25s ease',
                            boxShadow: '0 2px 12px rgba(0, 255, 157, 0.15)',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.boxShadow = '0 6px 24px rgba(0, 255, 157, 0.3)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = '0 2px 12px rgba(0, 255, 157, 0.15)';
                        }}
                    >
                        <span style={{ fontSize: '1.2rem', lineHeight: 1 }}>+</span> New Document
                    </button>
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', margin: '4rem 0' }}>
                        <div style={{
                            width: '40px',
                            height: '40px',
                            border: '3px solid rgba(0, 255, 157, 0.3)',
                            borderTop: '3px solid #00ff9d',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite',
                            margin: '0 auto 1.5rem'
                        }}></div>
                        <p style={{ color: 'rgba(255,255,255,0.6)' }}>Loading documents...</p>
                    </div>
                ) : error ? (
                    <div style={{
                        background: 'rgba(255, 59, 48, 0.1)',
                        border: '1px solid rgba(255, 59, 48, 0.2)',
                        padding: '2rem',
                        borderRadius: '16px',
                        textAlign: 'center',
                        maxWidth: '500px',
                        margin: '0 auto'
                    }}>
                        <h3 style={{ color: '#ff3b30', fontSize: '1.2rem', marginBottom: '0.5rem' }}>Error</h3>
                        <p style={{ color: 'rgba(255,255,255,0.8)' }}>{error}</p>
                        {error.includes('authorized') && (
                            <button
                                onClick={() => window.location.href = 'http://localhost:8000/auth/google/login'}
                                style={{
                                    marginTop: '1.5rem',
                                    padding: '0.75rem 2rem',
                                    background: '#00ff9d',
                                    color: '#000000',
                                    border: 'none',
                                    borderRadius: '8px',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                }}
                            >
                                Login with Google
                            </button>
                        )}
                    </div>
                ) : documents.length === 0 ? (
                    <div style={{
                        textAlign: 'center',
                        color: 'rgba(255, 255, 255, 0.4)',
                        padding: '4rem',
                        background: 'rgba(255, 255, 255, 0.02)',
                        borderRadius: '24px',
                        border: '1px dashed rgba(255, 255, 255, 0.1)'
                    }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📄</div>
                        <h3 style={{ color: 'white', marginBottom: '0.5rem' }}>No documents found</h3>
                        <p>There are no files in your _ESimulate folder yet.</p>
                    </div>
                ) : (
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                        gap: '1.5rem'
                    }}>
                        {documents.map((doc) => (
                            <div key={doc.id} style={{
                                background: 'rgba(255, 255, 255, 0.03)',
                                border: '1px solid rgba(255, 255, 255, 0.05)',
                                borderRadius: '16px',
                                padding: '1.5rem',
                                transition: 'all 0.3s ease',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: 'column',
                                height: '200px',
                                position: 'relative',
                                overflow: 'hidden'
                            }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.transform = 'translateY(-5px)';
                                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)';
                                    e.currentTarget.style.border = '1px solid rgba(0, 255, 157, 0.3)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'translateY(0)';
                                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                                    e.currentTarget.style.border = '1px solid rgba(255, 255, 255, 0.05)';
                                }}
                                onClick={() => {
                                    window.location.href = `/documents/modify?id=${doc.id}&title=${encodeURIComponent(doc.title || 'Untitled')}`;
                                }}
                            >
                                {/* Glow hover effect element */}
                                <div className="card-glow" style={{
                                    position: 'absolute',
                                    top: 0, right: 0,
                                    width: '100px', height: '100px',
                                    background: 'radial-gradient(circle, rgba(0,255,157,0.1) 0%, transparent 70%)',
                                    opacity: 0.5,
                                    transition: 'opacity 0.3s ease'
                                }}></div>

                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                                        <div style={{
                                            width: '40px', height: '40px',
                                            borderRadius: '10px',
                                            background: 'rgba(0, 255, 157, 0.1)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            color: '#00ff9d',
                                            fontSize: '1.2rem'
                                        }}>
                                            📝
                                        </div>
                                        <span style={{
                                            fontSize: '0.75rem',
                                            padding: '4px 8px',
                                            borderRadius: '6px',
                                            background: 'rgba(255, 255, 255, 0.1)',
                                            color: 'rgba(255, 255, 255, 0.6)'
                                        }}>
                                            {doc.drive_file_id ? 'Drive Sync' : 'Local'}
                                        </span>
                                    </div>
                                    <h3 style={{
                                        margin: '0 0 0.5rem 0',
                                        fontSize: '1.1rem',
                                        fontWeight: '600',
                                        color: '#ffffff',
                                        whiteSpace: 'nowrap',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis'
                                    }}>
                                        {doc.title || 'Untitled Document'}
                                    </h3>
                                    <p style={{
                                        margin: 0,
                                        fontSize: '0.85rem',
                                        color: 'rgba(255, 255, 255, 0.5)',
                                    }}>
                                        Last modified: {new Date(doc.updated_at).toLocaleDateString([], {
                                            month: 'short', day: 'numeric', year: 'numeric'
                                        })}
                                    </p>
                                </div>

                                <div style={{
                                    marginTop: 'auto',
                                    paddingTop: '1rem',
                                    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    color: '#00ff9d',
                                    fontSize: '0.9rem',
                                    fontWeight: '500'
                                }}>
                                    Edit Document {/* Right Arrow */}
                                    <span style={{ marginLeft: 'auto', fontSize: '1.2rem' }}>&rarr;</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>

            <style jsx global>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    )
}
