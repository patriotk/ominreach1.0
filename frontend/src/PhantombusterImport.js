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

export const PhantombusterImport = ({ onClose, onImportComplete }) => {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState(null);

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await api.get('/phantombuster/agents');
      setAgents(response.data.agents || []);
    } catch (error) {
      toast.error('Failed to load Phantombuster agents. Check API key in Settings.');
    }
    setLoading(false);
  };

  const handleImport = async (agentId) => {
    setImporting(true);
    setSelectedAgent(agentId);
    
    try {
      const response = await api.post(`/phantombuster/import-leads?agent_id=${agentId}`);
      toast.success(`Imported ${response.data.count} leads!`);
      
      if (onImportComplete) {
        onImportComplete();
      }
      
      if (onClose) {
        onClose();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Import failed');
    }
    
    setImporting(false);
    setSelectedAgent(null);
  };

  if (loading) {
    return (
      <div className=\"modal-overlay\">
        <div className=\"modal-content\">
          <h3>Loading Phantombuster Agents...</h3>
          <div className=\"loading-spinner\"></div>
        </div>
      </div>
    );
  }

  return (
    <div className=\"modal-overlay\" onClick={onClose}>
      <div className=\"modal-content\" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <h3>Import Leads from Phantombuster</h3>
          <button onClick={onClose} className=\"btn-secondary\">✕ Close</button>
        </div>

        {agents.length === 0 ? (
          <div className=\"empty-state\">
            <p>No Phantombuster agents found. Create agents in your Phantombuster dashboard first.</p>
            <a 
              href=\"https://phantombuster.com/dashboard\" 
              target=\"_blank\" 
              rel=\"noopener noreferrer\"
              className=\"btn-primary\"
              style={{ marginTop: '1rem', display: 'inline-block' }}
            >
              Open Phantombuster Dashboard
            </a>
          </div>
        ) : (
          <div className=\"agents-list\">
            {agents.map((agent) => (
              <div key={agent.id} className=\"agent-card\">
                <div className=\"agent-info\">
                  <h4>{agent.name}</h4>
                  <p>{agent.scriptId}</p>
                  <small>Last run: {agent.lastEndMessage || 'Never'}</small>
                </div>
                <button
                  onClick={() => handleImport(agent.id)}
                  className=\"btn-primary\"
                  disabled={importing}
                >
                  {importing && selectedAgent === agent.id ? 'Importing...' : 'Import Leads'}
                </button>
              </div>
            ))}
          </div>
        )}

        <div className=\"info-banner\" style={{ marginTop: '2rem' }}>
          <p><strong>How it works:</strong> Select a Phantombuster agent that has scraped LinkedIn profiles. OmniReach will import the leads with their names, companies, titles, and LinkedIn URLs.</p>
        </div>
      </div>
    </div>
  );
};
