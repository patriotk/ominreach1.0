import { useState, useEffect } from 'react';
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

export const AIAgentStudio = () => {
  const [config, setConfig] = useState(null);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [activeStep, setActiveStep] = useState(1);

  useEffect(() => {
    fetchConfig();
    fetchUsage();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await api.get('/ai-agent/config');
      setConfig(response.data);
    } catch (error) {
      toast.error('Failed to load AI config');
    }
    setLoading(false);
  };

  const fetchUsage = async () => {
    try {
      const response = await api.get('/ai-agent/usage?days=30');
      setUsage(response.data);
    } catch (error) {
      console.error('Failed to load usage');
    }
  };

  const saveConfig = async () => {
    try {
      await api.post('/ai-agent/config', config);
      toast.success('AI Agent configuration saved!');
      setEditing(false);
      fetchUsage();
    } catch (error) {
      toast.error('Failed to save configuration');
    }
  };

  if (loading) {
    return <div className="loading-screen"><div className="loading-spinner"></div></div>;
  }

  return (
    <div className="ai-studio">
      <div className="studio-header">
        <div>
          <h1>🤖 AI Agent Studio</h1>
          <p>Configure and monitor AI message generation</p>
        </div>
        <button onClick={() => setEditing(!editing)} className="btn-secondary">
          {editing ? 'Cancel' : '✏️ Edit Configuration'}
        </button>
      </div>

      {/* Usage Dashboard */}
      <div className="usage-dashboard">
        <h3>Usage & Costs (Last 30 Days)</h3>
        <div className="usage-metrics">
          <div className="usage-card">
            <div className="usage-label">Total AI Calls</div>
            <div className="usage-value">{usage?.total_calls || 0}</div>
          </div>
          <div className="usage-card">
            <div className="usage-label">Total Tokens</div>
            <div className="usage-value">{usage?.total_tokens?.toLocaleString() || 0}</div>
          </div>
          <div className="usage-card">
            <div className="usage-label">Estimated Cost</div>
            <div className="usage-value">${usage?.total_cost?.toFixed(4) || '0.00'}</div>
          </div>
        </div>

        {usage?.by_provider && Object.keys(usage.by_provider).length > 0 && (
          <div className="provider-breakdown">
            <h4>By Provider</h4>
            {Object.entries(usage.by_provider).map(([provider, stats]) => (
              <div key={provider} className="provider-stat">
                <strong>{provider}:</strong> {stats.calls} calls, {stats.tokens.toLocaleString()} tokens
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Model Configuration */}
      <div className="model-config-section">
        <h3>Model Configuration</h3>
        <div className="config-grid">
          <div className="config-field">
            <label>Provider</label>
            {editing ? (
              <select
                value={config?.model_provider || 'openai'}
                onChange={(e) => setConfig({ ...config, model_provider: e.target.value })}
                className="input"
              >
                <option value="openai">OpenAI (GPT-5)</option>
                <option value="gemini">Google (Gemini)</option>
              </select>
            ) : (
              <div className="display-value">{config?.model_provider || 'openai'}</div>
            )}
          </div>

          <div className="config-field">
            <label>Model</label>
            {editing ? (
              <input
                type="text"
                value={config?.model_name || 'gpt-5'}
                onChange={(e) => setConfig({ ...config, model_name: e.target.value })}
                className="input"
              />
            ) : (
              <div className="display-value">{config?.model_name || 'gpt-5'}</div>
            )}
          </div>

          <div className="config-field">
            <label>Temperature (0-1)</label>
            {editing ? (
              <input
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={config?.temperature || 0.7}
                onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
                className="input"
              />
            ) : (
              <div className="display-value">{config?.temperature || 0.7}</div>
            )}
            <small style={{ color: '#6b6b7b' }}>Higher = more creative, Lower = more focused</small>
          </div>

          <div className="config-field">
            <label>Max Tokens</label>
            {editing ? (
              <input
                type="number"
                value={config?.max_tokens || 500}
                onChange={(e) => setConfig({ ...config, max_tokens: parseInt(e.target.value) })}
                className="input"
              />
            ) : (
              <div className="display-value">{config?.max_tokens || 500}</div>
            )}
          </div>
        </div>
      </div>

      {/* Step-Specific Prompts */}
      <div className="step-prompts-section">
        <h3>Agent Instructions by Step</h3>
        <div className="step-tabs">
          {[1, 2, 3].map(step => (
            <button
              key={step}
              className={`step-tab ${activeStep === step ? 'active' : ''}`}
              onClick={() => setActiveStep(step)}
            >
              Step {step}
            </button>
          ))}
        </div>

        <div className="step-config">
          <div className="config-field">
            <label>System Prompt (Step {activeStep})</label>
            {editing ? (
              <textarea
                value={config?.[`step_${activeStep}_system_prompt`] || ''}
                onChange={(e) => setConfig({ ...config, [`step_${activeStep}_system_prompt`]: e.target.value })}
                className="input"
                rows="3"
                placeholder="The AI agent's role and expertise..."
              />
            ) : (
              <div className="display-value prompt-display">
                {config?.[`step_${activeStep}_system_prompt`] || 'Not set'}
              </div>
            )}
            <small style={{ color: '#6b6b7b' }}>Defines the AI's role and expertise</small>
          </div>

          <div className="config-field">
            <label>Instructions (Step {activeStep})</label>
            {editing ? (
              <textarea
                value={config?.[`step_${activeStep}_instructions`] || ''}
                onChange={(e) => setConfig({ ...config, [`step_${activeStep}_instructions`]: e.target.value })}
                className="input"
                rows="4"
                placeholder="Specific requirements for this step..."
              />
            ) : (
              <div className="display-value prompt-display">
                {config?.[`step_${activeStep}_instructions`] || 'Not set'}
              </div>
            )}
            <small style={{ color: '#6b6b7b' }}>Specific requirements and constraints</small>
          </div>
        </div>
      </div>

      {editing && (
        <button onClick={saveConfig} className="btn-primary" style={{ marginTop: '2rem' }}>
          💾 Save AI Agent Configuration
        </button>
      )}

      {/* Recent AI Operations */}
      {usage?.logs && usage.logs.length > 0 && (
        <div className="recent-operations">
          <h3>Recent AI Operations</h3>
          <div className="operations-list">
            {usage.logs.map((log, index) => (
              <div key={index} className="operation-item">
                <div className="operation-info">
                  <strong>{log.operation}</strong>
                  <span>{log.provider} / {log.model}</span>
                </div>
                <div className="operation-stats">
                  <span>{log.total_tokens} tokens</span>
                  <span>{new Date(log.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
