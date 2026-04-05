'use client'

import React, { useEffect, useState } from 'react'

const API_BASE = 'http://localhost:8000'

interface Project {
    id: string
    user_id: string
    title: string
    description: string
    created_at: string
    updated_at: string
}

interface ProjectListResponse {
    projects: Project[]
}

export default function DocumentsPage() {
    const [projects, setProjects] = useState<Project[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [deleting, setDeleting] = useState<string | null>(null)

    // Create project form state
    const [showCreateForm, setShowCreateForm] = useState(false)
    const [newTitle, setNewTitle] = useState('')
    const [newDescription, setNewDescription] = useState('')
    const [creating, setCreating] = useState(false)

    const handleDelete = async (projectId: string, projectTitle: string) => {
        if (!confirm(`Delete project "${projectTitle}"? This will permanently remove it and all its documents.`)) return;
        setDeleting(projectId);
        try {
            const res = await fetch(`${API_BASE}/api/projects/${projectId}`, {
                method: 'DELETE',
                credentials: 'include',
            });
            if (!res.ok && res.status !== 204) {
                throw new Error('Failed to delete project');
            }
            setProjects(prev => prev.filter(p => p.id !== projectId));
        } catch (err: any) {
            alert(`Delete failed: ${err.message}`);
        } finally {
            setDeleting(null);
        }
    };

    const handleCreateProject = async () => {
        if (!newTitle.trim()) return
        setCreating(true)
        try {
            const res = await fetch(`${API_BASE}/api/projects/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ title: newTitle.trim(), description: newDescription.trim() }),
            })
            if (!res.ok) throw new Error(await res.text())
            const project: Project = await res.json()
            setProjects(prev => [project, ...prev])
            setNewTitle('')
            setNewDescription('')
            setShowCreateForm(false)
        } catch (err: any) {
            alert(`Create failed: ${err.message}`)
        } finally {
            setCreating(false)
        }
    }

    useEffect(() => {
        const fetchProjects = async () => {
            try {
                const response = await fetch(`${API_BASE}/api/projects/`, {
                    method: 'GET',
                    credentials: 'include',
                });

                if (!response.ok) {
                    if (response.status === 401) {
                        throw new Error('Not authorized. Please log in.');
                    }
                    throw new Error('Failed to fetch projects');
                }

                const data: ProjectListResponse = await response.json();
                setProjects(data.projects || []);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchProjects();
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
                        View and manage your local projects and documents.
                    </p>
                </header>

                <div style={{ display: 'flex', justifyContent: 'flex-start', gap: '1rem', marginBottom: '2rem' }}>
                    <button onClick={() => setShowCreateForm(true)}
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
                        <span style={{ fontSize: '1.3rem' }}>+</span> New Project
                    </button>

                    <button onClick={() => window.location.href = '/documents/create'}
                        style={{
                            display: 'flex', alignItems: 'center', gap: '0.6rem',
                            padding: '0.75rem 1.75rem',
                            background: 'rgba(0,170,255,0.1)',
                            color: 'var(--primary)', border: '1px solid rgba(0,170,255,0.3)', borderRadius: '10px',
                            fontWeight: '600', fontSize: '0.95rem',
                            cursor: 'pointer', transition: 'all 0.25s ease',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.background = 'rgba(0,170,255,0.2)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.background = 'rgba(0,170,255,0.1)';
                        }}
                    >
                        <span style={{ fontSize: '1.3rem' }}>📄</span> New Document
                    </button>
                </div>

                {/* Create Project Form */}
                {showCreateForm && (
                    <div style={{
                        background: 'var(--secondary)', border: '1px solid rgba(0,170,255,0.3)',
                        borderRadius: '16px', padding: '1.5rem', marginBottom: '2rem',
                        boxShadow: '0 4px 20px rgba(0,0,0,0.3), 0 0 15px rgba(0,170,255,0.08)',
                    }}>
                        <h3 style={{ margin: '0 0 1rem', fontSize: '1.1rem', color: 'var(--foreground)' }}>Create New Project</h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                            <input
                                type="text" placeholder="Project title" autoFocus
                                value={newTitle} onChange={e => setNewTitle(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleCreateProject()}
                                style={{
                                    background: 'var(--glass)', border: '1px solid var(--border)',
                                    borderRadius: '8px', padding: '0.6rem 0.75rem',
                                    color: 'var(--foreground)', fontSize: '0.95rem', outline: 'none',
                                    transition: 'border-color 0.2s',
                                }}
                                onFocus={e => e.currentTarget.style.borderColor = 'rgba(0,170,255,0.5)'}
                                onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
                            />
                            <textarea
                                placeholder="Description (optional)" rows={2}
                                value={newDescription} onChange={e => setNewDescription(e.target.value)}
                                style={{
                                    background: 'var(--glass)', border: '1px solid var(--border)',
                                    borderRadius: '8px', padding: '0.6rem 0.75rem',
                                    color: 'var(--foreground)', fontSize: '0.9rem', outline: 'none',
                                    resize: 'vertical', fontFamily: 'inherit',
                                    transition: 'border-color 0.2s',
                                }}
                                onFocus={e => e.currentTarget.style.borderColor = 'rgba(0,170,255,0.5)'}
                                onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
                            />
                            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                                <button onClick={() => { setShowCreateForm(false); setNewTitle(''); setNewDescription('') }}
                                    style={{
                                        padding: '0.5rem 1.25rem', background: 'transparent',
                                        color: 'var(--text-muted)', border: '1px solid var(--border)',
                                        borderRadius: '8px', fontSize: '0.85rem', cursor: 'pointer',
                                    }}
                                >Cancel</button>
                                <button onClick={handleCreateProject} disabled={creating || !newTitle.trim()}
                                    style={{
                                        padding: '0.5rem 1.25rem',
                                        background: !newTitle.trim() ? 'rgba(0,170,255,0.3)' : 'linear-gradient(135deg, #0066cc 0%, #00aaff 100%)',
                                        color: '#fff', border: 'none', borderRadius: '8px',
                                        fontSize: '0.85rem', fontWeight: 600,
                                        cursor: !newTitle.trim() ? 'not-allowed' : 'pointer',
                                    }}
                                >{creating ? 'Creating...' : 'Create'}</button>
                            </div>
                        </div>
                    </div>
                )}

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
                ) : projects.length === 0 ? (
                    <div style={{
                        textAlign: 'center', color: 'var(--text-muted)', padding: '4rem',
                        background: 'var(--glass)', borderRadius: '24px', border: '1px dashed var(--border)'
                    }}>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📁</div>
                        <h3 style={{ color: 'white', marginBottom: '0.5rem' }}>No projects yet</h3>
                        <p>Create your first project to get started.</p>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
                        {projects.map((project) => (
                            <div key={project.id} style={{
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
                                    window.location.href = `/documents/create?projectId=${project.id}`;
                                }}
                            >
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
                                        <div style={{
                                            width: '42px', height: '42px', borderRadius: '10px',
                                            background: 'var(--primary-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            color: 'var(--primary)', fontSize: '1.3rem', border: '1px solid var(--border)'
                                        }}>📁</div>
                                        <span style={{
                                            fontSize: '0.7rem', padding: '4px 8px', borderRadius: '4px',
                                            background: 'rgba(0,170,255,0.08)', color: 'var(--primary)',
                                            fontWeight: 600, border: '1px solid var(--border)'
                                        }}>
                                            Project
                                        </span>
                                    </div>
                                    <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.15rem', fontWeight: '700', color: 'var(--foreground)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                        {project.title || 'Untitled Project'}
                                    </h3>
                                    {project.description && (
                                        <p style={{ margin: '0 0 0.5rem', fontSize: '0.82rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical' as any }}>
                                            {project.description}
                                        </p>
                                    )}
                                    <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                        MODIFIED: {new Date(project.updated_at).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' }).toUpperCase()}
                                    </p>
                                </div>

                                <div style={{
                                    marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border)',
                                    display: 'flex', alignItems: 'center', color: 'var(--primary)',
                                    fontSize: '0.85rem', fontWeight: '600', letterSpacing: '0.05em'
                                }}>
                                    OPEN PROJECT
                                    <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                        <button onClick={(e) => { e.stopPropagation(); handleDelete(project.id, project.title || 'Untitled') }}
                                            disabled={deleting === project.id}
                                            style={{
                                                background: 'rgba(255, 64, 96, 0.1)', border: '1px solid rgba(255, 64, 96, 0.2)',
                                                borderRadius: '6px', padding: '4px 8px', color: 'var(--error)', fontSize: '0.85rem',
                                                transition: 'all 0.2s', opacity: deleting === project.id ? 0.5 : 1,
                                                cursor: 'pointer',
                                            }}
                                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255, 64, 96, 0.25)'; e.currentTarget.style.color = '#ff4060' }}
                                            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255, 64, 96, 0.1)'; e.currentTarget.style.color = 'var(--error)' }}
                                        >
                                            {deleting === project.id ? '...' : '🗑'}
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
