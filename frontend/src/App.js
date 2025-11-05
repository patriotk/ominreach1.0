import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { CampaignBuilder } from "./CampaignBuilder";
import { AIAgentStudio } from "./AIAgentStudio";
import { PhantombusterImport } from "./PhantombusterImport";
import "@/App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Axios instance with credentials
const api = axios.create({
  baseURL: API,
  withCredentials: true
});

// Set auth token from cookie or header
api.interceptors.request.use((config) => {
  const sessionToken = localStorage.getItem('session_token');
  if (sessionToken) {
    config.headers.Authorization = `Bearer ${sessionToken}`;
  }
  return config;
});

// Landing Page
const LandingPage = () => {
  const navigate = useNavigate();
  
  const handleLogin = () => {
    const redirectUrl = `${window.location.origin}/dashboard`;
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="landing-page">
      <div className="landing-container">
        <nav className="landing-nav">
          <div className="logo-text">OmniReach AI</div>
          <button onClick={handleLogin} className="nav-login-btn" data-testid="nav-login-btn">
            Sign In
          </button>
        </nav>
        
        <section className="hero-section">
          <div className="hero-content">
            <h1 className="hero-title" data-testid="hero-title">
              AI-Powered Outreach,<br/>Analytics & CRM Sync
            </h1>
            <p className="hero-subtitle" data-testid="hero-subtitle">
              Automate LinkedIn + Email campaigns. Analyze with AI. Sync with Google Sheets.
            </p>
            <div className="hero-cta">
              <button onClick={handleLogin} className="cta-primary" data-testid="cta-get-started">
                Get Started Free
              </button>
            </div>
          </div>
        </section>

        <section className="features-section">
          <h2 className="section-title">Everything You Need</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">📧</div>
              <h3>Multi-Channel Outreach</h3>
              <p>Automated LinkedIn + Email campaigns with smart scheduling</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🧪</div>
              <h3>A/B Testing</h3>
              <p>Test message variants and identify top performers with AI</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🤖</div>
              <h3>AI Analytics</h3>
              <p>GPT-5 powered insights on campaign performance and optimization</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">🔍</div>
              <h3>LinkedIn Research</h3>
              <p>AI-powered persona generation from LinkedIn profiles</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">📊</div>
              <h3>Google Sheets Sync</h3>
              <p>Automatic bi-directional CRM synchronization</p>
            </div>
            <div className="feature-card">
              <div className="feature-icon">👥</div>
              <h3>Team Collaboration</h3>
              <p>Multi-user accounts with roles and shared campaigns</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

// Auth Handler Component
const AuthHandler = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handleAuth = async () => {
      // Check for session_id in URL fragment
      const hash = window.location.hash;
      const sessionIdMatch = hash.match(/session_id=([^&]+)/);
      
      if (sessionIdMatch) {
        const sessionId = sessionIdMatch[1];
        
        try {
          // Exchange session_id for user data
          const response = await api.post('/auth/session-data', {}, {
            headers: { 'X-Session-ID': sessionId }
          });
          
          const { session_token, ...userData } = response.data;
          
          // Store session token
          localStorage.setItem('session_token', session_token);
          localStorage.setItem('user', JSON.stringify(userData));
          
          // Clean URL
          window.history.replaceState(null, '', window.location.pathname);
          
          toast.success('Welcome back!');
          navigate('/dashboard');
        } catch (error) {
          console.error('Auth error:', error);
          toast.error('Authentication failed');
          navigate('/');
        }
      } else {
        // Check existing session
        const sessionToken = localStorage.getItem('session_token');
        if (sessionToken) {
          try {
            await api.get('/auth/me');
            navigate('/dashboard');
          } catch (error) {
            localStorage.removeItem('session_token');
            localStorage.removeItem('user');
            navigate('/');
          }
        } else {
          navigate('/');
        }
      }
      setLoading(false);
    };

    handleAuth();
  }, [navigate]);

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Authenticating...</p>
      </div>
    );
  }

  return null;
};

// Protected Route
const ProtectedRoute = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const checkAuth = async () => {
      const sessionToken = localStorage.getItem('session_token');
      if (!sessionToken) {
        setIsAuthenticated(false);
        return;
      }

      try {
        await api.get('/auth/me');
        setIsAuthenticated(true);
      } catch (error) {
        localStorage.removeItem('session_token');
        localStorage.removeItem('user');
        setIsAuthenticated(false);
      }
    };

    checkAuth();
  }, []);

  if (isAuthenticated === null) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
};

