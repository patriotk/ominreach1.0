import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { StepTab, ReviewMessagesTab, ScheduleTab } from './CampaignBuilderV2_Components';

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

export const CampaignBuilderV2 = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [leads, setLeads] = useState([]);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    if (campaignId) {
      fetchCampaign();
      fetchLeads();
    }
  }, [campaignId]);

  const fetchCampaign = async () => {
    try {
      const response = await api.get(`${API}/${campaignId}`);
      setCampaign(response.data);
      
      // Fetch messages if in test phase or later
      if (['test_phase', 'approved', 'active'].includes(response.data.status)) {
        fetchMessages();
      }
    } catch (error) {
      toast.error('Failed to load campaign');
    }
    setLoading(false);
  };

  const fetchLeads = async () => {
    try {
      const response = await api.get('/api/leads');
      setLeads(response.data);
    } catch (error) {
      console.error('Failed to load leads');
    }
  };

  const fetchMessages = async () => {
    try {
      const response = await api.get(`${API}/${campaignId}/messages`);
      setMessages(response.data);
    } catch (error) {
      console.error('Failed to load messages');
    }
  };

  if (loading) {
    return <div className="loading-screen"><div className="loading-spinner"></div></div>;
  }

  if (!campaign) {
    return <div>Campaign not found</div>;
  }

  return (
    <div className="campaign-builder-v2">
      <div className="builder-header">
        <div>
          <h1>{campaign.name}</h1>
          <div className="campaign-meta">
            <span className={`status-badge status-${campaign.status}`}>{campaign.status}</span>
            <span className="type-badge">{campaign.type === 'email' ? '📧 Email' : '💼 LinkedIn'}</span>
            <span>{campaign.selected_lead_ids?.length || 0} / {campaign.lead_limit} leads</span>
          </div>
        </div>
        <div className="builder-actions">
          <button onClick={() => navigate('/dashboard')} className="btn-secondary">
            ← Back
          </button>
        </div>
      </div>

      <div className="builder-tabs-v2">
        <button
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📋 Overview
        </button>
        <button
          className={`tab ${activeTab === 'product' ? 'active' : ''}`}
          onClick={() => setActiveTab('product')}
        >
          📦 Product Info
        </button>
        <button
          className={`tab ${activeTab === 'step1' ? 'active' : ''}`}
          onClick={() => setActiveTab('step1')}
        >
          1️⃣ Step 1
        </button>
        <button
          className={`tab ${activeTab === 'step2' ? 'active' : ''}`}
          onClick={() => setActiveTab('step2')}
        >
          2️⃣ Step 2
        </button>
        <button
          className={`tab ${activeTab === 'step3' ? 'active' : ''}`}
          onClick={() => setActiveTab('step3')}
        >
          3️⃣ Step 3
        </button>
        <button
          className={`tab ${activeTab === 'review' ? 'active' : ''}`}
          onClick={() => setActiveTab('review')}
          disabled={messages.length === 0}
        >
          📝 Review Messages
          {messages.length > 0 && <span className="badge">{messages.length}</span>}
        </button>
        <button
          className={`tab ${activeTab === 'schedule' ? 'active' : ''}`}
          onClick={() => setActiveTab('schedule')}
        >
          🚀 Schedule & Activate
        </button>
      </div>

      <div className="builder-content-v2">
        {activeTab === 'overview' && (
          <OverviewTab 
            campaign={campaign} 
            onUpdate={fetchCampaign}
            leads={leads}
          />
        )}

        {activeTab === 'product' && (
          <ProductInfoTab 
            campaign={campaign} 
            onUpdate={fetchCampaign}
          />
        )}

        {['step1', 'step2', 'step3'].includes(activeTab) && (
          <StepTab 
            campaign={campaign}
            stepNumber={parseInt(activeTab.replace('step', ''))}
            onUpdate={fetchCampaign}
          />
        )}

        {activeTab === 'review' && (
          <ReviewMessagesTab 
            campaign={campaign}
            messages={messages}
            leads={leads}
            onUpdate={fetchMessages}
          />
        )}

        {activeTab === 'schedule' && (
          <ScheduleTab 
            campaign={campaign}
            onUpdate={fetchCampaign}
          />
        )}
      </div>
    </div>
  );
};

