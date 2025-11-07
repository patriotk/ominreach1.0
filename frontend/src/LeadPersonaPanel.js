import { useState } from 'react';
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

export const LeadPersonaPanel = ({ lead, onClose, onUpdate }) => {
  const [editingPersona, setEditingPersona] = useState(false);
  const [personaText, setPersonaText] = useState(lead.persona || '');
  const [regenerating, setRegenerating] = useState(false);

  const handleRegeneratePersona = async () => {
    if (!lead.name || !lead.linkedin_url) {
      toast.error('Name and LinkedIn URL required for persona generation');
      return;
    }

    setRegenerating(true);
    try {
      await api.post(`/leads/${lead.id}/regenerate-persona`);
      toast.success('Persona regeneration started! Check back in 30-60 seconds.');
      
      setTimeout(() => {
        if (onUpdate) onUpdate();
      }, 3000);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to regenerate');
    }
    setRegenerating(false);
  };

  const handleSavePersona = async () => {
    try {
      await api.patch(`/leads/${lead.id}`, {
        persona: personaText,
        persona_status: 'completed'
      });
      toast.success('Persona updated!');
      setEditingPersona(false);
      
      if (onUpdate) {
        onUpdate();
      }
    } catch (error) {
      toast.error('Failed to save persona');
    }
  };

  const handleGeneratePersona = async () => {
    await handleRegeneratePersona();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="lead-persona-panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-header">
          <h2>🪪 Lead Persona Profile</h2>
          <button onClick={onClose} className="close-btn">✕</button>
        </div>

        <div className="panel-content">
          {/* Lead Information */}
          <div className="lead-info-grid">
            <div className="info-item">
              <label>👤 Name</label>
              <div className="info-value">{lead.name}</div>
            </div>

            <div className="info-item">
              <label>🏢 Company</label>
              <div className="info-value">{lead.company || 'Not specified'}</div>
            </div>

            <div className="info-item">
              <label>💼 Title</label>
              <div className="info-value">{lead.title || 'Not specified'}</div>
            </div>

            <div className="info-item">
              <label>📧 Email</label>
              <div className="info-value">{lead.email || 'Not specified'}</div>
            </div>

            {lead.linkedin_url && (
              <div className="info-item" style={{ gridColumn: '1 / -1' }}>
                <label>🔗 LinkedIn</label>
                <div className="info-value">
                  <a 
                    href={lead.linkedin_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="linkedin-link-panel"
                  >
                    View Profile →
                  </a>
                </div>
              </div>
            )}
          </div>

          {/* Persona Section */}
          <div className="persona-section">
            <div className="section-header">
              <h3>🧠 Persona Summary</h3>
              {lead.score && <span className="persona-score-large">{lead.score}/10</span>}
            </div>

            {lead.persona_status === 'completed' && lead.persona ? (
              <div className="persona-content">
                {editingPersona ? (
                  <div>
                    <textarea
                      value={personaText}
                      onChange={(e) => setPersonaText(e.target.value)}
                      className="input"
                      rows="6"
                      style={{ width: '100%', marginBottom: '1rem' }}
                    />
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                      <button onClick={handleSavePersona} className="btn-primary">
                        💾 Save Changes
                      </button>
                      <button onClick={() => { setEditingPersona(false); setPersonaText(lead.persona); }} className="btn-secondary">
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <p className="persona-paragraph">{lead.persona}</p>
                    <div className="persona-actions">
                      <button 
                        onClick={handleRegeneratePersona}
                        className="btn-secondary"
                        disabled={regenerating}
                      >
                        {regenerating ? '🔄 Regenerating...' : '🔄 Regenerate Persona'}
                      </button>
                      <button 
                        onClick={() => setEditingPersona(true)}
                        className="btn-secondary"
                      >
                        ✏️ Edit Persona
                      </button>
                    </div>
                    <small style={{ color: '#22c55e', display: 'block', marginTop: '1rem' }}>
                      ✅ Saved as <code>{'{{leadPersona}}'}</code> variable for message generation
                    </small>
                  </div>
                )}
              </div>
            ) : lead.persona_status === 'researching' ? (
              <div className="persona-empty">
                <div className="spinner-small" style={{ margin: '2rem auto' }}></div>
                <p>Researching persona... This will take 30-60 seconds.</p>
              </div>
            ) : lead.persona_status === 'failed' ? (
              <div className="persona-empty">
                <p style={{ color: '#ef4444' }}>❌ {lead.persona || 'Persona generation failed'}</p>
                {lead.name && lead.linkedin_url && (
                  <button 
                    onClick={handleGeneratePersona}
                    className="btn-primary"
                    style={{ marginTop: '1rem' }}
                  >
                    🔄 Retry Generation
                  </button>
                )}
              </div>
            ) : (
              <div className="persona-empty">
                <p>⚠️ No persona available for this lead.</p>
                {lead.name && lead.linkedin_url ? (
                  <button 
                    onClick={handleGeneratePersona}
                    className="btn-primary"
                    style={{ marginTop: '1rem' }}
                  >
                    🤖 Generate Persona
                  </button>
                ) : (
                  <p style={{ color: '#a0a0b0', fontSize: '0.9rem' }}>
                    Add name and LinkedIn URL, then generate persona.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Status Bar */}
          <div className="status-bar">
            <div className="status-item">
              <span>Persona Status:</span>
              <span className={`status-badge status-${lead.persona_status || 'pending'}`}>
                {lead.persona_status === 'completed' && '✅ Success'}
                {lead.persona_status === 'researching' && '🔄 Researching'}
                {lead.persona_status === 'failed' && '❌ Failed'}
                {lead.persona_status === 'pending' && '⏳ Pending'}
              </span>
            </div>
            <div className="status-item">
              <span>Lead Status:</span>
              <span className={`status-badge ${lead.call_booked ? 'status-active' : 'status-draft'}`}>
                {lead.call_booked ? '✅ Call Booked' : lead.date_contacted ? '📧 Contacted' : '⏳ New'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