// Dashboard Layout
const DashboardLayout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(null);

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }
  }, []);

  const handleLogout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      console.error('Logout error:', error);
    }
    localStorage.removeItem('session_token');
    localStorage.removeItem('user');
    navigate('/');
  };

  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/campaigns', label: 'Campaigns', icon: '🎯' },
    { path: '/leads', label: 'Leads', icon: '👥' },
    { path: '/messages', label: 'Messages', icon: '💬' },
    { path: '/analytics', label: 'Analytics', icon: '📈' },
    { path: '/research', label: 'Research', icon: '🔍' },
    { path: '/ai-studio', label: 'AI Studio', icon: '🤖' },
    { path: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">OmniReach AI</div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={`sidebar-nav-item ${location.pathname === item.path ? 'active' : ''}`}
              data-testid={`nav-${item.label.toLowerCase()}`}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-profile">
            {user?.picture ? (
              <img src={user.picture} alt={user.name} className="user-avatar" />
            ) : (
              <div className="user-avatar-placeholder">{user?.name?.charAt(0) || 'U'}</div>
            )}
            <div className="user-info">
              <div className="user-name">{user?.name || 'User'}</div>
              <div className="user-role">{user?.role || 'agent'}</div>
            </div>
          </div>
          <button onClick={handleLogout} className="logout-btn" data-testid="logout-btn">
            Logout
          </button>
        </div>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

// Dashboard Home
const Dashboard = () => {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchOverview = async () => {
      try {
        const response = await api.get('/analytics/overview');
        setOverview(response.data);
      } catch (error) {
        toast.error('Failed to load analytics');
      }
      setLoading(false);
    };

    fetchOverview();
  }, []);

  if (loading) {
    return <div className="loading-screen"><div className="loading-spinner"></div></div>;
  }

  return (
    <div className="page-container" data-testid="dashboard-page">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Overview of your outreach performance</p>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Total Campaigns</div>
          <div className="metric-value">{overview?.total_campaigns || 0}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Total Leads</div>
          <div className="metric-value">{overview?.total_leads || 0}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Messages Sent</div>
          <div className="metric-value">{overview?.total_sent || 0}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Calls Booked</div>
          <div className="metric-value">{overview?.calls_booked || 0}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Open Rate</div>
          <div className="metric-value">{overview?.open_rate || 0}%</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Reply Rate</div>
          <div className="metric-value">{overview?.reply_rate || 0}%</div>
        </div>
      </div>
    </div>
  );
};

