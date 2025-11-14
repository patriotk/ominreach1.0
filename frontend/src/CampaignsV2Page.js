import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api/v2/campaigns`;

const api = axios.create({
  baseURL: BACKEND_URL,
  withCredentials: true
});

api.interceptors.request.use((config) => {
  const sessionToken = localStorage.getItem('session_token');
  if (sessionToken) {
    config.headers.Authorization = `Bearer ${sessionToken}`;
  }
  return config;
});

export const CampaignsV2Page = () => {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newCampaign, setNewCampaign] = useState({
    name: '',
    type: 'email',
    lead_limit: 100
  });

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const fetchCampaigns = async () => {
    try {
      const response = await api.get(API);
      setCampaigns(response.data);
    } catch (error) {
      toast.error('Failed to load campaigns');
    }
    setLoading(false);
  };

  const createCampaign = async () => {
    if (!newCampaign.name) {
      toast.error('Please enter campaign name');
      return;
    }

    try {
      const response = await api.post(API, newCampaign);
      toast.success('Campaign created!');
      setShowCreate(false);
      setNewCampaign({ name: '', type: 'email', lead_limit: 100 });
      navigate(`/campaigns-v2/${response.data.id}`);
    } catch (error) {
      toast.error('Failed to create campaign');
    }
  };

  const deleteCampaign = async (campaignId) => {
    if (!window.confirm('Delete this campaign?')) return;

    try {
      await api.delete(`${API}/${campaignId}`);
      toast.success('Campaign deleted');
      fetchCampaigns();
    } catch (error) {
      toast.error('Failed to delete campaign');
    }
  };

  if (loading) {
    return <div className="loading-screen"><div className="loading-spinner"></div></div>;
  }

  return (
    <div className="campaigns-v2-page">
      <div className="page-header">
        <div>
          <h1>🚀 Campaigns (V2)</h1>
          <p style={{ color: '#a0a0b0' }}>Create and manage your outreach campaigns</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          ➕ New Campaign
        </button>
      </div>

      {campaigns.length === 0 ? (
        <div className="empty-state">
          <h3>No campaigns yet</h3>
          <p>Create your first campaign to get started</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary" style={{ marginTop: '1rem' }}>
            ➕ Create Campaign
          </button>
        </div>
      ) : (
        <div className="campaigns-grid">
          {campaigns.map(campaign => (
            <div key={campaign.id} className="campaign-card-v2">
              <div className="campaign-card-header">
                <h3>{campaign.name}</h3>
                <span className={`status-badge status-${campaign.status}`}>{campaign.status}</span>
              </div>
              <div className="campaign-card-meta">
                <span>{campaign.type === 'email' ? '📧 Email' : '💼 LinkedIn'}</span>
                <span>{campaign.selected_lead_ids?.length || 0} / {campaign.lead_limit} leads</span>
              </div>
              <div className="campaign-card-actions">
                <button onClick={() => navigate(`/campaigns-v2/${campaign.id}`)} className="btn-secondary">
                  ✏️ Edit
                </button>
                <button onClick={() => deleteCampaign(campaign.id)} className="btn-danger">
                  🗑️ Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && (
        <div className="modal-overlay" onClick={() => setShowCreate(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create New Campaign</h2>
            <div className="form-group">
              <label>Campaign Name</label>
              <input
                type="text"
                placeholder="e.g., Q4 Outreach Campaign"
                value={newCampaign.name}
                onChange={(e) => setNewCampaign({ ...newCampaign, name: e.target.value })}
                className="input"
              />
            </div>
            <div className="form-group">
              <label>Campaign Type</label>
              <select
                value={newCampaign.type}
                onChange={(e) => setNewCampaign({ ...newCampaign, type: e.target.value })}
                className="input"
              >
                <option value="email">📧 Email Campaign</option>
                <option value="linkedin">💼 LinkedIn Campaign</option>
              </select>
            </div>
            <div className="form-group">
              <label>Lead Limit</label>
              <input
                type="number"
                min="1"
                max="10000"
                value={newCampaign.lead_limit}
                onChange={(e) => setNewCampaign({ ...newCampaign, lead_limit: parseInt(e.target.value) })}
                className="input"
              />
            </div>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
              <button onClick={createCampaign} className="btn-primary">
                ✅ Create Campaign
              </button>
              <button onClick={() => setShowCreate(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CampaignsV2Page;
