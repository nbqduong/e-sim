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
    const [deleting, setDeleting] = useState<string | null>(null);

    const handleDelete = async (docId: string, docTitle: string) => {
        if (!confirm(`Delete "${docTitle}"? This will permanently remove it from Google Drive.`)) return;
        setDeleting(docId);
        try {
            const res = await fetch(`http://localhost:8000/api/documents/${docId}`, {
                method: 'DELETE',
                credentials: 'include',
            });
            if (!res.ok && res.status !== 204) {
                throw new Error('Failed to delete document');
            }
            setDocuments(prev => prev.filter(d => d.id !== docId));
        } catch (err: any) {
            alert(`Delete failed: ${err.message}`);
        } finally {
            setDeleting(null);
        }
    };

    useEffect(() => {
        const fetchDocuments = async () => {
            try {
                const response = await fetch('http://localhost:8000/api/documents/', {
                    method: 'GET',
                    credentials: 'include',
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
                setDocuments(data.documents || []);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchDocuments();
    }, []);

    return (
        <div className="oscilloscope-grid" style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            color: 'var(--foreground)',
            fontFamily: 'var(--font-inter), system-ui, sans-serif',
            padding: '4rem 2rem',
        }}>
            {/* Background glowing effect */}
            <div style={{
                position: 'fixed', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                width: '600px', height: '600px',
                background: 'var(--primary-glow)',
                filter: 'blur(150px)', borderRadius: '50%',
                zIndex: 0, pointerEvents: 'none',
            }} />

            <main style={{ zIndex: 1, width: '100%', maxWidth: '1200px', animation: 'fadeIn 0.8s ease-out' }}>
                <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
                    <h1 className="gradient-text" style={{
                        fontSize: '3.5rem', fontWeight: '800', letterSpacing: '-0.02em', marginBottom: '1rem',
                    }}>
                        All projects
                    </h1>
                    <p style={{
                        fontSize: '1.2rem', color: 'var(--text-muted)', maxWidth: '500px', margin: '0 auto',
                    }}>
                        View and manage all your project sync with google drive.
                    </p>
                </header>

                <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: '2rem' }}>
                    <button onClick={() => window.location.href = '/documents/create'}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.6rem',
                            padding: '0.75rem 1.75rem',
                            background: 'linear-gradient(135deg, #0066cc 0%, #00aaff 100%)',
                            color: '#ffffff', border: 'none', borderRadius: '10px',
                            fontWeight: '600', fontSize: '0.95rem',
                            cursor: 'pointer', transition: 'all 0.25s ease',
                            boxShadow: '0 4px 15px rgba(0, 170, 255, 0.2)',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 170, 255, 0.4)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = '0 4px 15px rgba(0, 170, 255, 0.2)';
                        }}
                    >
                        <span style={{ fontSize: '1.3rem' }}>+</span> New Document
                    </button>
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', margin: '4rem 0' }}>
                        <div style={{
                            width: '40px', height: '40px',
                            border: '3px solid var(--primary-dim)', borderTop: '3px solid var(--primary)',
                            borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 1.5rem'
                        }} />
                        <p style={{ color: 'var(--text-muted)' }}>Loading documents...</p>
                    </div>
                ) : error ? (
                    <div style={{
                        background: 'rgba(255, 64, 96, 0.08)', border: '1px solid rgba(255, 64, 96, 0.25)',
                        padding: '2rem', borderRadius: '16px', textAlign: 'center', maxWidth: '500px', margin: '0 auto'
                    }}>
                        <h3 style={{ color: 'var(--error)', fontSize: '1.2rem', marginBottom: '0.5rem' }}>Error</h3>
                        <p style={{ color: 'var(--foreground)' }}>{error}</p>
                        {error.includes('authorized') && (
                            <button onClick={() => window.location.href = 'http://localhost:8000/auth/google/login'}
                                style={{
                                    marginTop: '1.5rem', padding: '0.75rem 2rem',
                                    background: 'var(--primary)', color: '#000', borderRadius: '8px', fontWeight: '600',
                                }}
                            >Login with Google</button>
                        )}
                    </div>
                ) : documents.length === 0 ? (
                    <div style={{
                        textAlign: 'center', color: 'var(--text-muted)', padding: '4rem',
                        background: 'var(--glass)', borderRadius: '24px', border: '1px dashed var(--border)'
                    }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📄</div>
                        <h3 style={{ color: 'white', marginBottom: '0.5rem' }}>No projects found</h3>
                        <p>There are no files in your E-Sim folder yet.</p>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
                        {documents.map((doc) => (
                            <div key={doc.id} style={{
                                background: 'var(--secondary)', border: '1px solid var(--border)',
                                borderRadius: '16px', padding: '1.5rem', transition: 'all 0.3s ease',
                                cursor: 'pointer', display: 'flex', flexDirection: 'column', height: '210px',
                                position: 'relative', overflow: 'hidden'
                            }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.transform = 'translateY(-5px)';
                                    e.currentTarget.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.5), 0 0 15px rgba(0, 170, 255, 0.1)';
                                    e.currentTarget.style.borderColor = 'rgba(0, 170, 255, 0.4)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.transform = 'translateY(0)';
                                    e.currentTarget.style.boxShadow = 'none';
                                    e.currentTarget.style.borderColor = 'var(--border)';
                                }}
                                onClick={() => {
                                    window.location.href = `/documents/modify?id=${doc.id}&title=${encodeURIComponent(doc.title || 'Untitled')}`;
                                }}
                            >
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
                                        <div style={{
                                            width: '42px', height: '42px', borderRadius: '10px',
                                            background: 'var(--primary-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            color: 'var(--primary)', fontSize: '1.3rem', border: '1px solid var(--border)'
                                        }}>⚡</div>
                                        <span style={{
                                            fontSize: '0.7rem', padding: '4px 8px', borderRadius: '4px',
                                            background: 'rgba(0,170,255,0.08)', color: 'var(--primary)',
                                            fontWeight: 600, border: '1px solid var(--border)'
                                        }}>
                                            {doc.drive_file_id ? 'GDrive Sync' : 'Local'}
                                        </span>
                                    </div>
                                    <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.15rem', fontWeight: '700', color: 'var(--foreground)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {doc.title || 'Untitled Project'}
                                    </h3>
                                    <p style={{ margin: 0, fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                                        MODIFIED: {new Date(doc.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }).toUpperCase()}
                                    </p>
                                </div>

                                <div style={{
                                    marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border)',
                                    display: 'flex', alignItems: 'center', color: 'var(--primary)',
                                    fontSize: '0.85rem', fontWeight: '600', letterSpacing: '0.05em'
                                }}>
                                    OPEN PROJECT
                                    <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                        <button onClick={(e) => { e.stopPropagation(); handleDelete(doc.id, doc.title || 'Untitled') }}
                                            disabled={deleting === doc.id}
                                            style={{
                                                background: 'rgba(255, 64, 96, 0.1)', border: '1px solid rgba(255, 64, 96, 0.2)',
                                                borderRadius: '6px', padding: '4px 8px', color: 'var(--error)', fontSize: '0.85rem',
                                                transition: 'all 0.2s', opacity: deleting === doc.id ? 0.5 : 1,
                                            }}
                                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255, 64, 96, 0.25)'; e.currentTarget.style.color = '#ff4060' }}
                                            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255, 64, 96, 0.1)'; e.currentTarget.style.color = 'var(--error)' }}
                                        >
                                            {deleting === doc.id ? '...' : '🗑'}
                                        </button>
                                        <span style={{ fontSize: '1.3rem' }}>&rarr;</span>
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>

            <style jsx global>{`
                @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
                @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
            `}</style>
        </div>
    )
}