// Campaigns Page
const CampaignsPage = () => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newCampaign, setNewCampaign] = useState({ 
    name: '', 
    goal_type: 'email',  // Changed default to email only
    target_persona: '' 
  });

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      const response = await api.get('/campaigns');
      setCampaigns(response.data);
    } catch (error) {
      toast.error('Failed to load campaigns');
    }
  };

  const handleCreate = async () => {
    if (!newCampaign.name) {
      toast.error('Campaign name is required');
      return;
    }

    try {
      const response = await api.post('/campaigns', newCampaign);
      toast.success('Campaign created!');
      setShowCreate(false);
      setNewCampaign({ name: '', goal_type: 'email', target_persona: '' });
      
      // Navigate to campaign builder
      navigate(`/campaigns/${response.data.id}/edit`);
    } catch (error) {
      toast.error('Failed to create campaign');
    }
  };

  return (
    <div className="page-container" data-testid="campaigns-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Campaigns</h1>
          <p className="page-subtitle">Manage your outreach campaigns</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary" data-testid="create-campaign-btn">
          + New Campaign
        </button>
      </div>

      {showCreate && (
        <div className="create-form">
          <h3>New Campaign</h3>
          
          <label className="form-label">Campaign Name *</label>
          <input
            type="text"
            placeholder="E.g., CTO Outreach Q1"
            value={newCampaign.name}
            onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
            className="input"
            data-testid="campaign-name-input"
          />

          <label className="form-label">Channel *</label>
          <div className="channel-selector">
            <button
              className={`channel-option ${newCampaign.goal_type === 'email' ? 'active' : ''}`}
              onClick={() => setNewCampaign({ ...newCampaign, goal_type: 'email' })}
              data-testid="channel-email"
            >
              <span className="channel-icon">📧</span>
              <span>Email Campaign</span>
            </button>
            <button
              className={`channel-option ${newCampaign.goal_type === 'linkedin' ? 'active' : ''}`}
              onClick={() => setNewCampaign({ ...newCampaign, goal_type: 'linkedin' })}
              data-testid="channel-linkedin"
            >
              <span className="channel-icon">💼</span>
              <span>LinkedIn Campaign</span>
            </button>
          </div>

          <label className="form-label">Target Persona (Optional)</label>
          <input
            type="text"
            placeholder="E.g., CTOs at B2B SaaS companies"
            value={newCampaign.target_persona}
            onChange={(e) => setNewCampaign({ ...newCampaign, target_persona: e.target.value })}
            className="input"
          />

          <div className="form-actions">
            <button onClick={handleCreate} className="btn-primary" data-testid="submit-campaign-btn">
              Create & Configure
            </button>
            <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      <div className="campaigns-list">
        {campaigns.length === 0 ? (
          <div className="empty-state">
            <p>No campaigns yet. Create your first campaign to get started!</p>
          </div>
        ) : (
          campaigns.map((campaign) => (
            <div 
              key={campaign.id} 
              className="campaign-card" 
              data-testid={`campaign-${campaign.id}`}
              onClick={() => navigate(`/campaigns/${campaign.id}/edit`)}
              style={{ cursor: 'pointer' }}
            >
              <div className="campaign-info">
                <h3>{campaign.name}</h3>
                <p className="campaign-meta">
                  <span className={`status-badge status-${campaign.status}`}>{campaign.status}</span>
                  <span className={`goal-badge goal-${campaign.goal_type}`}>
                    {campaign.goal_type === 'email' ? '📧 Email' : '💼 LinkedIn'}
                  </span>
                  <span>{campaign.lead_ids?.length || 0} leads</span>
                </p>
                <p>Steps: {campaign.message_steps?.length || 0} | Variants: {campaign.message_variants?.length || 0}</p>
                {campaign.metrics && (
                  <div className="campaign-metrics-preview">
                    <small>Sent: {campaign.metrics.messages_sent || 0}</small>
                    <small>Open: {campaign.metrics.open_rate || 0}%</small>
                    <small>Reply: {campaign.metrics.reply_rate || 0}%</small>
                    {campaign.metrics.ai_score && (
                      <small className="ai-score">AI Score: {campaign.metrics.ai_score}/10</small>
                    )}
                  </div>
                )}
              </div>
              <div className="campaign-actions">
                <button 
                  onClick={(e) => { e.stopPropagation(); navigate(`/campaigns/${campaign.id}/edit`); }}
                  className="btn-secondary"
                >
                  Edit
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Leads Page
const LeadsPage = () => {
  const [leads, setLeads] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [showPhantombuster, setShowPhantombuster] = useState(false);
  const [editingLead, setEditingLead] = useState(null);
  const [newLead, setNewLead] = useState({ name: '', email: '', linkedin_url: '', company: '', title: '' });
  const [importText, setImportText] = useState('');

  useEffect(() => {
    fetchLeads();
  }, []);

  const fetchLeads = async () => {
    try {
      const response = await api.get('/leads');
      setLeads(response.data);
    } catch (error) {
      toast.error('Failed to load leads');
    }
  };

  const handleCreate = async () => {
    try {
      await api.post('/leads', newLead);
      toast.success('Lead added!');
      setShowCreate(false);
      setNewLead({ name: '', email: '', linkedin_url: '', company: '', title: '' });
      fetchLeads();
    } catch (error) {
      toast.error('Failed to add lead');
    }
  };

  const handleUpdate = async () => {
    try {
      await api.patch(`/leads/${editingLead.id}`, editingLead);
      toast.success('Lead updated!');
      setEditingLead(null);
      fetchLeads();
    } catch (error) {
      toast.error('Failed to update lead');
    }
  };

  const handleDelete = async (leadId) => {
    if (!window.confirm('Delete this lead?')) return;
    
    try {
      await api.delete(`/leads/${leadId}`);
      toast.success('Lead deleted!');
      setEditingLead(null);
      fetchLeads();
    } catch (error) {
      toast.error('Failed to delete lead');
    }
  };

  const handleImport = async () => {
    try {
      // Parse CSV format: name,email,linkedin_url,company,title
      const lines = importText.trim().split('\n');
      const leads = lines.slice(1).map(line => {
        const [name, email, linkedin_url, company, title] = line.split(',').map(s => s.trim());
        return { name, email, linkedin_url, company, title };
      }).filter(lead => lead.name);

      const response = await api.post('/leads/import', { leads });
      toast.success(`Imported ${response.data.count} leads!`);
      setShowImport(false);
      setImportText('');
      fetchLeads();
    } catch (error) {
      toast.error('Failed to import leads');
    }
  };

  return (
    <div className="page-container" data-testid="leads-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Leads</h1>
          <p className="page-subtitle">Manage your contact list</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button onClick={() => setShowPhantombuster(true)} className="btn-secondary" data-testid="phantombuster-import-btn">
            🤖 Import from Phantombuster
          </button>
          <button onClick={() => setShowImport(true)} className="btn-secondary" data-testid="import-leads-btn">
            📥 Import CSV
          </button>
          <button onClick={() => setShowCreate(true)} className="btn-primary" data-testid="add-lead-btn">
            + Add Lead
          </button>
        </div>
      </div>

      {showPhantombuster && (
        <PhantombusterImport
          onClose={() => setShowPhantombuster(false)}
          onImportComplete={fetchLeads}
        />
      )}

      {showImport && (
        <div className="create-form">
          <h3>Import Contacts (CSV)</h3>
          <p style={{ color: '#a0a0b0', marginBottom: '1rem' }}>
            Paste CSV data with headers: name,email,linkedin_url,company,title
          </p>
          <textarea
            placeholder="name,email,linkedin_url,company,title&#10;John Doe,john@example.com,https://linkedin.com/in/johndoe,Acme Inc,CTO"
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            className="input"
            rows="8"
            data-testid="import-textarea"
          />
          <div className="form-actions">
            <button onClick={handleImport} className="btn-primary" data-testid="submit-import-btn">Import</button>
            <button onClick={() => setShowImport(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {showCreate && (
        <div className="create-form">
          <h3>New Lead</h3>
          <input
            type="text"
            placeholder="Name"
            value={newLead.name}
            onChange={(e) => setNewLead({ ...newLead, name: e.target.value })}
            className="input"
            data-testid="lead-name-input"
          />
          <input
            type="email"
            placeholder="Email"
            value={newLead.email}
            onChange={(e) => setNewLead({ ...newLead, email: e.target.value })}
            className="input"
          />
          <input
            type="text"
            placeholder="LinkedIn URL"
            value={newLead.linkedin_url}
            onChange={(e) => setNewLead({ ...newLead, linkedin_url: e.target.value })}
            className="input"
          />
          <input
            type="text"
            placeholder="Company"
            value={newLead.company}
            onChange={(e) => setNewLead({ ...newLead, company: e.target.value })}
            className="input"
          />
          <input
            type="text"
            placeholder="Title"
            value={newLead.title}
            onChange={(e) => setNewLead({ ...newLead, title: e.target.value })}
            className="input"
          />
          <div className="form-actions">
            <button onClick={handleCreate} className="btn-primary" data-testid="submit-lead-btn">Add Lead</button>
            <button onClick={() => setShowCreate(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {editingLead && (
        <div className="modal-overlay" onClick={() => setEditingLead(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Edit Lead</h3>
            <input
              type="text"
              placeholder="Name"
              value={editingLead.name}
              onChange={(e) => setEditingLead({ ...editingLead, name: e.target.value })}
              className="input"
            />
            <input
              type="email"
              placeholder="Email"
              value={editingLead.email || ''}
              onChange={(e) => setEditingLead({ ...editingLead, email: e.target.value })}
              className="input"
            />
            <input
              type="text"
              placeholder="LinkedIn URL"
              value={editingLead.linkedin_url || ''}
              onChange={(e) => setEditingLead({ ...editingLead, linkedin_url: e.target.value })}
              className="input"
            />
            <input
              type="text"
              placeholder="Company"
              value={editingLead.company || ''}
              onChange={(e) => setEditingLead({ ...editingLead, company: e.target.value })}
              className="input"
            />
            <input
              type="text"
              placeholder="Title"
              value={editingLead.title || ''}
              onChange={(e) => setEditingLead({ ...editingLead, title: e.target.value })}
              className="input"
            />
            <div className="form-actions">
              <button onClick={handleUpdate} className="btn-primary">Save Changes</button>
              <button onClick={() => handleDelete(editingLead.id)} className="btn-danger">Delete</button>
              <button onClick={() => setEditingLead(null)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="leads-table">
        {leads.length === 0 ? (
          <div className="empty-state">
            <p>No leads yet. Add your first lead to get started!</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>LinkedIn</th>
                <th>Company</th>
                <th>Title</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id} data-testid={`lead-${lead.id}`}>
                  <td>{lead.name}</td>
                  <td>{lead.email || '-'}</td>
                  <td>
                    {lead.linkedin_url ? (
                      <a 
                        href={lead.linkedin_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="linkedin-table-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        View Profile
                      </a>
                    ) : '-'}
                  </td>
                  <td>{lead.company || '-'}</td>
                  <td>{lead.title || '-'}</td>
                  <td>
                    {lead.call_booked ? '✅ Booked' : lead.date_contacted ? '📧 Contacted' : '⏳ New'}
                  </td>
                  <td>
                    <button 
                      onClick={() => setEditingLead(lead)}
                      className="btn-edit"
                      data-testid={`edit-lead-${lead.id}`}
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// Analytics Page
const AnalyticsPage = () => {
  const [insights, setInsights] = useState([]);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    fetchInsights();
  }, []);

  const fetchInsights = async () => {
    try {
      const response = await api.get('/analytics/insights');
      setInsights(response.data);
    } catch (error) {
      console.error('Failed to load insights');
    }
  };

  const generateInsights = async () => {
    setGenerating(true);
    try {
      const response = await api.post('/analytics/insights', { time_period: 'week' });
      setInsights(response.data.insights.map(i => ({ ...i, generated_at: new Date().toISOString() })));
      toast.success('Insights generated!');
    } catch (error) {
      toast.error('Failed to generate insights');
    }
    setGenerating(false);
  };

  return (
    <div className="page-container" data-testid="analytics-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">AI Analytics</h1>
          <p className="page-subtitle">AI-powered campaign insights</p>
        </div>
        <button 
          onClick={generateInsights} 
          className="btn-primary" 
          disabled={generating}
          data-testid="generate-insights-btn"
        >
          {generating ? 'Generating...' : '🤖 Generate Insights'}
        </button>
      </div>

      <div className="insights-list">
        {insights.length === 0 ? (
          <div className="empty-state">
            <p>No insights yet. Click "Generate Insights" to get AI-powered recommendations.</p>
          </div>
        ) : (
          insights.map((insight, index) => (
            <div key={index} className="insight-card" data-testid={`insight-${index}`}>
              <div className="insight-type">{insight.type || insight.insight_type}</div>
              <h3>{insight.title}</h3>
              <p>{insight.description}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Research Page
const ResearchPage = () => {
  const [leads, setLeads] = useState([]);
  const [researching, setResearching] = useState(null);

  useEffect(() => {
    fetchLeads();
  }, []);

  const fetchLeads = async () => {
    try {
      const response = await api.get('/leads');
      setLeads(response.data);
    } catch (error) {
      toast.error('Failed to load leads');
    }
  };

  const handleResearch = async (lead) => {
    if (!lead.linkedin_url && !lead.name) {
      toast.error('Lead needs at least a name to research');
      return;
    }

    setResearching(lead.id);
    try {
      const response = await api.post('/research/persona', {
        lead_id: lead.id,
        linkedin_url: lead.linkedin_url || `https://linkedin.com/search?q=${encodeURIComponent(lead.name + ' ' + lead.company)}`
      });
      
      if (response.data.persona) {
        toast.success('Persona generated successfully!');
        fetchLeads();
      } else {
        toast.error(response.data.message || 'Research failed');
      }
    } catch (error) {
      toast.error('Research failed - check your Perplexity API key in Settings');
    }
    setResearching(null);
  };

  return (
    <div className="page-container" data-testid="research-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">LinkedIn Research</h1>
          <p className="page-subtitle">AI-powered persona generation using Perplexity</p>
        </div>
      </div>

      <div className="research-info-banner">
        <h4>How it works:</h4>
        <p>Perplexity searches the web for public information about each lead (articles, interviews, company news, professional profiles) and generates a comprehensive persona including communication style, goals, pain points, and outreach recommendations.</p>
      </div>

      <div className="research-list">
        {leads.length === 0 ? (
          <div className="empty-state">
            <p>No leads available. Add leads to start researching personas.</p>
          </div>
        ) : (
          leads.map((lead) => (
            <div key={lead.id} className="research-card" data-testid={`research-lead-${lead.id}`}>
              <div className="research-info">
                <h3>{lead.name}</h3>
                <p>{lead.title || 'Position not specified'} • {lead.company || 'Company not specified'}</p>
                {lead.email && <p className="lead-contact">📧 {lead.email}</p>}
                {lead.linkedin_url && (
                  <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer" className="linkedin-link">
                    View LinkedIn Profile →
                  </a>
                )}
                {lead.persona && (
                  <div className="persona-result">
                    <div className="persona-header">
                      <strong>🎯 Generated Persona</strong>
                      {lead.score && <span className="persona-score">{lead.score}/10</span>}
                    </div>
                    <p style={{ whiteSpace: 'pre-wrap' }}>{lead.persona}</p>
                  </div>
                )}
              </div>
              <button
                onClick={() => handleResearch(lead)}
                className="btn-primary"
                disabled={researching === lead.id}
                data-testid={`research-btn-${lead.id}`}
              >
                {researching === lead.id ? (
                  <>
                    <span className="spinner-small"></span>
                    Researching...
                  </>
                ) : lead.persona ? (
                  '🔄 Re-research'
                ) : (
                  '🔍 Research Persona'
                )}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

// Settings Page
const SettingsPage = () => {
  const [integrations, setIntegrations] = useState(null);
  const [apiKeys, setApiKeys] = useState({ 
    perplexity: '', 
    openai: '', 
    gemini: '', 
    resend: '', 
    phantombuster: '',
    linkedin_cookie: ''
  });
  const [showApiKeys, setShowApiKeys] = useState(false);
  const [sheetsUrl, setSheetsUrl] = useState('');
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetchIntegrations();
    fetchApiKeys();
  }, []);

  const fetchIntegrations = async () => {
    try {
      const response = await api.get('/settings/integrations');
      setIntegrations(response.data);
    } catch (error) {
      toast.error('Failed to load integrations');
    }
    setLoading(false);
  };

  const fetchApiKeys = async () => {
    try {
      const response = await api.get('/settings/api-keys');
      setShowApiKeys(
        response.data.perplexity_configured || 
        response.data.openai_configured || 
        response.data.gemini_configured ||
        response.data.resend_configured
      );
    } catch (error) {
      console.error('Failed to load API keys');
    }
  };

  const saveApiKeys = async () => {
    try {
      const payload = {
        perplexity_key: apiKeys.perplexity || undefined,
        openai_key: apiKeys.openai || undefined,
        gemini_key: apiKeys.gemini || undefined,
        resend_key: apiKeys.resend || undefined,
        phantombuster_key: apiKeys.phantombuster || undefined
      };
      
      await api.post('/settings/api-keys', payload);
      toast.success('API keys saved!');
      setApiKeys({ perplexity: '', openai: '', gemini: '', resend: '', phantombuster: '' });
      fetchIntegrations();
      fetchApiKeys();
    } catch (error) {
      toast.error('Failed to save API keys');
    }
  };

  const handleConnectSheets = async () => {
    if (!sheetsUrl) {
      toast.error('Please enter a Google Sheets URL');
      return;
    }

    try {
      await api.post('/integrations/google-sheets/connect', { spreadsheet_url: sheetsUrl });
      toast.success('Google Sheets connected!');
      setSheetsUrl('');
      fetchIntegrations();
    } catch (error) {
      toast.error('Failed to connect Google Sheets');
    }
  };

  const handleSyncSheets = async () => {
    setSyncing(true);
    try {
      const response = await api.post('/integrations/google-sheets/sync');
      toast.success(`Synced ${response.data.synced_leads} leads`);
    } catch (error) {
      toast.error('Sync failed');
    }
    setSyncing(false);
  };

  if (loading) {
    return <div className="loading-screen"><div className="loading-spinner"></div></div>;
  }

  const getStatusBadge = (status) => {
    const statusMap = {
      'ready': { label: '✅ Ready', class: 'status-active' },
      'connected': { label: '✅ Connected', class: 'status-active' },
      'not_configured': { label: '⚠️ Not Configured', class: 'status-paused' },
      'not_connected': { label: '❌ Not Connected', class: 'status-draft' },
      'mock_mode': { label: '🔄 Mock Mode', class: 'status-paused' }
    };
    const badge = statusMap[status] || { label: status, class: 'status-draft' };
    return <span className={`status-badge ${badge.class}`}>{badge.label}</span>;
  };

  return (
    <div className="page-container" data-testid="settings-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Manage integrations and API connections</p>
        </div>
      </div>

      {/* API Keys Configuration */}
      <div className="settings-section">
        <h2 className="settings-title">🔑 API Keys</h2>
        <div className="api-keys-config">
          <div className="config-note" style={{ marginBottom: '1.5rem' }}>
            <p>Configure your own API keys or use the built-in Emergent LLM Key for GPT-5 and Gemini.</p>
          </div>
          
          <div className="form-group">
            <label className="form-label">Perplexity API Key</label>
            <input
              type="password"
              placeholder="pplx-..."
              value={apiKeys.perplexity}
              onChange={(e) => setApiKeys({ ...apiKeys, perplexity: e.target.value })}
              className="input"
              data-testid="perplexity-key-input"
            />
            <small style={{ color: '#a0a0b0', display: 'block', marginTop: '0.5rem' }}>
              Get your key from: <a href="https://www.perplexity.ai/settings/api" target="_blank" rel="noopener noreferrer" style={{ color: '#93c5fd' }}>perplexity.ai/settings/api</a>
            </small>
          </div>

          <div className="form-group">
            <label className="form-label">OpenAI API Key (Optional)</label>
            <input
              type="password"
              placeholder="sk-..."
              value={apiKeys.openai}
              onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
              className="input"
              data-testid="openai-key-input"
            />
            <small style={{ color: '#a0a0b0', display: 'block', marginTop: '0.5rem' }}>
              Leave blank to use Emergent LLM Key (recommended)
            </small>
          </div>

          <div className="form-group">
            <label className="form-label">Gemini API Key (Optional)</label>
            <input
              type="password"
              placeholder="AI..."
              value={apiKeys.gemini}
              onChange={(e) => setApiKeys({ ...apiKeys, gemini: e.target.value })}
              className="input"
              data-testid="gemini-key-input"
            />
            <small style={{ color: '#a0a0b0', display: 'block', marginTop: '0.5rem' }}>
              Leave blank to use Emergent LLM Key (recommended)
            </small>
          </div>

          <div className="form-group">
            <label className="form-label">Resend API Key (Email Sending)</label>
            <input
              type="password"
              placeholder="re_..."
              value={apiKeys.resend}
              onChange={(e) => setApiKeys({ ...apiKeys, resend: e.target.value })}
              className="input"
              data-testid="resend-key-input"
            />
            <small style={{ color: '#a0a0b0', display: 'block', marginTop: '0.5rem' }}>
              Get your key from: <a href="https://resend.com/api-keys" target="_blank" rel="noopener noreferrer" style={{ color: '#93c5fd' }}>resend.com/api-keys</a>
            </small>
          </div>

          <div className="form-group">
            <label className="form-label">Phantombuster API Key (LinkedIn Automation)</label>
            <input
              type="password"
              placeholder="Already configured ✅"
              value={apiKeys.phantombuster}
              onChange={(e) => setApiKeys({ ...apiKeys, phantombuster: e.target.value })}
              className="input"
              data-testid="phantombuster-key-input"
            />
            <small style={{ color: '#22c55e', display: 'block', marginTop: '0.5rem' }}>
              ✅ Phantombuster key already configured in backend!
            </small>
          </div>

          <button onClick={saveApiKeys} className="btn-primary" data-testid="save-api-keys-btn">
            💾 Save API Keys
          </button>
        </div>
      </div>

      <div className="settings-section">
        <h2 className="settings-title">🤖 AI Models</h2>
        <div className="integration-grid">
          <div className="integration-card">
            <div className="integration-header">
              <h3>GPT-5 (OpenAI)</h3>
              {getStatusBadge(integrations?.ai_models?.gpt5?.status)}
            </div>
            <p>Advanced AI for analytics and insights generation</p>
            {integrations?.ai_models?.gpt5?.enabled && (
              <div className="integration-info">Using Emergent LLM Key</div>
            )}
          </div>

          <div className="integration-card">
            <div className="integration-header">
              <h3>Gemini (Google)</h3>
              {getStatusBadge(integrations?.ai_models?.gemini?.status)}
            </div>
            <p>Alternative AI model for content generation</p>
            {integrations?.ai_models?.gemini?.enabled && (
              <div className="integration-info">Using Emergent LLM Key</div>
            )}
          </div>

          <div className="integration-card">
            <div className="integration-header">
              <h3>Perplexity AI</h3>
              {getStatusBadge(integrations?.ai_models?.perplexity?.status)}
            </div>
            <p>LinkedIn profile research and persona generation</p>
            {integrations?.ai_models?.perplexity?.status === 'not_configured' && (
              <div className="integration-warning">
                Add your Perplexity API key above to enable
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="settings-section">
        <h2 className="settings-title">🔗 Integrations</h2>
        <div className="integration-grid">
          <div className="integration-card">
            <div className="integration-header">
              <h3>Google Sheets</h3>
              {getStatusBadge(integrations?.integrations?.google_sheets?.status)}
            </div>
            <p>Bi-directional CRM sync with Google Sheets</p>
            
            {!integrations?.integrations?.google_sheets?.connected ? (
              <div style={{ marginTop: '1rem' }}>
                <input
                  type="text"
                  placeholder="Paste Google Sheets URL"
                  value={sheetsUrl}
                  onChange={(e) => setSheetsUrl(e.target.value)}
                  className="input"
                  data-testid="sheets-url-input"
                />
                <button 
                  onClick={handleConnectSheets} 
                  className="btn-primary" 
                  style={{ marginTop: '0.5rem' }}
                  data-testid="connect-sheets-btn"
                >
                  Connect Sheet
                </button>
              </div>
            ) : (
              <button 
                onClick={handleSyncSheets} 
                className="btn-secondary" 
                style={{ marginTop: '1rem' }}
                disabled={syncing}
                data-testid="sync-sheets-btn"
              >
                {syncing ? 'Syncing...' : '🔄 Sync Now'}
              </button>
            )}
          </div>

          <div className="integration-card">
            <div className="integration-header">
              <h3>LinkedIn</h3>
              {getStatusBadge(integrations?.integrations?.linkedin?.status)}
            </div>
            <p>Automated outreach via Phantombuster</p>
            {integrations?.integrations?.linkedin?.connected ? (
              <div className="integration-info">
                ✅ Phantombuster connected - Ready to send LinkedIn messages!
              </div>
            ) : (
              <div className="integration-warning">
                Add Phantombuster API key above to enable
              </div>
            )}
          </div>

          <div className="integration-card">
            <div className="integration-header">
              <h3>Email Service</h3>
              {getStatusBadge(integrations?.integrations?.email?.status)}
            </div>
            <p>Email outreach via Resend/SendGrid</p>
            <div className="integration-warning">
              Configure email service to enable sending
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Messages/Inbox Page
const MessagesPage = () => {
  const [messages, setMessages] = useState([]);
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [replyText, setReplyText] = useState('');
  const [filter, setFilter] = useState('all'); // all, incoming, outgoing
  const [sending, setSending] = useState(false);

  useEffect(() => {
    fetchMessages();
  }, [filter]);

  const fetchMessages = async () => {
    try {
      const params = filter !== 'all' ? { direction: filter } : {};
      const response = await api.get('/messages', { params });
      setMessages(response.data);
    } catch (error) {
      toast.error('Failed to load messages');
    }
  };

  const handleSendReply = async () => {
    if (!replyText.trim()) {
      toast.error('Reply cannot be empty');
      return;
    }

    setSending(true);
    try {
      await api.post('/messages/reply', {
        message_id: selectedMessage.id,
        content: replyText
      });
      toast.success('Reply sent!');
      setReplyText('');
      setSelectedMessage(null);
      fetchMessages();
    } catch (error) {
      toast.error('Failed to send reply');
    }
    setSending(false);
  };

  const incomingMessages = messages.filter(m => m.direction === 'incoming');
  const outgoingMessages = messages.filter(m => m.direction === 'outgoing');

  return (
    <div className="page-container" data-testid="messages-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Messages</h1>
          <p className="page-subtitle">View and respond to campaign messages</p>
        </div>
      </div>

      <div className="messages-layout">
        {/* Sidebar - Message List */}
        <div className="messages-sidebar">
          <div className="message-filters">
            <button
              className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({messages.length})
            </button>
            <button
              className={`filter-btn ${filter === 'incoming' ? 'active' : ''}`}
              onClick={() => setFilter('incoming')}
            >
              📥 Inbox ({incomingMessages.length})
            </button>
            <button
              className={`filter-btn ${filter === 'outgoing' ? 'active' : ''}`}
              onClick={() => setFilter('outgoing')}
            >
              📤 Sent ({outgoingMessages.length})
            </button>
          </div>

          <div className="messages-list">
            {messages.length === 0 ? (
              <div className="empty-state">
                <p>No messages yet</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`message-item ${selectedMessage?.id === msg.id ? 'selected' : ''} ${msg.direction}`}
                  onClick={() => setSelectedMessage(msg)}
                  data-testid={`message-${msg.id}`}
                >
                  <div className="message-item-header">
                    <strong>{msg.lead_name || 'Unknown Lead'}</strong>
                    <span className="message-time">
                      {msg.sent_at ? new Date(msg.sent_at).toLocaleDateString() : ''}
                    </span>
                  </div>
                  <div className="message-item-preview">
                    {msg.subject && <div className="message-subject">{msg.subject}</div>}
                    <div className="message-preview">{msg.content?.substring(0, 60)}...</div>
                  </div>
                  <div className="message-item-meta">
                    <span className={`direction-badge ${msg.direction}`}>
                      {msg.direction === 'incoming' ? '📥' : '📤'}
                    </span>
                    <span className={`status-indicator status-${msg.status}`}>
                      {msg.status}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Main - Message Detail & Reply */}
        <div className="message-detail">
          {!selectedMessage ? (
            <div className="empty-state">
              <p>Select a message to view details</p>
            </div>
          ) : (
            <div className="message-content">
              <div className="message-header">
                <div>
                  <h3>{selectedMessage.lead_name}</h3>
                  <p>{selectedMessage.lead_email} • {selectedMessage.lead_company}</p>
                </div>
                <div className="message-header-meta">
                  <span className={`status-badge status-${selectedMessage.status}`}>
                    {selectedMessage.status}
                  </span>
                  <span className={`channel-badge`}>
                    {selectedMessage.channel === 'email' ? '📧 Email' : '💼 LinkedIn'}
                  </span>
                </div>
              </div>

              <div className="message-body">
                {selectedMessage.subject && (
                  <div className="message-subject-display">
                    <strong>Subject:</strong> {selectedMessage.subject}
                  </div>
                )}
                <div className="message-text">
                  {selectedMessage.content}
                </div>
                <div className="message-footer">
                  <small>
                    Sent: {selectedMessage.sent_at ? new Date(selectedMessage.sent_at).toLocaleString() : 'N/A'}
                  </small>
                  {selectedMessage.opened_at && (
                    <small>Opened: {new Date(selectedMessage.opened_at).toLocaleString()}</small>
                  )}
                  {selectedMessage.replied_at && (
                    <small>Replied: {new Date(selectedMessage.replied_at).toLocaleString()}</small>
                  )}
                </div>
              </div>

              {selectedMessage.direction === 'incoming' && (
                <div className="reply-section">
                  <h4>Reply</h4>
                  <textarea
                    placeholder="Type your reply..."
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    className="input"
                    rows="8"
                    data-testid="reply-textarea"
                  />
                  <button
                    onClick={handleSendReply}
                    className="btn-primary"
                    disabled={sending}
                    data-testid="send-reply-btn"
                  >
                    {sending ? 'Sending...' : '📤 Send Reply'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth" element={<AuthHandler />} />
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <DashboardLayout>
                <Dashboard />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/campaigns" element={
            <ProtectedRoute>
              <DashboardLayout>
                <CampaignsPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/campaigns/:campaignId/edit" element={
            <ProtectedRoute>
              <DashboardLayout>
                <CampaignBuilder />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/leads" element={
            <ProtectedRoute>
              <DashboardLayout>
                <LeadsPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/messages" element={
            <ProtectedRoute>
              <DashboardLayout>
                <MessagesPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/analytics" element={
            <ProtectedRoute>
              <DashboardLayout>
                <AnalyticsPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/research" element={
            <ProtectedRoute>
              <DashboardLayout>
                <ResearchPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/ai-studio" element={
            <ProtectedRoute>
              <DashboardLayout>
                <AIAgentStudio />
              </DashboardLayout>
            </ProtectedRoute>
          } />
          <Route path="/settings" element={
            <ProtectedRoute>
              <DashboardLayout>
                <SettingsPage />
              </DashboardLayout>
            </ProtectedRoute>
          } />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
