import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
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
    { path: '/analytics', label: 'Analytics', icon: '📈' },
    { path: '/research', label: 'Research', icon: '🔍' },
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
  const [campaigns, setCampaigns] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newCampaign, setNewCampaign] = useState({ name: '', target_persona: '' });

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
    try {
      await api.post('/campaigns', newCampaign);
      toast.success('Campaign created!');
      setShowCreate(false);
      setNewCampaign({ name: '', target_persona: '' });
      fetchCampaigns();
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
          + Create Campaign
        </button>
      </div>

      {showCreate && (
        <div className="create-form">
          <h3>New Campaign</h3>
          <input
            type="text"
            placeholder="Campaign name"
            value={newCampaign.name}
            onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
            className="input"
            data-testid="campaign-name-input"
          />
          <input
            type="text"
            placeholder="Target persona (optional)"
            value={newCampaign.target_persona}
            onChange={(e) => setNewCampaign({ ...newCampaign, target_persona: e.target.value })}
            className="input"
          />
          <div className="form-actions">
            <button onClick={handleCreate} className="btn-primary" data-testid="submit-campaign-btn">Create</button>
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
            <div key={campaign.id} className="campaign-card" data-testid={`campaign-${campaign.id}`}>
              <div className="campaign-info">
                <h3>{campaign.name}</h3>
                <p>Status: <span className={`status-badge status-${campaign.status}`}>{campaign.status}</span></p>
                <p>Variants: {campaign.message_variants?.length || 0}</p>
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
          <button onClick={() => setShowImport(true)} className="btn-secondary" data-testid="import-leads-btn">
            📥 Import Contacts
          </button>
          <button onClick={() => setShowCreate(true)} className="btn-primary" data-testid="add-lead-btn">
            + Add Lead
          </button>
        </div>
      </div>

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
                <th>Company</th>
                <th>Title</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id} data-testid={`lead-${lead.id}`}>
                  <td>{lead.name}</td>
                  <td>{lead.email || '-'}</td>
                  <td>{lead.company || '-'}</td>
                  <td>{lead.title || '-'}</td>
                  <td>
                    {lead.call_booked ? '✅ Booked' : lead.date_contacted ? '📧 Contacted' : '⏳ New'}
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
    if (!lead.linkedin_url) {
      toast.error('No LinkedIn URL provided');
      return;
    }

    setResearching(lead.id);
    try {
      const response = await api.post('/research/persona', {
        lead_id: lead.id,
        linkedin_url: lead.linkedin_url
      });
      toast.success('Persona generated!');
      fetchLeads();
    } catch (error) {
      toast.error('Research failed');
    }
    setResearching(null);
  };

  return (
    <div className="page-container" data-testid="research-page">
      <div className="page-header">
        <h1 className="page-title">LinkedIn Research</h1>
        <p className="page-subtitle">AI-powered persona generation from LinkedIn profiles</p>
      </div>

      <div className="research-list">
        {leads.filter(l => l.linkedin_url).length === 0 ? (
          <div className="empty-state">
            <p>No leads with LinkedIn URLs. Add LinkedIn URLs to leads to start researching.</p>
          </div>
        ) : (
          leads.filter(l => l.linkedin_url).map((lead) => (
            <div key={lead.id} className="research-card" data-testid={`research-lead-${lead.id}`}>
              <div className="research-info">
                <h3>{lead.name}</h3>
                <p>{lead.company} • {lead.title}</p>
                <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer" className="linkedin-link">
                  View LinkedIn Profile →
                </a>
                {lead.persona && (
                  <div className="persona-result">
                    <strong>Persona:</strong>
                    <p>{lead.persona}</p>
                  </div>
                )}
              </div>
              <button
                onClick={() => handleResearch(lead)}
                className="btn-primary"
                disabled={researching === lead.id}
                data-testid={`research-btn-${lead.id}`}
              >
                {researching === lead.id ? 'Researching...' : lead.persona ? '🔄 Re-research' : '🔍 Research'}
              </button>
            </div>
          ))
        )}
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
          <Route path="/leads" element={
            <ProtectedRoute>
              <DashboardLayout>
                <LeadsPage />
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
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
