import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  GitBranch,
  Settings,
  FileText,
  Code,
  Layers,
  Download,
  Sun,
  Moon,
  Terminal,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  FolderOpen,
  Hash,
  Database,
  X,
  ChevronLeft,
  ChevronRight,
  Menu,
  MessageSquare
} from 'lucide-react';
import { marked } from 'marked';
import mermaid from 'mermaid';

const customRenderer = new marked.Renderer();
customRenderer.code = (code, lang) => {
  if (typeof code === 'object') {
    lang = code.lang;
    code = code.text;
  }
  if (lang === 'mermaid') {
    return `<div class="mermaid">${code}</div>`;
  }
  return `<pre><code class="language-${lang || ''}">${code}</code></pre>`;
};

// API Base URL - update if backend runs on a different port
const API_BASE_URL = 'http://localhost:8000';


function App() {
  const [theme, setTheme] = useState('dark');
  const [activeTab, setActiveTab] = useState('readme'); // 'readme' | 'devdoc'
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null); // 'pending' | 'running' | 'done' | 'error'
  const [jobDetails, setJobDetails] = useState(null);
  const [readmeContent, setReadmeContent] = useState('');
  const [devdocContent, setDevdocContent] = useState('');

  // Input fields
  const [githubUrl, setGithubUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [recentJobs, setRecentJobs] = useState([]);
  const [downloadModal, setDownloadModal] = useState({
    isOpen: false,
    fileName: '',
    progress: 0,
    status: 'preparing'
  });

  // UI states
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const fileInputRef = useRef(null);

  // Sidebar sizing & collapse states
  const [leftSidebarWidth, setLeftSidebarWidth] = useState(280);
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(false);
  const [rightSidebarWidth, setRightSidebarWidth] = useState(320);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(false);

  const startResizeLeft = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = leftSidebarWidth;

    const doDrag = (dragEvent) => {
      const newWidth = Math.max(200, Math.min(450, startWidth + (dragEvent.clientX - startX)));
      setLeftSidebarWidth(newWidth);
    };

    const stopDrag = () => {
      document.removeEventListener('mousemove', doDrag);
      document.removeEventListener('mouseup', stopDrag);
    };

    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', stopDrag);
  };

  const startResizeRight = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = rightSidebarWidth;

    const doDrag = (dragEvent) => {
      const newWidth = Math.max(240, Math.min(480, startWidth - (dragEvent.clientX - startX)));
      setRightSidebarWidth(newWidth);
    };

    const stopDrag = () => {
      document.removeEventListener('mousemove', doDrag);
      document.removeEventListener('mouseup', stopDrag);
    };

    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', stopDrag);
  };

  // Chat states
  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Explorer states
  const [selectedExplorerFile, setSelectedExplorerFile] = useState(null);

  const handleExplorerFileClick = (path) => {
    const file = jobDetails?.project_model?.files?.find(f => f.path === path);
    if (file) {
      setSelectedExplorerFile(file);
    }
  };

  // Auto-scroll chat history
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  const sendChatMessage = async (question) => {
    if (!question || !jobId) return;

    // Add user message
    const userMsg = { role: 'user', content: question };
    const historyPayload = [...chatHistory, userMsg].map(m => ({ role: m.role, content: m.content }));

    setChatHistory(prev => [...prev, userMsg]);
    setChatLoading(true);
    setChatInput('');

    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, history: historyPayload }),
      });

      if (!response.ok) throw new Error('Failed to fetch chat response');

      // Append assistant message slot to be updated by stream
      setChatHistory(prev => [...prev, { role: 'assistant', content: '', sources: [] }]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep remaining incomplete line

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const data = JSON.parse(line);
            if (data.token !== undefined) {
              setChatHistory(prev => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                  updated[lastIdx] = {
                    ...updated[lastIdx],
                    content: updated[lastIdx].content + data.token
                  };
                }
                return updated;
              });
            } else if (data.sources !== undefined) {
              setChatHistory(prev => {
                const updated = [...prev];
                const lastIdx = updated.length - 1;
                if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                  updated[lastIdx] = {
                    ...updated[lastIdx],
                    sources: data.sources
                  };
                }
                return updated;
              });
            }
          } catch (e) {
            console.error('Failed to parse NDJSON line:', e);
          }
        }
      }
    } catch (err) {
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: 'Failed to communicate with the codebase assistant. Please verify the backend is running.',
        sources: []
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleChatSubmit = (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    sendChatMessage(chatInput);
  };

  // Initialize theme and load recents
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Handle Mermaid rendering when tab, theme, or content changes
  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: theme === 'dark' ? 'dark' : 'default',
      securityLevel: 'loose',
    });

    if (jobStatus === 'done') {
      const timer = setTimeout(() => {
        try {
          const elements = document.querySelectorAll('.mermaid');
          elements.forEach(el => {
            el.removeAttribute('data-processed');
          });
          mermaid.run();
        } catch (err) {
          console.error("Failed to render Mermaid diagrams:", err);
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [activeTab, readmeContent, devdocContent, jobStatus, theme]);

  useEffect(() => {
    const saved = localStorage.getItem('codeatlas_recent_jobs');
    if (saved) {
      setRecentJobs(JSON.parse(saved));
    }
  }, []);

  // Save jobs to recents list
  const saveJobToRecents = (job) => {
    const updated = [job, ...recentJobs.filter(j => j.id !== job.id)].slice(0, 10);
    setRecentJobs(updated);
    localStorage.setItem('codeatlas_recent_jobs', JSON.stringify(updated));
  };

  // Remove a job from recents
  const removeRecentJob = (id, e) => {
    e.stopPropagation();
    const updated = recentJobs.filter(j => j.id !== id);
    setRecentJobs(updated);
    localStorage.setItem('codeatlas_recent_jobs', JSON.stringify(updated));
    if (jobId === id) {
      setJobId(null);
      setJobStatus(null);
      setJobDetails(null);
      setReadmeContent('');
      setDevdocContent('');
    }
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  // Poll job status
  useEffect(() => {
    if (!jobId || jobStatus === 'done' || jobStatus === 'error') return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`);
        if (!response.ok) throw new Error('Job status check failed');

        const data = await response.json();
        setJobStatus(data.status);
        setJobDetails(data);

        if (data.status === 'done') {
          clearInterval(interval);
          fetchGeneratedDocs(jobId);
          saveJobToRecents({
            id: jobId,
            name: data.project_name || data.source_detail,
            source_type: data.source_type,
            created_at: data.created_at
          });
        } else if (data.status === 'error') {
          clearInterval(interval);
          setErrorMsg(data.error_message || 'An error occurred during codebase parsing.');
        }
      } catch (err) {
        clearInterval(interval);
        setJobStatus('error');
        setErrorMsg('Failed to connect to the backend server.');
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [jobId, jobStatus]);

  // Fetch documents once done
  const fetchGeneratedDocs = async (id) => {
    setLoading(true);
    try {
      const readmeRes = await fetch(`${API_BASE_URL}/api/jobs/${id}/readme`);
      const devdocRes = await fetch(`${API_BASE_URL}/api/jobs/${id}/devdoc`);

      if (readmeRes.ok) setReadmeContent(await readmeRes.text());
      if (devdocRes.ok) setDevdocContent(await devdocRes.text());
    } catch (err) {
      console.error('Error fetching generated documents:', err);
    } finally {
      setLoading(false);
    }
  };

  // Submit GitHub Url
  const handleGithubSubmit = async (e) => {
    e.preventDefault();
    if (!githubUrl) return;

    setLoading(true);
    setErrorMsg('');
    setJobId(null);
    setJobStatus(null);
    setJobDetails(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze/github`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: githubUrl }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to submit URL');
      }

      const data = await response.json();
      setJobId(data.job_id);
      setJobStatus('pending');
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Submit Zip file
  const handleZipUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setErrorMsg('');
    setJobId(null);
    setJobStatus(null);
    setJobDetails(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze/zip`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await response.json();
      setJobId(data.job_id);
      setJobStatus('pending');
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Download docs ZIP
  const handleDownload = async () => {
    if (!jobId) return;
    const projName = jobDetails?.project_name || 'project';
    setDownloadModal({
      isOpen: true,
      fileName: `${projName}_docs.zip`,
      progress: 10,
      status: 'preparing'
    });

    setTimeout(() => {
      setDownloadModal(prev => ({ ...prev, progress: 40, status: 'downloading' }));
    }, 400);

    try {
      const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/download`);
      if (!response.ok) throw new Error('Download failed');
      
      setDownloadModal(prev => ({ ...prev, progress: 80 }));
      
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${projName}_docs.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      setDownloadModal({
        isOpen: true,
        fileName: `${projName}_docs.zip`,
        progress: 100,
        status: 'completed'
      });
    } catch (err) {
      setDownloadModal(prev => ({ ...prev, isOpen: false }));
      alert('Failed to download ZIP archive');
    }
  };

  const handleDownloadMarkdown = (content, filename) => {
    if (!content) return;
    setDownloadModal({
      isOpen: true,
      fileName: filename,
      progress: 20,
      status: 'preparing'
    });

    setTimeout(() => {
      setDownloadModal(prev => ({ ...prev, progress: 70, status: 'downloading' }));
      
      setTimeout(() => {
        const blob = new Blob([content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        setDownloadModal({
          isOpen: true,
          fileName: filename,
          progress: 100,
          status: 'completed'
        });
      }, 500);
    }, 300);
  };

  const downloadReadme = () => {
    handleDownloadMarkdown(readmeContent, 'README.md');
  };

  const downloadDevdoc = () => {
    handleDownloadMarkdown(devdocContent, 'DEVELOPER.md');
  };

  // Load a job from the recents list
  const loadRecentJob = (job) => {
    setErrorMsg('');
    setJobId(job.id);
    setJobStatus('done');
    fetchGeneratedDocs(job.id);
    // Retrieve basic status details for inspector
    fetch(`${API_BASE_URL}/api/jobs/${job.id}`)
      .then(res => res.json())
      .then(data => setJobDetails(data))
      .catch(err => console.error(err));
  };

  return (
    <div className="workbench-layout">
      {/* Sidebar Panel */}
      {!leftSidebarCollapsed ? (
        <div
          className="sidebar"
          style={{
            width: `${leftSidebarWidth}px`,
            display: 'flex',
            flexDirection: 'column',
            flexShrink: 0
          }}
        >
          <div style={{ padding: '24px', borderBottom: '1px solid var(--outline-variant)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers style={{ color: 'var(--primary)', width: '24px', height: '24px' }} />
                <h2 style={{ fontSize: '20px', fontWeight: '800', color: 'var(--on-surface)', letterSpacing: '-0.02em' }}>CodeAtlas</h2>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <button
                  className="secondary"
                  onClick={toggleTheme}
                  style={{ padding: '6px', borderRadius: 'var(--rounded-md)', display: 'inline-flex' }}
                  title="Toggle theme"
                >
                  {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                </button>
                <button
                  className="secondary"
                  onClick={() => setLeftSidebarCollapsed(true)}
                  style={{ padding: '6px', borderRadius: 'var(--rounded-md)', display: 'inline-flex' }}
                  title="Collapse sidebar"
                >
                  <ChevronLeft size={16} />
                </button>
              </div>
            </div>
            <span className="label-caps" style={{ marginTop: '12px', display: 'block' }}>STATIC CODE ANALYSIS</span>
          </div>

          <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', flex: 1, overflowY: 'auto' }}>
            {/* GitHub Input */}
            <form onSubmit={handleGithubSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span className="label-caps">GitHub Repository</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <input
                  type="text"
                  placeholder="https://github.com/..."
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  disabled={loading || (jobStatus && jobStatus !== 'done' && jobStatus !== 'error')}
                  style={{ width: '100%' }}
                />
                <button
                  type="submit"
                  className="primary"
                  disabled={loading || !githubUrl || (jobStatus && jobStatus !== 'done' && jobStatus !== 'error')}
                  style={{
                    justifyContent: 'center'
                  }}
                >
                  <GitBranch size={16} />
                  <span>{loading ? "Analyzing..." : "Analyze Link"}</span>
                </button>
              </div>
            </form>

            {/* Divider */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--outline-variant)' }}></div>
              <span className="label-caps" style={{ color: 'var(--outline)' }}>OR</span>
              <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--outline-variant)' }}></div>
            </div>

            {/* ZIP Upload */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span className="label-caps">Upload Code Archive</span>
              <input
                type="file"
                accept=".zip"
                ref={fileInputRef}
                onChange={handleZipUpload}
                style={{ display: 'none' }}
              />
              <button
                className="secondary"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading || (jobStatus && jobStatus !== 'done' && jobStatus !== 'error')}
                style={{ justifyContent: 'center', width: '100%', borderStyle: 'dashed' }}
              >
                <Upload size={16} />
                <span>{loading ? "Uploading..." : "Choose ZIP file"}</span>
              </button>
            </div>

            {/* Recent Jobs */}
            {recentJobs.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <span className="label-caps" style={{ display: 'block', marginBottom: '8px' }}>Recent Analyses</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {recentJobs.map((job) => (
                    <div
                      key={job.id}
                      onClick={() => loadRecentJob(job)}
                      style={{
                        padding: '10px',
                        borderRadius: 'var(--rounded-default)',
                        backgroundColor: 'var(--surface-container-low)',
                        cursor: 'pointer',
                        border: jobId === job.id ? '1px solid var(--primary)' : '1px solid transparent',
                        transition: 'var(--transition-smooth)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '8px'
                      }}
                    >
                      <div style={{ flex: 1, overflow: 'hidden' }}>
                        <div style={{ fontSize: '13px', fontWeight: '600', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                          {job.name}
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--outline)' }}>
                          {job.source_type === 'github' ? <GitBranch size={10} /> : <Upload size={10} />}
                          <span>{new Date(job.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <button
                        onClick={(e) => removeRecentJob(job.id, e)}
                        style={{
                          padding: '4px',
                          background: 'transparent',
                          color: 'var(--outline)',
                          borderRadius: 'var(--rounded-sm)',
                          display: 'inline-flex',
                          border: 'none'
                        }}
                        title="Remove analysis"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}

      {/* Left Resizer Handle */}
      {!leftSidebarCollapsed && (
        <div
          onMouseDown={startResizeLeft}
          style={{
            width: '4px',
            cursor: 'col-resize',
            backgroundColor: 'var(--outline-variant)',
            opacity: 0.3,
            transition: 'opacity 0.2s',
            alignSelf: 'stretch',
            zIndex: 10
          }}
          onMouseEnter={(e) => e.target.style.opacity = '1'}
          onMouseLeave={(e) => e.target.style.opacity = '0.3'}
        />
      )}

      {/* Main Workspace Panel */}
      <div className="main-content">
        {/* Navigation & Status Header */}
        <div className="nav-header">
          {/* Left: Sidebar Toggle and Title */}
          <div className="nav-header-left">
            {leftSidebarCollapsed && (
              <button
                className="secondary"
                onClick={() => setLeftSidebarCollapsed(false)}
                style={{ padding: '8px', display: 'inline-flex' }}
                title="Expand sidebar"
              >
                <Menu size={16} />
              </button>
            )}
            {jobStatus !== 'done' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Terminal size={16} style={{ color: 'var(--outline)' }} />
                <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--outline)' }}>Workspace Console</span>
              </div>
            )}
          </div>

          {/* Center: macOS Style Floating Dock */}
          {jobStatus === 'done' && (
            <div className="nav-tabs">
              <button
                className={activeTab === 'readme' ? 'primary' : 'secondary'}
                onClick={() => setActiveTab('readme')}
              >
                <FileText size={16} />
                README.md
              </button>
              <button
                className={activeTab === 'devdoc' ? 'primary' : 'secondary'}
                onClick={() => setActiveTab('devdoc')}
              >
                <Code size={16} />
                DEVELOPER.md
              </button>
              <button
                className={activeTab === 'chat' ? 'primary' : 'secondary'}
                onClick={() => setActiveTab('chat')}
              >
                <MessageSquare size={16} />
                Chat Assistant
              </button>
              <button
                className={activeTab === 'explorer' ? 'primary' : 'secondary'}
                onClick={() => setActiveTab('explorer')}
              >
                <FolderOpen size={16} />
                File Explorer
              </button>
            </div>
          )}

          {/* Right: Actions */}
          <div className="nav-actions">
            {jobStatus === 'done' && (
              <>
                <button className="secondary" onClick={downloadReadme} title="Download README.md only" style={{ gap: '6px' }}>
                  <Download size={14} />
                  README
                </button>
                <button className="secondary" onClick={downloadDevdoc} title="Download DEVELOPER.md only" style={{ gap: '6px' }}>
                  <Download size={14} />
                  DevDoc
                </button>
                <button className="primary" onClick={handleDownload} title="Download both as a ZIP archive" style={{ gap: '6px' }}>
                  <Download size={14} />
                  ZIP
                </button>
              </>
            )}
            {jobStatus === 'done' && jobDetails && rightSidebarCollapsed && (
              <button
                className="secondary"
                onClick={() => setRightSidebarCollapsed(false)}
                style={{ padding: '8px', display: 'inline-flex' }}
                title="Show details"
              >
                <Settings size={16} />
              </button>
            )}
          </div>
        </div>

        {/* Content Box */}
        <div style={{ 
          flex: 1, 
          padding: '40px', 
          overflowY: 'auto', 
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: !jobStatus ? 'center' : 'stretch'
        }}>
          {jobStatus !== 'done' && <FluidGradient theme={theme} />}
          {errorMsg && (
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px',
              padding: '16px',
              backgroundColor: 'rgba(255, 179, 175, 0.1)',
              border: '1px solid var(--error)',
              borderRadius: 'var(--rounded-md)',
              marginBottom: '20px',
              position: 'relative',
              zIndex: 1
            }}>
              <AlertTriangle style={{ color: 'var(--tertiary)', flexShrink: 0 }} />
              <div>
                <h4 style={{ color: 'var(--on-surface)', fontWeight: '600', fontSize: '14px' }}>Analysis Failed</h4>
                <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)' }}>{errorMsg}</p>
              </div>
            </div>
          )}

          {/* Default Landing Page */}
          {!jobStatus && (
            <div style={{ 
              maxWidth: '850px', 
              margin: 'auto', 
              padding: '48px', 
              borderRadius: 'var(--rounded-xl)', 
              background: theme === 'dark' ? 'rgba(14, 21, 17, 0.55)' : 'rgba(255, 255, 255, 0.65)', 
              backdropFilter: 'blur(24px)', 
              WebkitBackdropFilter: 'blur(24px)', 
              border: '1px solid var(--outline-variant)', 
              boxShadow: theme === 'dark' ? '0 24px 64px rgba(0, 0, 0, 0.4)' : '0 24px 64px rgba(0, 108, 76, 0.05)',
              display: 'flex', 
              flexDirection: 'column', 
              gap: '36px',
              animation: 'fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) both',
              position: 'relative',
              zIndex: 1
            }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ 
                  display: 'inline-flex', 
                  alignItems: 'center', 
                  justifyContent: 'center', 
                  width: '64px', 
                  height: '64px', 
                  borderRadius: 'var(--rounded-full)', 
                  background: 'var(--primary-container)', 
                  color: 'var(--on-primary-container)',
                  marginBottom: '24px',
                  boxShadow: '0 8px 16px rgba(0,0,0,0.1)'
                }}>
                  <Layers size={32} />
                </div>
                <h1 className="landing-title">
                  CodeAtlas Workspace
                </h1>
                <p style={{ fontSize: '15px', color: 'var(--on-surface-variant)', maxWidth: '620px', margin: '0 auto', lineHeight: '1.6' }}>
                  To begin, use the sidebar to clone a public GitHub repository or upload a local project ZIP archive. CodeAtlas will parse the codebase structure, build AST models, and map relative imports dynamically.
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', textAlign: 'left' }}>
                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center', 
                      width: '36px', 
                      height: '36px', 
                      borderRadius: 'var(--rounded-md)', 
                      background: 'var(--surface-container-high)', 
                      color: 'var(--primary)' 
                    }}>
                      <Code size={20} />
                    </div>
                    <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--on-surface)' }}>Static AST Analysis Heuristics</h3>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', lineHeight: '1.6' }}>
                    Extracts modules, classes, decorators, imports, methods, parameters, and function calls from Python and JS/TS codebases using secure, local standard AST parsers.
                  </p>
                </div>

                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '24px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center', 
                      width: '36px', 
                      height: '36px', 
                      borderRadius: 'var(--rounded-md)', 
                      background: 'var(--surface-container-high)', 
                      color: 'var(--primary)' 
                    }}>
                      <Layers size={20} />
                    </div>
                    <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--on-surface)' }}>Visual Dependency Mapping</h3>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', lineHeight: '1.6' }}>
                    Resolves relative imports and builds cross-file dependency maps dynamically displayed via standard GitHub-compatible Mermaid diagrams and file explorer.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Loader/Progress states */}
          {(jobStatus === 'pending' || jobStatus === 'running') && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '16px', position: 'relative', zIndex: 1 }}>
              <RefreshCw className="spin" style={{ color: 'var(--primary)', width: '48px', height: '48px', animation: 'spin 1.5s linear infinite' }} />
              <div style={{ textAlign: 'center' }}>
                <h3 style={{ fontWeight: '600' }}>
                  {jobStatus === 'pending' ? 'Queuing project...' : 'Analyzing Codebase...'}
                </h3>
                <p style={{ fontSize: '13px', color: 'var(--outline)' }}>
                  This may take a moment depending on the size of the repository.
                </p>
              </div>
              <style>{`
                @keyframes spin {
                  from { transform: rotate(0deg); }
                  to { transform: rotate(360deg); }
                }
              `}</style>
            </div>
          )}

          {/* Done rendering tab */}
          {jobStatus === 'done' && (
            <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', position: 'relative', zIndex: 1 }}>
              {activeTab === 'chat' ? (
                <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '12px', paddingBottom: '20px' }}>
                  {chatHistory.length > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <button
                        className="secondary"
                        onClick={() => setChatHistory([])}
                        style={{ padding: '6px 12px', fontSize: '12px' }}
                      >
                        Clear Chat History
                      </button>
                    </div>
                  )}
                  <div style={{
                    flex: 1,
                    backgroundColor: 'var(--surface-container-lowest)',
                    border: '1px solid var(--outline-variant)',
                    borderRadius: 'var(--rounded-lg)',
                    padding: '24px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '16px',
                    overflowY: 'auto',
                    minHeight: '380px'
                  }}>
                    {chatHistory.length === 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '300px', gap: '12px', textAlign: 'center', color: 'var(--outline)' }}>
                        <MessageSquare size={48} style={{ color: 'var(--primary)', opacity: 0.8 }} />
                        <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--on-surface)' }}>Ask Codebase Assistant</h3>
                        <p style={{ fontSize: '13px', maxWidth: '400px' }}>
                          Get instant, rule-based details about the codebase structure, dependencies, APIs, and components without external AI calls.
                        </p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center', marginTop: '12px', maxWidth: '550px' }}>
                          <button className="secondary" onClick={() => sendChatMessage("What dependencies are used?")} style={{ fontSize: '12px', padding: '6px 12px' }}>📦 Dependencies</button>
                          <button className="secondary" onClick={() => sendChatMessage("List all API routes")} style={{ fontSize: '12px', padding: '6px 12px' }}>🔌 API Routes</button>
                          <button className="secondary" onClick={() => sendChatMessage("What technologies are in this stack?")} style={{ fontSize: '12px', padding: '6px 12px' }}>🛠️ Tech Stack</button>
                          <button className="secondary" onClick={() => sendChatMessage("Show files overview")} style={{ fontSize: '12px', padding: '6px 12px' }}>📁 Files Overview</button>
                        </div>
                      </div>
                    ) : (
                      chatHistory.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`chat-bubble ${msg.role}`}
                          style={{
                            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            maxWidth: '85%',
                            backgroundColor: msg.role === 'user' ? 'var(--primary)' : 'var(--surface-container-low)',
                            color: msg.role === 'user' ? 'var(--on-primary)' : 'var(--on-surface)',
                            padding: '12px 18px',
                            borderRadius: 'var(--rounded-md)',
                            border: msg.role === 'user' ? 'none' : '1px solid var(--outline-variant)'
                          }}
                        >
                          <div style={{ fontSize: '11px', fontWeight: '700', opacity: 0.8, marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            {msg.role === 'user' ? 'You' : 'Assistant'}
                          </div>
                          <div
                            className="markdown-body"
                            dangerouslySetInnerHTML={{ __html: marked.parse(msg.content, { renderer: customRenderer }) }}
                            style={{ fontSize: '14px', lineHeight: '1.6' }}
                          />
                          {msg.sources && msg.sources.length > 0 && (
                            <div style={{ marginTop: '8px', borderTop: '1px solid var(--outline-variant)', paddingTop: '6px', fontSize: '11px', color: 'var(--on-surface-variant)' }}>
                              <strong>Sources:</strong> {msg.sources.join(', ')}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                    <div ref={chatEndRef} />
                  </div>

                  <form onSubmit={handleChatSubmit} style={{ display: 'flex', gap: '10px' }}>
                    <input
                      type="text"
                      placeholder="Ask a question about the files, classes, or dependencies..."
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      style={{ flex: 1 }}
                      disabled={chatLoading}
                    />
                    <button type="submit" className="primary" disabled={!chatInput.trim() || chatLoading}>
                      <MessageSquare size={16} />
                      Send
                    </button>
                  </form>
                </div>
              ) : activeTab === 'explorer' ? (
                <div style={{ display: 'flex', gap: '24px', flex: 1, height: '100%', minHeight: '500px', overflow: 'hidden', paddingBottom: '20px' }}>
                  {/* Left: Interactive File Tree */}
                  <div style={{
                    width: '320px',
                    backgroundColor: 'var(--surface-container-lowest)',
                    border: '1px solid var(--outline-variant)',
                    borderRadius: 'var(--rounded-lg)',
                    padding: '20px',
                    overflowY: 'auto',
                    height: '100%'
                  }}>
                    <h3 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '16px', color: 'var(--on-surface)' }}>Repository Tree</h3>
                    <FileTree 
                      files={jobDetails?.project_model?.files || []} 
                      onFileClick={handleExplorerFileClick}
                      selectedPath={selectedExplorerFile?.path}
                    />
                  </div>
                  
                  {/* Right: File Details Inspector */}
                  <div style={{
                    flex: 1,
                    backgroundColor: 'var(--surface-container-lowest)',
                    border: '1px solid var(--outline-variant)',
                    borderRadius: 'var(--rounded-lg)',
                    padding: '24px',
                    overflowY: 'auto',
                    height: '100%'
                  }}>
                    {selectedExplorerFile ? (
                      <FileInspector file={selectedExplorerFile} />
                    ) : (
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--outline)', minHeight: '300px' }}>
                        <FolderOpen style={{ color: 'var(--primary)', opacity: 0.8, marginBottom: '12px' }} />
                        <h4 style={{ color: 'var(--on-surface)', fontWeight: '600' }}>Select a file</h4>
                        <p style={{ fontSize: '13px' }}>Click a file in the repository tree to inspect its structural definitions, classes, functions, and docstrings.</p>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div
                  className="markdown-body"
                  dangerouslySetInnerHTML={{
                    __html: marked.parse(activeTab === 'readme' ? readmeContent : devdocContent, { renderer: customRenderer })
                  }}
                  style={{
                    lineHeight: '1.6',
                    color: 'var(--on-surface)',
                    fontFamily: 'var(--font-body)'
                  }}
                />
              )}
            </div>
          )}
        </div>
      </div>

      {/* Right Resizer Handle */}
      {jobStatus === 'done' && jobDetails && !rightSidebarCollapsed && (
        <div
          onMouseDown={startResizeRight}
          style={{
            width: '4px',
            cursor: 'col-resize',
            backgroundColor: 'var(--outline-variant)',
            opacity: 0.3,
            transition: 'opacity 0.2s',
            alignSelf: 'stretch',
            zIndex: 10
          }}
          onMouseEnter={(e) => e.target.style.opacity = '1'}
          onMouseLeave={(e) => e.target.style.opacity = '0.3'}
        />
      )}

      {/* Inspector / Project Details Sidebar */}
      {jobStatus === 'done' && jobDetails && !rightSidebarCollapsed && (
        <div style={{
          width: `${rightSidebarWidth}px`,
          backgroundColor: 'var(--surface-container-lowest)',
          borderLeft: '1px solid var(--outline-variant)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
          overflowY: 'auto',
          flexShrink: 0
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label-caps">Project Details</span>
            <button
              className="secondary"
              onClick={() => setRightSidebarCollapsed(true)}
              style={{ padding: '4px', border: 'none', display: 'inline-flex' }}
              title="Collapse sidebar"
            >
              <ChevronRight size={16} />
            </button>
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--on-surface)' }}>
            {jobDetails.project_name || 'Codebase'}
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ padding: '12px', borderRadius: 'var(--rounded-default)', backgroundColor: 'var(--surface-container-low)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--outline)', marginBottom: '4px' }}>
                <FolderOpen size={14} />
                <span className="label-caps" style={{ fontSize: '9px' }}>Files</span>
              </div>
              <div style={{ fontSize: '20px', fontWeight: '700' }}>{jobDetails.file_count || 0}</div>
            </div>

            <div style={{ padding: '12px', borderRadius: 'var(--rounded-default)', backgroundColor: 'var(--surface-container-low)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--outline)', marginBottom: '4px' }}>
                <Hash size={14} />
                <span className="label-caps" style={{ fontSize: '9px' }}>Lines</span>
              </div>
              <div style={{ fontSize: '20px', fontWeight: '700' }}>{jobDetails.total_loc || 0}</div>
            </div>
          </div>

          <div>
            <span className="label-caps">Detected Stack</span>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '8px' }}>
              {jobDetails.frameworks && jobDetails.frameworks.length > 0 ? (
                jobDetails.frameworks.map((fw) => (
                  <span
                    key={fw}
                    style={{
                      fontSize: '11px',
                      fontWeight: '600',
                      padding: '4px 10px',
                      borderRadius: 'var(--rounded-full)',
                      backgroundColor: 'var(--primary-container)',
                      color: 'var(--on-primary-container)'
                    }}
                  >
                    {fw}
                  </span>
                ))
              ) : (
                <span style={{ fontSize: '12px', color: 'var(--outline)' }}>No specific framework detected</span>
              )}
            </div>
          </div>

          {jobDetails.dependencies && jobDetails.dependencies.length > 0 && (
            <div>
              <span className="label-caps">Dependencies ({jobDetails.dependencies.length})</span>
              <div style={{
                marginTop: '8px',
                maxHeight: '300px',
                overflowY: 'auto',
                border: '1px solid var(--outline-variant)',
                borderRadius: 'var(--rounded-default)'
              }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                  <thead>
                    <tr style={{ backgroundColor: 'var(--surface-container-low)', textAlign: 'left' }}>
                      <th style={{ padding: '8px', borderBottom: '1px solid var(--outline-variant)' }} className="label-caps">Name</th>
                      <th style={{ padding: '8px', borderBottom: '1px solid var(--outline-variant)' }} className="label-caps">Version</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobDetails.dependencies.map((dep) => (
                      <tr key={dep.name} style={{ borderBottom: '1px solid var(--outline-variant)' }}>
                        <td style={{ padding: '8px', fontWeight: '600' }}>{dep.name}</td>
                        <td style={{ padding: '8px', color: 'var(--outline)' }}>{dep.version || '*'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Download Progress Modal */}
      {downloadModal.isOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          backdropFilter: 'blur(8px)',
          WebkitBackdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          animation: 'fadeIn 0.3s ease'
        }}>
          <div style={{
            width: '420px',
            background: theme === 'dark' ? 'rgba(22, 29, 25, 0.95)' : 'rgba(255, 255, 255, 0.95)',
            border: '1px solid var(--outline-variant)',
            borderRadius: 'var(--rounded-xl)',
            padding: '32px',
            boxShadow: '0 24px 64px rgba(0, 0, 0, 0.3)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '20px',
            textAlign: 'center',
            animation: 'scaleIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)'
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '56px',
              height: '56px',
              borderRadius: 'var(--rounded-full)',
              background: downloadModal.status === 'completed' ? 'rgba(90, 221, 170, 0.15)' : 'var(--primary-container)',
              color: downloadModal.status === 'completed' ? 'var(--primary)' : 'var(--on-primary-container)',
              transition: 'all 0.3s ease'
            }}>
              {downloadModal.status === 'completed' ? (
                <CheckCircle2 size={28} />
              ) : (
                <Download size={28} className={downloadModal.status === 'downloading' ? 'bounce-anim' : ''} />
              )}
            </div>

            <div>
              <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--on-surface)', marginBottom: '6px' }}>
                {downloadModal.status === 'completed' ? 'Download Complete!' : 'Downloading File'}
              </h3>
              <p style={{ fontSize: '13px', color: 'var(--on-surface-variant)', wordBreak: 'break-all' }}>
                {downloadModal.fileName}
              </p>
            </div>

            {/* Progress Bar Container */}
            <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--surface-container-high)', borderRadius: 'var(--rounded-full)', overflow: 'hidden', position: 'relative' }}>
              <div style={{
                width: `${downloadModal.progress}%`,
                height: '100%',
                backgroundColor: 'var(--primary)',
                borderRadius: 'var(--rounded-full)',
                transition: 'width 0.4s ease'
              }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', fontSize: '11px', color: 'var(--outline)' }} className="label-caps">
              <span>{downloadModal.status.toUpperCase()}</span>
              <span>{downloadModal.progress}%</span>
            </div>

            {downloadModal.status === 'completed' && (
              <button
                className="primary"
                onClick={() => setDownloadModal(prev => ({ ...prev, isOpen: false }))}
                style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }}
              >
                Done
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── File Tree Helper Functions & Components ─────────────────────────────────

function buildTreeStructure(files) {
  const tree = {};
  files.forEach(f => {
    const parts = f.path.split('/');
    let current = tree;
    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      if (i === parts.length - 1) {
        current[part] = null;
      } else {
        if (!current[part]) {
          current[part] = {};
        }
        current = current[part];
      }
    }
  });
  return tree;
}

function FileTreeNode({ name, node, path, onFileClick, selectedPath }) {
  const [isOpen, setIsOpen] = useState(true);
  const isDirectory = node !== null;

  if (isDirectory) {
    return (
      <div style={{ marginLeft: '12px', marginTop: '4px' }}>
        <div 
          onClick={() => setIsOpen(!isOpen)}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            padding: '6px 8px', 
            borderRadius: 'var(--rounded-default)',
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: '600',
            color: 'var(--on-surface)',
            userSelect: 'none',
            transition: 'var(--transition-smooth)'
          }}
          className="tree-node"
        >
          <FolderOpen size={14} style={{ color: 'var(--primary)', flexShrink: 0 }} />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
        </div>
        {isOpen && (
          <div style={{ borderLeft: '1px solid var(--outline-variant)', marginLeft: '14px', paddingLeft: '4px' }}>
            {Object.keys(node).map(key => (
              <FileTreeNode 
                key={key} 
                name={key} 
                node={node[key]} 
                path={path ? `${path}/${key}` : key}
                onFileClick={onFileClick}
                selectedPath={selectedPath}
              />
            ))}
          </div>
        )}
      </div>
    );
  } else {
    const isSelected = selectedPath === path;
    return (
      <div style={{ marginLeft: '12px', marginTop: '4px' }}>
        <div 
          onClick={() => onFileClick(path)}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            padding: '6px 8px', 
            borderRadius: 'var(--rounded-default)',
            cursor: 'pointer',
            fontSize: '13px',
            color: isSelected ? 'var(--primary)' : 'var(--on-surface-variant)',
            backgroundColor: isSelected ? 'var(--surface-container-high)' : 'transparent',
            userSelect: 'none',
            transition: 'var(--transition-smooth)'
          }}
          className="tree-node"
        >
          <FileText size={14} style={{ color: isSelected ? 'var(--primary)' : 'var(--outline)', flexShrink: 0 }} />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
        </div>
      </div>
    );
  }
}

