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

export const AIAgentProfileManager = ({ onClose, onSelect, campaignId }) => {
  const [profiles, setProfiles] = useState([]);
  const [creating, setCreating] = useState(false);
  const [newProfile, setNewProfile] = useState({
    name: '',
    tone: 'professional',
    style: 'medium',
    focus: 'value_driven',
    avoid_words: '',
    brand_personality: ''
  });

  useEffect(() => {
    fetchProfiles();
  }, []);

  const fetchProfiles = async () => {
    try {
      const response = await api.get('/ai-agent-profiles');
      setProfiles(response.data);
    } catch (error) {
      console.error('Failed to load profiles');
    }
  };

  const handleCreate = async () => {
    try {
      const profileData = {
        ...newProfile,
        avoid_words: newProfile.avoid_words.split(',').map(w => w.trim()).filter(Boolean)
      };
      
      const response = await api.post('/ai-agent-profiles', profileData);
      toast.success('Agent profile created!');
      setCreating(false);
      fetchProfiles();
      
      if (onSelect) {
        onSelect(response.data.id);
      }
    } catch (error) {
      toast.error('Failed to create profile');
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
        <h3>🧠 AI Agent Profiles</h3>
        
        {!creating ? (
          <div>
            <div className="profiles-list" style={{ marginBottom: '2rem' }}>
              {profiles.map((profile) => (
                <div key={profile.id} className="agent-profile-card" onClick={() => onSelect && onSelect(profile.id)}>
                  <h4>{profile.name}</h4>
                  <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
                    <span className="badge">{profile.tone}</span>
                    <span className="badge">{profile.style}</span>
                    <span className="badge">{profile.focus}</span>
                  </div>
                  <p style={{ color: '#a0a0b0', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                    {profile.brand_personality || 'No personality set'}
                  </p>
                </div>
              ))}
            </div>
            
            <button onClick={() => setCreating(true)} className="btn-primary">
              + Create New Agent Profile
            </button>
          </div>
        ) : (
          <div className="create-profile-form">
            <div className="form-group">
              <label>Agent Name</label>
              <input
                type="text"
                placeholder="E.g., Professional B2B Sales Agent"
                value={newProfile.name}
                onChange={(e) => setNewProfile({ ...newProfile, name: e.target.value })}
                className="input"
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Tone</label>
                <select
                  value={newProfile.tone}
                  onChange={(e) => setNewProfile({ ...newProfile, tone: e.target.value })}
                  className="input"
                >
                  <option value="friendly">Friendly</option>
                  <option value="professional">Professional</option>
                  <option value="energetic">Energetic</option>
                  <option value="persuasive">Persuasive</option>
                </select>
              </div>

              <div className="form-group">
                <label>Style</label>
                <select
                  value={newProfile.style}
                  onChange={(e) => setNewProfile({ ...newProfile, style: e.target.value })}
                  className="input"
                >
                  <option value="short">Short (50-100 words)</option>
                  <option value="medium">Medium (100-150 words)</option>
                  <option value="long">Long (150-200 words)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Focus</label>
                <select
                  value={newProfile.focus}
                  onChange={(e) => setNewProfile({ ...newProfile, focus: e.target.value })}
                  className="input"
                >
                  <option value="relationship_building">Relationship Building</option>
                  <option value="value_driven">Value-Driven</option>
                  <option value="insightful">Insightful</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label>Avoid Words (comma-separated)</label>
              <input
                type="text"
                placeholder="E.g., synergy, leverage, cutting-edge"
                value={newProfile.avoid_words}
                onChange={(e) => setNewProfile({ ...newProfile, avoid_words: e.target.value })}
                className="input"
              />
            </div>

            <div className="form-group">
              <label>Brand Personality</label>
              <textarea
                placeholder="Describe your brand's personality and how you want to come across..."
                value={newProfile.brand_personality}
                onChange={(e) => setNewProfile({ ...newProfile, brand_personality: e.target.value })}
                className="input"
                rows="3"
              />
            </div>

            <div className="form-actions">
              <button onClick={handleCreate} className="btn-primary">Create Profile</button>
              <button onClick={() => setCreating(false)} className="btn-secondary">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
