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
  Database
} from 'lucide-react';
import { marked } from 'marked';
import { SlotText } from 'slot-text/react';
import 'slot-text/style.css';
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
  
  // UI states
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  
  const fileInputRef = useRef(null);

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
  const handleDownload = () => {
    if (!jobId) return;
    window.location.href = `${API_BASE_URL}/api/jobs/${jobId}/download`;
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
      <div className="sidebar" style={{ display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '24px', borderBottom: '1px solid var(--outline-variant)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers style={{ color: 'var(--primary)', width: '24px', height: '24px' }} />
              <h2 style={{ fontSize: '20px', fontWeight: '700', color: 'var(--on-surface)' }}><SlotText text="CodeAtlas" /></h2>
            </div>
            <button 
              className="secondary" 
              onClick={toggleTheme} 
              style={{ padding: '6px', borderRadius: 'var(--rounded-md)', display: 'inline-flex' }}
            >
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
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
                style={{ justifyContent: 'center' }}
              >
                <GitBranch size={16} />
                <SlotText text={loading ? "Analyzing..." : "Analyze Link"} />
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
              <SlotText text={loading ? "Uploading..." : "Choose ZIP file"} />
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
                      transition: 'var(--transition-smooth)'
                    }}
                  >
                    <div style={{ fontSize: '13px', fontWeight: '600', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {job.name}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--outline)' }}>
                      {job.source_type === 'github' ? <GitBranch size={10} /> : <Upload size={10} />}
                      <span>{new Date(job.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Workspace Panel */}
      <div className="main-content">
        {/* Navigation & Status Header */}
        <div style={{ 
          padding: '16px 24px', 
          borderBottom: '1px solid var(--outline-variant)', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          backgroundColor: 'var(--surface-container-lowest)' 
        }}>
          {jobStatus === 'done' ? (
            <div style={{ display: 'flex', gap: '16px' }}>
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
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Terminal size={16} style={{ color: 'var(--outline)' }} />
              <span style={{ fontSize: '14px', fontWeight: '600', color: 'var(--outline)' }}>Workspace Console</span>
            </div>
          )}

          {jobStatus === 'done' && (
            <button className="primary" onClick={handleDownload}>
              <Download size={16} />
              Download ZIP
            </button>
          )}
        </div>

        {/* Content Box */}
        <div style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
          {errorMsg && (
            <div style={{ 
              display: 'flex', 
              alignItems: 'flex-start', 
              gap: '12px', 
              padding: '16px', 
              backgroundColor: 'rgba(255, 179, 175, 0.1)', 
              border: '1px solid var(--error)', 
              borderRadius: 'var(--rounded-md)',
              marginBottom: '20px'
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
            <div style={{ maxWidth: '800px', margin: '0 auto', textAlign: 'center', display: 'flex', flexDirection: 'column', gap: '30px' }}>
              <div style={{ margin: '40px 0 20px 0' }}>
                <Layers style={{ color: 'var(--primary)', width: '64px', height: '64px', margin: '0 auto 20px auto' }} />
                <h1 style={{ fontSize: '40px', fontWeight: '800', marginBottom: '12px', color: 'var(--on-surface)' }}>
                  <SlotText text="Interactive Codebase Visualizer" />
                </h1>
                <p style={{ fontSize: '18px', color: 'var(--on-surface-variant)' }}>
                  Upload a ZIP or submit a public GitHub repository. Get comprehensive, rule-based README and DEVELOPER documentation with zero external LLM calls.
                </p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', textAlign: 'left' }}>
                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Code style={{ color: 'var(--primary)' }} />
                    <h3 style={{ fontSize: '16px', fontWeight: '700' }}>Static AST Analysis</h3>
                  </div>
                  <p style={{ fontSize: '13px' }}>
                    Extracts modules, classes, decorators, imports, methods, parameters, and function calls from Python code using python standard ast parsing.
                  </p>
                </div>

                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Layers style={{ color: 'var(--primary)' }} />
                    <h3 style={{ fontSize: '16px', fontWeight: '700' }}>Architecture Mapping</h3>
                  </div>
                  <p style={{ fontSize: '13px' }}>
                    Resolves relative imports and builds cross-file dependency maps dynamically displayed via standard GitHub-compatible Mermaid diagrams.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Loader/Progress states */}
          {(jobStatus === 'pending' || jobStatus === 'running') && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: '16px' }}>
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
            <div style={{ maxWidth: '900px', margin: '0 auto' }}>
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
            </div>
          )}
        </div>
      </div>

      {/* Inspector / Project Details Sidebar */}
      {jobStatus === 'done' && jobDetails && (
        <div style={{ 
          width: '320px', 
          backgroundColor: 'var(--surface-container-lowest)', 
          borderLeft: '1px solid var(--outline-variant)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '24px',
          overflowY: 'auto'
        }}>
          <div>
            <span className="label-caps">Project Details</span>
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginTop: '6px' }}>
              <SlotText text={jobDetails.project_name || 'Codebase'} />
            </h3>
          </div>

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
    </div>
  );
}

export default App;