function FileTree({ files, onFileClick, selectedPath }) {
  const tree = React.useMemo(() => buildTreeStructure(files), [files]);
  
  return (
    <div style={{ marginLeft: '-12px' }}>
      {Object.keys(tree).map(key => (
        <FileTreeNode 
          key={key} 
          name={key} 
          node={tree[key]} 
          path={key}
          onFileClick={onFileClick}
          selectedPath={selectedPath}
        />
      ))}
    </div>
  );
}

function FileInspector({ file }) {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--outline-variant)', paddingBottom: '16px', marginBottom: '20px' }}>
        <div>
          <h3 style={{ fontSize: '20px', fontWeight: '700', color: 'var(--on-surface)' }}>{file.path.split('/').pop()}</h3>
          <span style={{ fontSize: '12px', color: 'var(--outline)' }}>{file.path}</span>
        </div>
        <span style={{ 
          fontSize: '11px', 
          fontWeight: '600', 
          padding: '4px 10px', 
          borderRadius: 'var(--rounded-full)', 
          backgroundColor: 'var(--surface-container-high)',
          color: 'var(--on-surface)',
          textTransform: 'uppercase'
        }}>
          {file.language} • {file.loc} LOC
        </span>
      </div>

      {file.module_docstring && (
        <div style={{ marginBottom: '24px' }}>
          <h4 className="label-caps" style={{ marginBottom: '8px' }}>Module Documentation</h4>
          <div style={{ padding: '14px', borderRadius: 'var(--rounded-default)', backgroundColor: 'var(--surface-container-low)', fontSize: '13px', fontStyle: 'italic', lineHeight: '1.6' }}>
            {file.module_docstring}
          </div>
        </div>
      )}

      {file.imports && file.imports.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h4 className="label-caps" style={{ marginBottom: '8px' }}>Imports / Selectors</h4>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {file.imports.map((imp, idx) => (
              <span key={idx} style={{ padding: '4px 8px', borderRadius: 'var(--rounded-sm)', backgroundColor: 'var(--surface-container-low)', fontSize: '12px', fontFamily: 'var(--font-code)' }}>
                {imp}
              </span>
            ))}
          </div>
        </div>
      )}

      {file.classes && file.classes.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h4 className="label-caps" style={{ marginBottom: '12px' }}>Classes ({file.classes.length})</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {file.classes.map((cls, idx) => (
              <div key={idx} style={{ border: '1px solid var(--outline-variant)', borderRadius: 'var(--rounded-default)', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span style={{ fontSize: '14px', fontWeight: '700', color: 'var(--on-surface)' }}>class {cls.name}</span>
                  {cls.base_classes && cls.base_classes.length > 0 && (
                    <span style={{ fontSize: '12px', color: 'var(--outline)' }}>({cls.base_classes.join(', ')})</span>
                  )}
                  <span style={{ fontSize: '11px', color: 'var(--outline)', marginLeft: 'auto' }}>Line {cls.line_number}</span>
                </div>
                {cls.docstring && (
                  <p style={{ fontSize: '12px', color: 'var(--on-surface-variant)', fontStyle: 'italic', marginBottom: '12px' }}>
                    {cls.docstring}
                  </p>
                )}
                {cls.methods && cls.methods.length > 0 && (
                  <div>
                    <h5 style={{ fontSize: '11px', fontWeight: '700', color: 'var(--outline)', textTransform: 'uppercase', marginBottom: '6px' }}>Methods</h5>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', paddingLeft: '8px' }}>
                      {cls.methods.map((method, mIdx) => (
                        <div key={mIdx} style={{ fontSize: '13px' }}>
                          <span style={{ fontWeight: '600', color: 'var(--primary)' }}>{method.name}</span>
                          <span style={{ color: 'var(--outline)' }}>({method.params.map(p => p.name).join(', ')})</span>
                          {method.return_type && <span style={{ color: 'var(--primary)' }}> -&gt; {method.return_type}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {file.functions && file.functions.length > 0 && (
        <div>
          <h4 className="label-caps" style={{ marginBottom: '12px' }}>Functions ({file.functions.length})</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {file.functions.map((fn, idx) => (
              <div key={idx} style={{ border: '1px solid var(--outline-variant)', borderRadius: 'var(--rounded-default)', padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <span style={{ fontSize: '14px', fontWeight: '700', color: 'var(--primary)' }}>{fn.name}</span>
                  <span style={{ color: 'var(--outline)', fontSize: '13px' }}>({fn.params.map(p => p.name).join(', ')})</span>
                  {fn.return_type && <span style={{ color: 'var(--primary)', fontSize: '13px' }}> -&gt; {fn.return_type}</span>}
                  <span style={{ fontSize: '11px', color: 'var(--outline)', marginLeft: 'auto' }}>Line {fn.line_number}</span>
                </div>
                {fn.docstring && (
                  <p style={{ fontSize: '12px', color: 'var(--on-surface-variant)', fontStyle: 'italic' }}>
                    {fn.docstring}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Fluid Gradient WebGL Animation Component ────────────────────────────────

function FluidGradient({ theme }) {
  const canvasRef = useRef(null);
  const themeRef = useRef(theme);

  // Keep themeRef updated
  useEffect(() => {
    themeRef.current = theme;
  }, [theme]);

  useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const gl = c.getContext('webgl');
    if (!gl) return;

    const vs = `attribute vec4 p;void main(){gl_Position=p;}`;
    const fs = `
      precision highp float;
      uniform vec2 u_resolution;
      uniform float u_time;
      uniform vec2 u_mouse;
      uniform vec3 u_colors[5];

      vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;}
      vec2 mod289(vec2 x){return x-floor(x*(1./289.))*289.;}
      vec3 permute(vec3 x){return mod289(((x*34.)+1.)*x);}
      float snoise(vec2 v){
          const vec4 C=vec4(.211324865405187,.366025403784439,-.577350269189626,.024390243902439);
          vec2 i=floor(v+dot(v,C.yy));
          vec2 x0=v-i+dot(i,C.xx);
          vec2 i1=(x0.x>x0.y)?vec2(1.,0.):vec2(0.,1.);
          vec4 x12=x0.xyxy+C.xxzz;
          x12.xy-=i1;
          i=mod289(i);
          vec3 pv=permute(permute(i.y+vec3(0.,i1.y,1.))+i.x+vec3(0.,i1.x,1.));
          vec3 m=max(.5-vec3(dot(x0,x0),dot(x12.xy,x12.xy),dot(x12.zw,x12.zw)),0.);
          m=m*m;m=m*m;
          vec3 x=2.*fract(pv*C.www)-1.;
          vec3 h=abs(x)-.5;
          vec3 ox=floor(x+.5);
          vec3 a0=x-ox;
          m*=1.79284291400159-.85373472095314*(a0*a0+h*h);
          vec3 g;
          g.x=a0.x*x0.x+h.x*x0.y;
          g.yz=a0.yz*x12.xz+h.yz*x12.yw;
          return 130.*dot(m,g);
      }

      void main(){
          vec2 st=gl_FragCoord.xy/u_resolution.xy;
          vec2 asp=st; asp.x*=u_resolution.x/u_resolution.y;
          float t=u_time*0.0900;
          
          // Hover interaction: push fluid coordinates away from cursor (deflection)
          vec2 m_asp = u_mouse;
          m_asp.x *= u_resolution.x/u_resolution.y;
          vec2 m_dir = asp - m_asp;
          float m_dist = length(m_dir);
          float m_influence = smoothstep(0.45, 0.0, m_dist);
          vec2 warp_offset = m_dir * m_influence * 0.28;
          
          vec2 uv=st;
          float w1=snoise((asp - warp_offset)*1.6000+vec2(t*.4,t*.3));
          float w2=snoise((asp - warp_offset)*2.1280-vec2(t*.2,t*.5));
          uv.x+=w1*0.3200 - warp_offset.x;
          uv.y+=w2*0.3200 - warp_offset.y;

          vec3 cCyan   = u_colors[0];
          vec3 cYellow = u_colors[1];
          vec3 cOrange = u_colors[2];
          vec3 cPurple = u_colors[3];
          vec3 cBlue   = u_colors[4];
    
          float n1=snoise(uv*1.2+vec2(t,0.))*.5+.5;
          float n2=snoise(uv*1.5-vec2(0.,t*.6))*.5+.5;
          float n3=snoise(uv*1.3+vec2(-t*.5,t*.3))*.5+.5;

          vec3 bg=mix(cCyan,cBlue,clamp(uv.x+n1*.4,0.,1.));
          bg=mix(bg,cYellow,smoothstep(.2,.9,n2*(1.2-uv.x)*uv.y));
          bg=mix(bg,cPurple,smoothstep(.1,.8,n1*uv.x*(1.1-uv.y)));
          bg=mix(bg,cOrange,smoothstep(.3,1.,n3*(1.-uv.y)*uv.x*1.5));
          
          // Subtly lift color near cursor without oversaturating (reduced brightness)
          bg += mix(cCyan, cYellow, sin(t)*0.5+0.5) * m_influence * 0.05;

          float grain=fract(sin(dot(gl_FragCoord.xy+u_time*100.,vec2(12.9898,78.233)))*43758.5453123);
          gl_FragColor=vec4(bg+(grain-.5)*0.0500,1.);
      }
    `;

    function sh(t, src) {
      const s = gl.createShader(t);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    }

    const prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, vs));
    gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, fs));
    gl.linkProgram(prog);

    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([1, -1, -1, -1, 1, 1, -1, 1]), gl.STATIC_DRAW);

    const ap = gl.getAttribLocation(prog, 'p');
    const ur = gl.getUniformLocation(prog, 'u_resolution');
    const ut = gl.getUniformLocation(prog, 'u_time');
    const um = gl.getUniformLocation(prog, 'u_mouse');
    const uc = gl.getUniformLocation(prog, 'u_colors');

    const colorsDark = [
      0.3529, 0.8667, 0.6667,
      0.0549, 0.0824, 0.0667,
      0.8667, 0.8941, 0.8706,
      0.7373, 0.7922, 0.7529,
      0.0863, 0.1137, 0.0980
    ];

    const colorsLight = [
      0.0000, 0.4235, 0.2980,
      0.9569, 0.9686, 0.9608,
      0.0510, 0.0824, 0.0667,
      0.2275, 0.2784, 0.2510,
      0.9412, 0.9608, 0.9490
    ];

    let mx = 0.5, my = 0.5, tx = 0.5, ty = 0.5;

    const handleMouseMove = (e) => {
      const rect = c.getBoundingClientRect();
      tx = (e.clientX - rect.left) / rect.width;
      ty = 1 - (e.clientY - rect.top) / rect.height;
    };

    const handleTouchMove = (e) => {
      if (e.touches.length) {
        const rect = c.getBoundingClientRect();
        const t = e.touches[0];
        tx = (t.clientX - rect.left) / rect.width;
        ty = 1 - (t.clientY - rect.top) / rect.height;
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('touchmove', handleTouchMove, { passive: true });

    const t0 = Date.now();
    let animationFrameId;

    function draw() {
      if (c.width !== c.clientWidth || c.height !== c.clientHeight) {
        c.width = c.clientWidth;
        c.height = c.clientHeight;
      }
      gl.viewport(0, 0, c.width, c.height);
      gl.useProgram(prog);
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.vertexAttribPointer(ap, 2, gl.FLOAT, false, 0, 0);
      gl.enableVertexAttribArray(ap);
      gl.uniform2f(ur, c.width, c.height);
      gl.uniform1f(ut, (Date.now() - t0) / 1000);
      mx += (tx - mx) * 0.08;
      my += (ty - my) * 0.08;
      gl.uniform2f(um, mx, my);

      const activeColors = themeRef.current === 'dark' ? colorsDark : colorsLight;
      gl.uniform3fv(uc, activeColors);

      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      animationFrameId = requestAnimationFrame(draw);
    }

    draw();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('touchmove', handleTouchMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
        opacity: 0.85
      }}
    />
  );
}

export default App;