// Overview Tab Component
const OverviewTab = ({ campaign, onUpdate, leads }) => {
  const [selectedLeads, setSelectedLeads] = useState(campaign.selected_lead_ids || []);
  const [leadLimit, setLeadLimit] = useState(campaign.lead_limit || 100);

  const handleSave = async () => {
    try {
      await api.patch(`${API}/${campaign.id}`, {
        selected_lead_ids: selectedLeads,
        lead_limit: leadLimit
      });
      toast.success('Campaign updated!');
      onUpdate();
    } catch (error) {
      toast.error('Failed to update campaign');
    }
  };

  const toggleLead = (leadId) => {
    setSelectedLeads(prev =>
      prev.includes(leadId)
        ? prev.filter(id => id !== leadId)
        : [...prev, leadId]
    );
  };

  return (
    <div className="overview-tab">
      <h2>Campaign Overview</h2>
      
      <div className="form-group">
        <label>Campaign Name</label>
        <input
          type="text"
          value={campaign.name}
          className="input"
          disabled
        />
      </div>

      <div className="form-group">
        <label>Campaign Type</label>
        <div className="type-display">
          {campaign.type === 'email' ? '📧 Email Campaign' : '💼 LinkedIn Campaign'}
        </div>
      </div>

      <div className="form-group">
        <label>Lead Limit</label>
        <input
          type="number"
          min="1"
          max="10000"
          value={leadLimit}
          onChange={(e) => setLeadLimit(parseInt(e.target.value))}
          className="input"
          style={{ width: '150px' }}
        />
        <small>Maximum number of leads to engage in this campaign</small>
      </div>

      <div className="form-group">
        <label>Select Leads ({selectedLeads.length} selected)</label>
        <div className="leads-grid">
          {leads.map(lead => (
            <div
              key={lead.id}
              className={`lead-card ${selectedLeads.includes(lead.id) ? 'selected' : ''}`}
              onClick={() => toggleLead(lead.id)}
            >
              <input
                type="checkbox"
                checked={selectedLeads.includes(lead.id)}
                onChange={() => {}}
              />
              <div>
                <strong>{lead.name}</strong>
                <p>{lead.title} at {lead.company}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <button onClick={handleSave} className="btn-primary">
        💾 Save Changes
      </button>
    </div>
  );
};

// Product Info Tab Component  
const ProductInfoTab = ({ campaign, onUpdate }) => {
  const [uploading, setUploading] = useState(false);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.match(/\.(pdf|docx|txt)$/i)) {
      toast.error('Only PDF, DOCX, and TXT files supported');
      return;
    }

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post(
        `${API}/${campaign.id}/product-info/upload`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      toast.success('✨ Product info extracted with AI!');
      onUpdate();
    } catch (error) {
      toast.error('Upload failed');
    }
    setUploading(false);
  };

  const productInfo = campaign.product_info || {};

  return (
    <div className="product-info-tab">
      <h2>📦 Product Information</h2>
      <p style={{ color: '#a0a0b0', marginBottom: '2rem' }}>
        Upload your product document (brochure, pitch deck, website content) and AI will extract key information.
      </p>

      <div className="file-upload-section">
        <input
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileUpload}
          style={{ display: 'none' }}
          id="product-doc-upload"
          disabled={uploading}
        />
        <label htmlFor="product-doc-upload" className="file-upload-btn" style={{ cursor: uploading ? 'not-allowed' : 'pointer' }}>
          {uploading ? '📤 Uploading & Analyzing...' : '📄 Upload Product Document'}
        </label>
      </div>

      {productInfo.product_name && (
        <div className="product-info-display">
          <h3>✅ Extracted Product Information</h3>
          
          <div className="info-card">
            <label>Product Name</label>
            <div className="value">{productInfo.product_name}</div>
          </div>

          <div className="info-card">
            <label>Summary</label>
            <div className="value">{productInfo.summary}</div>
          </div>

          <div className="info-card">
            <label>Key Features</label>
            <ul className="features-list">
              {productInfo.features?.map((feature, idx) => (
                <li key={idx}>{feature}</li>
              ))}
            </ul>
          </div>

          <div className="info-card">
            <label>Differentiators</label>
            <ul className="features-list">
              {productInfo.differentiators?.map((diff, idx) => (
                <li key={idx}>{diff}</li>
              ))}
            </ul>
          </div>

          <div className="info-card">
            <label>Call to Action</label>
            <div className="value">{productInfo.call_to_action}</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CampaignBuilderV2;
