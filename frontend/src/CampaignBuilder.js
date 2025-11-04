import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({
  baseURL: API,
  withCredentials: true
});

api.interceptors.request.use((config) => {
  const sessionToken = localStorage.getItem('session_token');
  if (sessionToken) {
    config.headers.Authorization = `Bearer ${sessionToken}`;
  }
  return config;
});

export const CampaignBuilder = () => {
  const { campaignId } = useParams();
  const navigate = useNavigate();
  const [campaign, setCampaign] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('product');
  const [leads, setLeads] = useState([]);
  const [initializingSteps, setInitializingSteps] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState(false);
  const [campaignEdits, setCampaignEdits] = useState({});

  useEffect(() => {
    if (campaignId) {
      fetchCampaign();
      fetchLeads();
    }
  }, [campaignId]);

  const fetchCampaign = async () => {
    try {
      const response = await api.get(`/campaigns/${campaignId}`);
      const campaignData = response.data;
      setCampaign(campaignData);
      setCampaignEdits({
        name: campaignData.name,
        product_info: campaignData.product_info || {}
      });
      
      // Auto-initialize 3 steps if campaign is new and hasn't been initialized
      if ((!campaignData.message_steps || campaignData.message_steps.length === 0) && !initializingSteps) {
        await initializeDefaultSteps(campaignData);
      }
    } catch (error) {
      toast.error('Failed to load campaign');
    }
    setLoading(false);
  };

  const initializeDefaultSteps = async (campaignData) => {
    if (initializingSteps) return;
    setInitializingSteps(true);

    const channel = campaignData.goal_type;
    const defaultSteps = [
      {
        step_number: 1,
        channel: channel,
        delay_days: 0,
        delay_hours: 0,
        variants: [
          { 
            id: `var-1a-${Date.now()}`, 
            name: 'Variant A', 
            subject: channel === 'email' ? 'Quick question, {{first_name}}' : '',
            content: `Hi {{first_name}},\n\nI noticed your work at {{company}} and thought this might be relevant.\n\nBest regards`,
            percentage: 50
          },
          { 
            id: `var-1b-${Date.now()}`, 
            name: 'Variant B', 
            subject: channel === 'email' ? 'Thought of you, {{first_name}}' : '',
            content: `Hello {{first_name}},\n\nYour role as {{job_title}} caught my attention.\n\nCheers`,
            percentage: 50
          }
        ]
      },
      {
        step_number: 2,
        channel: channel,
        delay_days: 3,
        delay_hours: 0,
        variants: [
          { 
            id: `var-2a-${Date.now()}`, 
            name: 'Variant A', 
            subject: channel === 'email' ? 'Following up' : '',
            content: `Hi {{first_name}},\n\nJust following up on my previous message.\n\nBest`,
            percentage: 50
          },
          { 
            id: `var-2b-${Date.now()}`, 
            name: 'Variant B', 
            subject: channel === 'email' ? 'Checking in' : '',
            content: `{{first_name}},\n\nWanted to check if you saw my last message.\n\nThanks`,
            percentage: 50
          }
        ]
      },
      {
        step_number: 3,
        channel: channel,
        delay_days: 5,
        delay_hours: 0,
        variants: [
          { 
            id: `var-3a-${Date.now()}`, 
            name: 'Variant A', 
            subject: channel === 'email' ? 'Last attempt' : '',
            content: `Hi {{first_name}},\n\nThis is my final follow-up.\n\nRegards`,
            percentage: 50
          },
          { 
            id: `var-3b-${Date.now()}`, 
            name: 'Variant B', 
            subject: channel === 'email' ? 'Final note' : '',
            content: `{{first_name}},\n\nOne last message before I close the loop.\n\nBest`,
            percentage: 50
          }
        ]
      }
    ];

    try {
      for (const step of defaultSteps) {
        await api.post(`/campaigns/${campaignId}/steps`, step);
      }
      toast.success('3-step sequence initialized!');
      fetchCampaign();
    } catch (error) {
      console.error('Failed to initialize steps:', error);
      toast.error('Failed to initialize sequence');
    }
    setInitializingSteps(false);
  };

  const fetchLeads = async () => {
    try {
      const response = await api.get('/leads');
      setLeads(response.data);
    } catch (error) {
      console.error('Failed to load leads');
    }
  };

  const addStep = async () => {
    const newStepNumber = (campaign.message_steps?.length || 0) + 1;
    const step = {
      step_number: newStepNumber,
      channel: 'email',
      delay_days: newStepNumber === 1 ? 0 : 2,
      variants: [
        { id: `var-a-${Date.now()}`, name: 'Variant A', subject: '', content: '' },
        { id: `var-b-${Date.now()}`, name: 'Variant B', subject: '', content: '' }
      ]
    };

    try {
      await api.post(`/campaigns/${campaignId}/steps`, step);
      toast.success('Step added!');
      fetchCampaign();
    } catch (error) {
      toast.error('Failed to add step');
    }
  };

  const updateVariant = (stepIndex, variantIndex, field, value) => {
    const updatedCampaign = { ...campaign };
    updatedCampaign.message_steps[stepIndex].variants[variantIndex][field] = value;
    setCampaign(updatedCampaign);
  };

  const saveStep = async (stepIndex) => {
    // In a full implementation, this would update the specific step
    toast.success('Step saved!');
  };

  const setSchedule = async (scheduleData) => {
    try {
      await api.post(`/campaigns/${campaignId}/schedule`, scheduleData);
      toast.success('Schedule saved!');
      fetchCampaign();
    } catch (error) {
      toast.error('Failed to save schedule');
    }
  };

  const validateCampaign = async () => {
    try {
      const response = await api.post(`/campaigns/${campaignId}/validate`);
      if (response.data.valid) {
        toast.success('Campaign is valid!');
      } else {
        toast.error(`Validation errors: ${response.data.errors.join(', ')}`);
      }
    } catch (error) {
      toast.error('Validation failed');
    }
  };

  const activateCampaign = async () => {
    try {
      const response = await api.post(`/campaigns/${campaignId}/activate`);
      if (response.data.success) {
        toast.success('Campaign activated!');
        fetchCampaign();
      } else {
        toast.error(`Cannot activate: ${response.data.errors.join(', ')}`);
      }
    } catch (error) {
      toast.error('Failed to activate campaign');
    }
  };

  const assignLeads = async (selectedLeadIds) => {
    try {
      await api.patch(`/campaigns/${campaignId}`, { lead_ids: selectedLeadIds });
      toast.success(`${selectedLeadIds.length} leads assigned!`);
      fetchCampaign();
    } catch (error) {
      toast.error('Failed to assign leads');
    }
  };

  const saveCampaignEdits = async () => {
    try {
      await api.patch(`/campaigns/${campaignId}`, campaignEdits);
      toast.success('Campaign updated!');
      setEditingCampaign(false);
      fetchCampaign();
    } catch (error) {
      toast.error('Failed to update campaign');
    }
  };

  const generateAIMessage = async (stepNumber, variantName, leadId) => {
    try {
      const response = await api.post('/campaigns/generate-message', {
        campaign_id: campaignId,
        step_number: stepNumber,
        lead_id: leadId,
        variant_name: variantName
      });
      
      toast.success('AI message generated!');
      return response.data;
    } catch (error) {
      toast.error('AI generation failed');
      return null;
    }
  };

  if (loading) {
    return <div className="loading-screen"><div className="loading-spinner"></div></div>;
  }

  if (!campaign) {
    return <div>Campaign not found</div>;
  }

  return (
    <div className="campaign-builder">
      <div className="builder-header">
        <div>
          <h1>{campaign.name}</h1>
          <div className="campaign-meta">
            <span className={`status-badge status-${campaign.status}`}>{campaign.status}</span>
            <span>Goal: {campaign.goal_type}</span>
            <span>{campaign.lead_ids?.length || 0} leads</span>
          </div>
        </div>
        <div className="builder-actions">
          <button onClick={validateCampaign} className="btn-secondary">
            Validate
          </button>
          {campaign.status === 'draft' && (
            <button onClick={activateCampaign} className="btn-primary">
              Activate Campaign
            </button>
          )}
          {campaign.status === 'active' && (
            <button onClick={() => api.patch(`/campaigns/${campaignId}`, { status: 'paused' }).then(fetchCampaign)} className="btn-secondary">
              Pause
            </button>
          )}
        </div>
      </div>

      <div className="builder-tabs">
        <button
          className={`tab ${activeTab === 'product' ? 'active' : ''}`}
          onClick={() => setActiveTab('product')}
        >
          📦 Product Info
        </button>
        <button
          className={`tab ${activeTab === 'steps' ? 'active' : ''}`}
          onClick={() => setActiveTab('steps')}
        >
          Message Steps
        </button>
        <button
          className={`tab ${activeTab === 'schedule' ? 'active' : ''}`}
          onClick={() => setActiveTab('schedule')}
        >
          Schedule
        </button>
        <button
          className={`tab ${activeTab === 'leads' ? 'active' : ''}`}
          onClick={() => setActiveTab('leads')}
        >
          Leads
        </button>
        <button
          className={`tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </div>

      <div className="builder-content">
        {activeTab === 'product' && (
          <ProductInfoEditor
            campaign={campaign}
            onSave={saveCampaignEdits}
            campaignEdits={campaignEdits}
            setCampaignEdits={setCampaignEdits}
            editingCampaign={editingCampaign}
            setEditingCampaign={setEditingCampaign}
          />
        )}

        {activeTab === 'steps' && (
          <StepsBuilder
            campaign={campaign}
            onAddStep={addStep}
            onUpdateVariant={updateVariant}
            onSaveStep={saveStep}
            leads={leads}
            generateAIMessage={generateAIMessage}
          />
        )}

        {activeTab === 'schedule' && (
          <ScheduleBuilder
            campaign={campaign}
            onSaveSchedule={setSchedule}
          />
        )}

        {activeTab === 'leads' && (
          <LeadsAssigner
            campaign={campaign}
            availableLeads={leads}
            onAssignLeads={assignLeads}
          />
        )}

        {activeTab === 'analytics' && (
          <CampaignAnalytics campaignId={campaignId} />
        )}
      </div>
    </div>
  );
};

const ProductInfoEditor = ({ campaign, onSave, campaignEdits, setCampaignEdits, editingCampaign, setEditingCampaign }) => {
  const productInfo = campaignEdits.product_info || {};

  const updateProductInfo = (field, value) => {
    setCampaignEdits({
      ...campaignEdits,
      product_info: {
        ...productInfo,
        [field]: value
      }
    });
  };

  return (
    <div className="product-info-editor">
      <div className="editor-header">
        <h3>Campaign & Product Information</h3>
        <button onClick={() => setEditingCampaign(!editingCampaign)} className="btn-secondary">
          {editingCampaign ? 'Cancel' : '✏️ Edit'}
        </button>
      </div>

      <div className="product-form">
        <div className="form-group">
          <label className="form-label">Campaign Name</label>
          {editingCampaign ? (
            <input
              type="text"
              value={campaignEdits.name || ''}
              onChange={(e) => setCampaignEdits({ ...campaignEdits, name: e.target.value })}
              className="input"
            />
          ) : (
            <div className="display-value">{campaign.name}</div>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">Product/Service Name</label>
          {editingCampaign ? (
            <input
              type="text"
              placeholder="E.g., CloudSync Pro"
              value={productInfo.name || ''}
              onChange={(e) => updateProductInfo('name', e.target.value)}
              className="input"
            />
          ) : (
            <div className="display-value">{productInfo.name || 'Not set'}</div>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">Product Description</label>
          {editingCampaign ? (
            <textarea
              placeholder="Brief description of what you're offering"
              value={productInfo.description || ''}
              onChange={(e) => updateProductInfo('description', e.target.value)}
              className="input"
              rows="4"
            />
          ) : (
            <div className="display-value">{productInfo.description || 'Not set'}</div>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">Key Benefits</label>
          {editingCampaign ? (
            <textarea
              placeholder="Main benefits and value propositions"
              value={productInfo.benefits || ''}
              onChange={(e) => updateProductInfo('benefits', e.target.value)}
              className="input"
              rows="3"
            />
          ) : (
            <div className="display-value">{productInfo.benefits || 'Not set'}</div>
          )}
        </div>

        <div className="form-group">
          <label className="form-label">Call-to-Action</label>
          {editingCampaign ? (
            <input
              type="text"
              placeholder="E.g., Schedule a demo, Learn more, Get started"
              value={productInfo.cta || ''}
              onChange={(e) => updateProductInfo('cta', e.target.value)}
              className="input"
            />
          ) : (
            <div className="display-value">{productInfo.cta || 'Not set'}</div>
          )}
        </div>

        {editingCampaign && (
          <button onClick={onSave} className="btn-primary">
            💾 Save Changes
          </button>
        )}
      </div>

      {!editingCampaign && (!productInfo.name || !productInfo.description) && (
        <div className="info-banner">
          <p>💡 Add product information to enable AI-powered message generation!</p>
        </div>
      )}
    </div>
  );
};

const StepsBuilder = ({ campaign, onAddStep, onUpdateVariant, onSaveStep, leads, generateAIMessage }) => {
  const steps = campaign.message_steps || [];
  const [generatingAI, setGeneratingAI] = useState(null);

  const handleAIGenerate = async (stepNumber, variantIndex, variantName) => {
    const leadWithPersona = leads.find(l => l.persona);
    
    if (!leadWithPersona) {
      toast.error('Please research at least one lead persona first (Research page)');
      return;
    }

    if (!campaign.product_info || !campaign.product_info.name) {
      toast.error('Please add product information first (Product Info tab)');
      return;
    }

    setGeneratingAI(`${stepNumber}-${variantIndex}`);
    const result = await generateAIMessage(stepNumber, variantName, leadWithPersona.id);
    
    if (result) {
      // Update the variant with AI-generated content
      const stepIndex = steps.findIndex(s => s.step_number === stepNumber);
      if (stepIndex !== -1) {
        onUpdateVariant(stepIndex, variantIndex, 'content', result.content);
        if (result.subject && campaign.goal_type === 'email') {
          onUpdateVariant(stepIndex, variantIndex, 'subject', result.subject);
        }
      }
    }
    
    setGeneratingAI(null);
  };

  const updateStepTiming = (stepIndex, field, value) => {
    toast.info('Step timing update - save to apply');
  };

  return (
    <div className="steps-builder">
      <div className="steps-header">
        <div>
          <h3>Message Sequence</h3>
          <p style={{ color: '#a0a0b0', fontSize: '0.95rem' }}>
            3-step sequence • Channel: {campaign.goal_type === 'email' ? '📧 Email' : '💼 LinkedIn'}
          </p>
        </div>
        {steps.length < 5 && (
          <button onClick={onAddStep} className="btn-secondary">
            + Add Step
          </button>
        )}
      </div>

      {steps.length === 0 ? (
        <div className="empty-state">
          <p>Initializing 3-step sequence...</p>
        </div>
      ) : (
        <div className="steps-list">
          {steps.map((step, stepIndex) => (
            <div key={step.id || stepIndex} className="step-card">
              <div className="step-header">
                <h4>Step {step.step_number}</h4>
                <div className="step-meta">
                  <span className="channel-badge">
                    {step.channel === 'email' ? '📧 Email' : '💼 LinkedIn'}
                  </span>
                </div>
              </div>

              {/* Timing Controls */}
              <div className="step-timing">
                <div className="timing-group">
                  <label>Wait after previous step:</label>
                  <div className="timing-inputs">
                    <input
                      type="number"
                      min="0"
                      value={step.delay_days || 0}
                      onChange={(e) => updateStepTiming(stepIndex, 'delay_days', parseInt(e.target.value))}
                      className="input timing-input"
                      placeholder="Days"
                    />
                    <span>days</span>
                    <input
                      type="number"
                      min="0"
                      max="23"
                      value={step.delay_hours || 0}
                      onChange={(e) => updateStepTiming(stepIndex, 'delay_hours', parseInt(e.target.value))}
                      className="input timing-input"
                      placeholder="Hours"
                    />
                    <span>hours</span>
                  </div>
                </div>
              </div>

              {/* A/B Variants */}
              <div className="variants-container">
                {step.variants?.map((variant, variantIndex) => (
                  <div key={variant.id || variantIndex} className="variant-card">
                    <div className="variant-header">
                      <h5>{variant.name}</h5>
                      <div className="variant-actions">
                        <div className="percentage-control">
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={variant.percentage || 50}
                            onChange={(e) => onUpdateVariant(stepIndex, variantIndex, 'percentage', parseInt(e.target.value))}
                            className="percentage-input"
                          />
                          <span>%</span>
                        </div>
                        <button
                          onClick={() => handleAIGenerate(step.step_number, variantIndex, variant.name)}
                          className="btn-ai-generate"
                          disabled={generatingAI === `${step.step_number}-${variantIndex}`}
                          title="Generate message using AI"
                        >
                          {generatingAI === `${step.step_number}-${variantIndex}` ? '⏳' : '🤖 AI'}
                        </button>
                      </div>
                    </div>
                    
                    {step.channel === 'email' && (
                      <input
                        type="text"
                        placeholder="Email subject line"
                        value={variant.subject || ''}
                        onChange={(e) => onUpdateVariant(stepIndex, variantIndex, 'subject', e.target.value)}
                        className="input"
                      />
                    )}
                    
                    <textarea
                      placeholder={`Message content...\n\nUse: {{first_name}}, {{company}}, {{job_title}}`}
                      value={variant.content || ''}
                      onChange={(e) => onUpdateVariant(stepIndex, variantIndex, 'content', e.target.value)}
                      className="input"
                      rows="8"
                    />
                    
                    <div className="variant-metrics">
                      <small>Sent: {variant.metrics?.sent || 0}</small>
                      <small>Opened: {variant.metrics?.opened || 0}</small>
                      <small>Replied: {variant.metrics?.replied || 0}</small>
                      {variant.is_winner && <small className="winner-badge">🏆 Winner</small>}
                    </div>
                  </div>
                ))}
              </div>

              <button onClick={() => onSaveStep(stepIndex)} className="btn-secondary">
                💾 Save Step {step.step_number}
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="sequence-summary">
        <h4>Sequence Timeline</h4>
        <div className="timeline">
          {steps.map((step, idx) => (
            <div key={idx} className="timeline-item">
              <div className="timeline-marker">{step.step_number}</div>
              <div className="timeline-content">
                <strong>Step {step.step_number}</strong>
                {step.delay_days > 0 || step.delay_hours > 0 ? (
                  <span className="timeline-delay">
                    Wait: {step.delay_days}d {step.delay_hours}h
                  </span>
                ) : (
                  <span className="timeline-delay">Immediate</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const ScheduleBuilder = ({ campaign, onSaveSchedule }) => {
  const [schedule, setSchedule] = useState(campaign.schedule || {
    start_date: new Date().toISOString().split('T')[0],
    timezone: 'UTC',
    sending_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
    sending_hours: [9, 10, 11, 14, 15, 16],
    max_daily_linkedin: 50,
    max_daily_email: 100,
    randomize_timing: true
  });

  const allDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  const toggleDay = (day) => {
    const days = schedule.sending_days.includes(day)
      ? schedule.sending_days.filter(d => d !== day)
      : [...schedule.sending_days, day];
    setSchedule({ ...schedule, sending_days: days });
  };

  return (
    <div className="schedule-builder">
      <h3>Campaign Schedule</h3>

      <div className="schedule-form">
        <div className="form-group">
          <label>Start Date</label>
          <input
            type="date"
            value={schedule.start_date}
            onChange={(e) => setSchedule({ ...schedule, start_date: e.target.value })}
            className="input"
          />
        </div>

        <div className="form-group">
          <label>Sending Days</label>
          <div className="day-selector">
            {allDays.map(day => (
              <button
                key={day}
                onClick={() => toggleDay(day)}
                className={`day-btn ${schedule.sending_days.includes(day) ? 'active' : ''}`}
              >
                {day.slice(0, 3)}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label>Sending Hours (24h format)</label>
          <input
            type="text"
            value={schedule.sending_hours.join(', ')}
            onChange={(e) => setSchedule({ ...schedule, sending_hours: e.target.value.split(',').map(n => parseInt(n.trim())).filter(n => !isNaN(n)) })}
            className="input"
            placeholder="9, 10, 11, 14, 15, 16"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Max Daily LinkedIn</label>
            <input
              type="number"
              value={schedule.max_daily_linkedin}
              onChange={(e) => setSchedule({ ...schedule, max_daily_linkedin: parseInt(e.target.value) })}
              className="input"
            />
          </div>

          <div className="form-group">
            <label>Max Daily Email</label>
            <input
              type="number"
              value={schedule.max_daily_email}
              onChange={(e) => setSchedule({ ...schedule, max_daily_email: parseInt(e.target.value) })}
              className="input"
            />
          </div>
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              checked={schedule.randomize_timing}
              onChange={(e) => setSchedule({ ...schedule, randomize_timing: e.target.checked })}
            />
            {' '}Randomize sending times (appears more natural)
          </label>
        </div>

        <button onClick={() => onSaveSchedule(schedule)} className="btn-primary">
          Save Schedule
        </button>
      </div>
    </div>
  );
};

const LeadsAssigner = ({ campaign, availableLeads, onAssignLeads }) => {
  const [selectedLeads, setSelectedLeads] = useState(campaign.lead_ids || []);

  const toggleLead = (leadId) => {
    setSelectedLeads(prev =>
      prev.includes(leadId)
        ? prev.filter(id => id !== leadId)
        : [...prev, leadId]
    );
  };

  return (
    <div className="leads-assigner">
      <div className="assigner-header">
        <h3>Assign Leads to Campaign</h3>
        <div>
          <span>{selectedLeads.length} selected</span>
          <button onClick={() => onAssignLeads(selectedLeads)} className="btn-primary">
            Assign Selected
          </button>
        </div>
      </div>

      <div className="leads-grid">
        {availableLeads.map(lead => (
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
  );
};

const CampaignAnalytics = ({ campaignId }) => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, [campaignId]);

  const fetchAnalytics = async () => {
    try {
      const response = await api.get(`/campaigns/${campaignId}/analytics`);
      setAnalytics(response.data);
    } catch (error) {
      toast.error('Failed to load analytics');
    }
    setLoading(false);
  };

  if (loading) {
    return <div className="loading-spinner"></div>;
  }

  const metrics = analytics?.overall_metrics || {};

  return (
    <div className="campaign-analytics">
      <h3>Campaign Performance</h3>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-label">Messages Sent</div>
          <div className="metric-value">{metrics.messages_sent || 0}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Open Rate</div>
          <div className="metric-value">{metrics.open_rate || 0}%</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Reply Rate</div>
          <div className="metric-value">{metrics.reply_rate || 0}%</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">AI Score</div>
          <div className="metric-value">{metrics.ai_score || 0}/10</div>
        </div>
      </div>

      {metrics.verdict && (
        <div className={`verdict-card verdict-${metrics.verdict.toLowerCase()}`}>
          <h4>Verdict: {metrics.verdict}</h4>
          {metrics.avg_response_time_hours && (
            <p>Average response time: {metrics.avg_response_time_hours.toFixed(1)} hours</p>
          )}
        </div>
      )}

      <h3>Variant Performance</h3>
      <div className="variants-performance">
        {analytics?.variant_performance?.map((vp, index) => (
          <div key={index} className="variant-performance-card">
            <h5>Step {vp.step} - {vp.variant}</h5>
            <div className="perf-stats">
              <span>Sent: {vp.metrics.messages_sent}</span>
              <span>Open: {vp.metrics.open_rate}%</span>
              <span>Reply: {vp.metrics.reply_rate}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
