import { useState } from 'react';
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

// Step Tab Component
export const StepTab = ({ campaign, stepNumber, onUpdate }) => {
  const step = campaign.steps?.find(s => s.step_number === stepNumber);
  const [uploading, setUploading] = useState(false);

  if (!step) {
    return <div>Step not found</div>;
  }

  const handleStepUpdate = async (field, value) => {
    try {
      const updates = { [field]: value };
      await api.patch(`${API}/${campaign.id}/steps/${stepNumber}`, updates);
      toast.success('Step updated!');
      onUpdate();
    } catch (error) {
      toast.error('Failed to update step');
    }
  };

  const handleBestPracticesUpload = async (event) => {
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

      await api.post(
        `${API}/${campaign.id}/steps/${stepNumber}/best-practices`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      toast.success('✅ Best practices uploaded!');
      onUpdate();
    } catch (error) {
      toast.error('Upload failed');
    }
    setUploading(false);
  };

  return (
    <div className="step-tab">
      <h2>Step {stepNumber} Configuration</h2>
      <p style={{ color: '#a0a0b0', marginBottom: '2rem' }}>
        {stepNumber === 1 && 'First contact - introduce value and build curiosity'}
        {stepNumber === 2 && 'Follow-up - reference previous message, add new insight'}
        {stepNumber === 3 && 'Final attempt - be direct, acknowledge previous messages'}
      </p>

      {/* Timing */}
      <div className="step-section">
        <h3>⏰ Timing</h3>
        <div className="form-row">
          <div className="form-group">
            <label>Delay after previous step</label>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <input
                type="number"
                min="0"
                value={step.delay_days}
                onChange={(e) => handleStepUpdate('delay_days', parseInt(e.target.value))}
                className="input"
                style={{ width: '100px' }}
              />
              <span>days</span>
              <input
                type="number"
                min="0"
                max="23"
                value={step.delay_hours}
                onChange={(e) => handleStepUpdate('delay_hours', parseInt(e.target.value))}
                className="input"
                style={{ width: '100px' }}
              />
              <span>hours</span>
            </div>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Send Window (24hr format)</label>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <input
                type="number"
                min="0"
                max="23"
                value={step.window_start_hour}
                onChange={(e) => handleStepUpdate('window_start_hour', parseInt(e.target.value))}
                className="input"
                style={{ width: '100px' }}
              />
              <span>to</span>
              <input
                type="number"
                min="0"
                max="23"
                value={step.window_end_hour}
                onChange={(e) => handleStepUpdate('window_end_hour', parseInt(e.target.value))}
                className="input"
                style={{ width: '100px' }}
              />
              <small>(e.g., 9 to 17 = 9am-5pm)</small>
            </div>
          </div>
        </div>
      </div>

      {/* AI Agent Settings */}
      <div className="step-section">
        <h3>🤖 AI Agent Settings</h3>
        <div className="form-group">
          <label>Tone</label>
          <select
            value={step.agent_settings.tone}
            onChange={(e) => handleStepUpdate('agent_settings', { ...step.agent_settings, tone: e.target.value })}
            className="input"
          >
            <option value="professional">Professional</option>
            <option value="casual">Casual</option>
            <option value="friendly">Friendly</option>
            <option value="formal">Formal</option>
            <option value="consultative">Consultative</option>
          </select>
        </div>

        <div className="form-group">
          <label>Style</label>
          <select
            value={step.agent_settings.style}
            onChange={(e) => handleStepUpdate('agent_settings', { ...step.agent_settings, style: e.target.value })}
            className="input"
          >
            <option value="concise">Concise</option>
            <option value="detailed">Detailed</option>
            <option value="storytelling">Storytelling</option>
            <option value="data-driven">Data-Driven</option>
          </select>
        </div>

        <div className="form-group">
          <label>Focus</label>
          <select
            value={step.agent_settings.focus}
            onChange={(e) => handleStepUpdate('agent_settings', { ...step.agent_settings, focus: e.target.value })}
            className="input"
          >
            <option value="value-driven">Value-Driven</option>
            <option value="problem-focused">Problem-Focused</option>
            <option value="solution-oriented">Solution-Oriented</option>
            <option value="relationship-building">Relationship-Building</option>
          </select>
        </div>
      </div>

      {/* Best Practices Upload */}
      <div className="step-section">
        <h3>📄 Best Practices Document</h3>
        <p style={{ color: '#a0a0b0', fontSize: '0.9rem', marginBottom: '1rem' }}>
          Upload a document with messaging guidelines specific to this step.
        </p>
        
        <input
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleBestPracticesUpload}
          style={{ display: 'none' }}
          id={`best-practices-${stepNumber}`}
          disabled={uploading}
        />
        <label htmlFor={`best-practices-${stepNumber}`} className="file-upload-btn" style={{ cursor: uploading ? 'not-allowed' : 'pointer' }}>
          {uploading ? '📤 Uploading...' : step.best_practices_file_url ? '📄 Replace Document' : '📄 Upload Document'}
        </label>

        {step.best_practices_file_url && (
          <div className="uploaded-file-info" style={{ marginTop: '1rem' }}>
            <div className="file-chip">✅ {step.best_practices_file_url}</div>
            {step.best_practices_text && (
              <div className="parsed-preview" style={{ marginTop: '0.5rem' }}>
                <strong>Preview:</strong>
                <p>{step.best_practices_text.substring(0, 200)}...</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// Review Messages Tab Component
export const ReviewMessagesTab = ({ campaign, messages, leads, onUpdate }) => {
  const [generating, setGenerating] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [editingMessage, setEditingMessage] = useState(null);

  const generateTestMessages = async () => {
    if (campaign.selected_lead_ids.length < 3) {
      toast.error('Please select at least 3 leads first');
      return;
    }

    setGenerating(true);
    try {
      const response = await api.post('/api/v2/campaigns/generate-test-messages', {
        campaign_id: campaign.id
      });

      toast.success(`✨ Generated ${response.data.messages_generated} messages for 3 test leads!`);
      onUpdate();
    } catch (error) {
      toast.error('Failed to generate messages');
    }
    setGenerating(false);
  };

  const generateBulkMessages = async () => {
    if (!campaign.test_approved) {
      toast.error('Please approve test phase first');
      return;
    }

    setGenerating(true);
    try {
      const response = await api.post('/api/v2/campaigns/generate-bulk-messages', {
        campaign_id: campaign.id
      });

      toast.success(`✨ Generated ${response.data.messages_generated} messages for all leads!`);
      onUpdate();
    } catch (error) {
      toast.error('Failed to generate messages');
    }
    setGenerating(false);
  };

  const approveTestPhase = async () => {
    try {
      await api.post(`${API}/${campaign.id}/approve-test`);
      toast.success('✅ Test phase approved! Ready for bulk generation.');
      onUpdate();
    } catch (error) {
      toast.error('Failed to approve');
    }
  };

  const regenerateMessage = async (messageId) => {
    try {
      await api.post(`/api/v2/campaigns/regenerate-message/${messageId}`);
      toast.success('✨ Message regenerated!');
      onUpdate();
    } catch (error) {
      toast.error('Failed to regenerate');
    }
  };

  const updateMessage = async (messageId, updates) => {
    try {
      await api.patch(`/api/v2/campaigns/messages/${messageId}`, updates);
      toast.success('Message updated!');
      setEditingMessage(null);
      onUpdate();
    } catch (error) {
      toast.error('Failed to update');
    }
  };

  // Group messages by lead
  const messagesByLead = messages.reduce((acc, msg) => {
    if (!acc[msg.lead_id]) {
      acc[msg.lead_id] = [];
    }
    acc[msg.lead_id].push(msg);
    return acc;
  }, {});

  return (
    <div className="review-messages-tab">
      <div className="review-header">
        <h2>📝 Review Messages</h2>
        <div className="review-actions">
          {campaign.status === 'draft' && (
            <button onClick={generateTestMessages} disabled={generating} className="btn-primary">
              {generating ? '⏳ Generating...' : '🧪 Generate Test (3 Leads)'}
            </button>
          )}
          
          {campaign.status === 'test_phase' && !campaign.test_approved && (
            <button onClick={approveTestPhase} className="btn-success">
              ✅ Approve Test Phase
            </button>
          )}
          
          {campaign.test_approved && campaign.status !== 'approved' && (
            <button onClick={generateBulkMessages} disabled={generating} className="btn-primary">
              {generating ? '⏳ Generating...' : '🚀 Generate All Messages'}
            </button>
          )}
        </div>
      </div>

      {messages.length === 0 ? (
        <div className="empty-state">
          <p>No messages generated yet. Click "Generate Test" to start.</p>
        </div>
      ) : (
        <div className="messages-review-table">
          <table>
            <thead>
              <tr>
                <th>Lead</th>
                <th>Step 1</th>
                <th>Step 2</th>
                <th>Step 3</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(messagesByLead).map(leadId => {
                const lead = leads.find(l => l.id === leadId);
                const leadMessages = messagesByLead[leadId];
                
                return (
                  <tr key={leadId}>
                    <td>
                      <strong>{lead?.name || 'Unknown'}</strong><br />
                      <small>{lead?.title}</small>
                    </td>
                    {[1, 2, 3].map(stepNum => {
                      const msg = leadMessages.find(m => m.step_number === stepNum);
                      return (
                        <td key={stepNum}>
                          {msg ? (
                            <div className="message-preview">
                              {msg.subject && <div className="msg-subject">{msg.subject}</div>}
                              <div className="msg-body">{msg.content.substring(0, 80)}...</div>
                              <div className="msg-actions">
                                <button onClick={() => setSelectedLead({ leadId, stepNum, msg })} className="btn-xs">
                                  👁️ View
                                </button>
                                <button onClick={() => regenerateMessage(msg.id)} className="btn-xs">
                                  🔄 Regenerate
                                </button>
                              </div>
                            </div>
                          ) : (
                            <span style={{ color: '#888' }}>-</span>
                          )}
                        </td>
                      );
                    })}
                    <td>
                      <button onClick={() => setSelectedLead({ leadId, messages: leadMessages, lead })} className="btn-secondary btn-sm">
                        📋 View All
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Lead Messages Modal */}
      {selectedLead && selectedLead.messages && (
        <div className="modal-overlay" onClick={() => setSelectedLead(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>{selectedLead.lead?.name} - All Messages</h3>
            {selectedLead.messages.map(msg => (
              <div key={msg.id} className="message-card">
                <div className="message-header">
                  <strong>Step {msg.step_number}</strong>
                  {msg.ai_score && (
                    <span className="ai-score">AI Score: {msg.ai_score.total}/10</span>
                  )}
                </div>
                {msg.subject && <div className="msg-subject"><strong>Subject:</strong> {msg.subject}</div>}
                <div className="msg-body">{msg.content}</div>
                {msg.generation_context?.reasoning && (
                  <div className="msg-reasoning">
                    <strong>AI Reasoning:</strong> {msg.generation_context.reasoning}
                  </div>
                )}
                <div className="message-actions">
                  <button onClick={() => setEditingMessage(msg)} className="btn-secondary btn-sm">✏️ Edit</button>
                  <button onClick={() => regenerateMessage(msg.id)} className="btn-secondary btn-sm">🔄 Regenerate</button>
                </div>
              </div>
            ))}
            <button onClick={() => setSelectedLead(null)} className="btn-secondary">Close</button>
          </div>
        </div>
      )}

      {/* Edit Message Modal */}
      {editingMessage && (
        <div className="modal-overlay" onClick={() => setEditingMessage(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Edit Message - Step {editingMessage.step_number}</h3>
            {editingMessage.channel === 'email' && (
              <div className="form-group">
                <label>Subject</label>
                <input
                  type="text"
                  value={editingMessage.subject}
                  onChange={(e) => setEditingMessage({ ...editingMessage, subject: e.target.value })}
                  className="input"
                />
              </div>
            )}
            <div className="form-group">
              <label>Message</label>
              <textarea
                value={editingMessage.content}
                onChange={(e) => setEditingMessage({ ...editingMessage, content: e.target.value })}
                className="input"
                rows="10"
              />
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button onClick={() => updateMessage(editingMessage.id, { subject: editingMessage.subject, content: editingMessage.content })} className="btn-primary">💾 Save</button>
              <button onClick={() => setEditingMessage(null)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Schedule Tab Component
export const ScheduleTab = ({ campaign, onUpdate }) => {
  const [schedule, setSchedule] = useState(campaign.schedule || {
    start_date: '',
    start_time: '09:00',
    timezone: 'America/New_York',
    daily_cap: 50
  });

  const handleSave = async () => {
    try {
      await api.patch(`${API}/${campaign.id}`, { schedule });
      toast.success('Schedule saved!');
      onUpdate();
    } catch (error) {
      toast.error('Failed to save schedule');
    }
  };

  const handleActivate = async () => {
    if (!campaign.test_approved) {
      toast.error('Please approve test phase and generate all messages first');
      return;
    }

    if (!schedule.start_date) {
      toast.error('Please set a start date');
      return;
    }

    try {
      await api.post(`${API}/${campaign.id}/activate`);
      toast.success('🚀 Campaign activated!');
      onUpdate();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to activate');
    }
  };

  return (
    <div className="schedule-tab">
      <h2>🚀 Schedule & Activate Campaign</h2>
      <p style={{ color: '#a0a0b0', marginBottom: '2rem' }}>
        Configure when and how your campaign will run.
      </p>

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
        <label>Start Time</label>
        <input
          type="time"
          value={schedule.start_time}
          onChange={(e) => setSchedule({ ...schedule, start_time: e.target.value })}
          className="input"
        />
      </div>

      <div className="form-group">
        <label>Timezone</label>
        <select
          value={schedule.timezone}
          onChange={(e) => setSchedule({ ...schedule, timezone: e.target.value })}
          className="input"
        >
          <option value="America/New_York">Eastern Time (ET)</option>
          <option value="America/Chicago">Central Time (CT)</option>
          <option value="America/Denver">Mountain Time (MT)</option>
          <option value="America/Los_Angeles">Pacific Time (PT)</option>
          <option value="Europe/London">London (GMT)</option>
          <option value="Europe/Paris">Paris (CET)</option>
        </select>
      </div>

      <div className="form-group">
        <label>Daily Send Limit</label>
        <input
          type="number"
          min="1"
          max="1000"
          value={schedule.daily_cap}
          onChange={(e) => setSchedule({ ...schedule, daily_cap: parseInt(e.target.value) })}
          className="input"
        />
        <small>Maximum messages to send per day</small>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
        <button onClick={handleSave} className="btn-secondary">
          💾 Save Schedule
        </button>
        <button 
          onClick={handleActivate} 
          className="btn-success"
          disabled={campaign.status === 'active'}
        >
          {campaign.status === 'active' ? '✅ Campaign Active' : '🚀 Activate Campaign'}
        </button>
      </div>

      {campaign.status === 'active' && (
        <div className="success-message" style={{ marginTop: '2rem' }}>
          ✅ Campaign is active and sending messages according to schedule!
        </div>
      )}
    </div>
  );
};
