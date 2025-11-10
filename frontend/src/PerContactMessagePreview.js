import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const api = axios.create({ baseURL: API, withCredentials: true });
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('session_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const PerContactMessagePreview = ({ campaign, lead, onClose }) => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(null);

  useEffect(() => {
    fetchMessages();
  }, []);

  const fetchMessages = async () => {
    try {
      const response = await api.get(`/campaigns/${campaign.id}/preview-messages/${lead.id}`);
      setMessages(response.data.messages || []);
    } catch (error) {
      toast.error('Failed to load message preview');
    }
    setLoading(false);
  };

  const regenerateStep = async (stepNumber) => {
    setRegenerating(stepNumber);
    try {
      await api.post(`/campaigns/${campaign.id}/regenerate-message`, {
        lead_id: lead.id,
        step_number: stepNumber
      });
      toast.success('Message regenerated!');
      fetchMessages();
    } catch (error) {
      toast.error('Regeneration failed');
    }
    setRegenerating(null);
  };

  if (loading) {
    return (
      <div className="modal-overlay">
        <div className="modal-content">
          <div className="loading-spinner"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="message-preview-panel" onClick={(e) => e.stopPropagation()}>
        <div className="panel-header">
          <div>
            <h3>📨 Message Preview: {lead.name}</h3>
            <p style={{ color: '#a0a0b0' }}>{lead.title} at {lead.company}</p>
          </div>
          <button onClick={onClose} className="close-btn">✕</button>
        </div>

        <div className="panel-content">
          {messages.map((msg, index) => (
            <div key={index} className="message-preview-card">
              <div className="step-header">
                <h4>Step {msg.step_number}: {msg.step_name}</h4>
                <div className="score-display">
                  <span className="score-badge" title="Total AI Score">
                    🎯 {msg.total_score}/10
                  </span>
                </div>
              </div>

              {msg.subject && (
                <div className="message-subject">
                  <strong>Subject:</strong> {msg.subject}
                </div>
              )}

              <div className="message-body">
                {msg.body}
              </div>

              <div className="message-scores">
                <div className="score-item">
                  <span>Clarity:</span>
                  <span className="score-value">{msg.clarity_score}/10</span>
                </div>
                <div className="score-item">
                  <span>Personalization:</span>
                  <span className="score-value">{msg.personalization_score}/10</span>
                </div>
                <div className="score-item">
                  <span>Relevance:</span>
                  <span className="score-value">{msg.relevance_score}/10</span>
                </div>
              </div>

              {msg.reasoning && (
                <div className="message-reasoning">
                  <strong>Strategy:</strong> {msg.reasoning}
                </div>
              )}

              <button
                onClick={() => regenerateStep(msg.step_number)}
                className="btn-secondary"
                disabled={regenerating === msg.step_number}
                style={{ marginTop: '1rem' }}
              >
                {regenerating === msg.step_number ? '🔄 Regenerating...' : '🔄 Regenerate'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
