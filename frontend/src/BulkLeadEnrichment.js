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

export const BulkLeadEnrichment = ({ leads, onClose, onComplete }) => {
  const [enrichmentData, setEnrichmentData] = useState('');
  const [processing, setProcessing] = useState(false);

  const handleEnrich = async () => {
    setProcessing(true);
    
    try {
      // Parse enrichment data: Name | Company | Title (one per line)
      const lines = enrichmentData.trim().split('\n');
      const updates = [];
      
      for (const line of lines) {
        const parts = line.split('|').map(p => p.trim());
        if (parts.length >= 3) {
          const [name, company, title] = parts;
          
          // Find matching lead by name
          const lead = leads.find(l => 
            l.name.toLowerCase().includes(name.toLowerCase()) ||
            name.toLowerCase().includes(l.name.toLowerCase())
          );
          
          if (lead) {
            updates.push({
              id: lead.id,
              company,
              title
            });
          }
        }
      }

      // Update leads
      for (const update of updates) {
        await api.patch(`/leads/${update.id}`, {
          company: update.company,
          title: update.title,
          persona_status: 'pending'  // Reset to trigger auto-research
        });
      }

      toast.success(`✅ Updated ${updates.length} leads! Auto-research starting...`);
      
      if (onComplete) {
        onComplete();
      }
      
      if (onClose) {
        onClose();
      }
    } catch (error) {
      toast.error('Enrichment failed');
    }
    
    setProcessing(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '700px' }}>
        <h3>🔧 Bulk Enrich Leads</h3>
        
        <p style={{ color: '#a0a0b0', marginBottom: '1rem' }}>
          Add company and title data for leads that are missing it. Format: Name | Company | Title (one per line)
        </p>

        <textarea
          placeholder="Violet Masoud | Microsoft | Senior Product Manager&#10;Vanessa Sherer | Google | Engineering Director&#10;Goli Shariat | Meta | VP of Marketing"
          value={enrichmentData}
          onChange={(e) => setEnrichmentData(e.target.value)}
          className="input"
          rows="12"
          style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}
        />

        <div className="info-banner" style={{ margin: '1rem 0' }}>
          <p><strong>Tip:</strong> Copy your connection names, then add their companies and titles from LinkedIn. Persona research will auto-start when you save!</p>
        </div>

        <div className="form-actions">
          <button 
            onClick={handleEnrich} 
            className="btn-primary"
            disabled={processing || !enrichmentData}
          >
            {processing ? 'Enriching...' : `Enrich ${enrichmentData.split('\n').filter(l => l.includes('|')).length} Leads`}
          </button>
          <button onClick={onClose} className="btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  );
};
