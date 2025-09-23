// src/App.js
import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = 'http://localhost:8001';

// Helper function to create wave input components
function WaveInput({ type = "text", value, onChange, placeholder, required = false, className = "" }) {
  const labelText = placeholder || "Input";
  const inputId = `input-${Math.random().toString(36).substr(2, 9)}`;
  
  return (
    <div className={`wave-group ${className}`}>
      <input
        id={inputId}
        required={required}
        type={type}
        className="input"
        value={value}
        onChange={onChange}
      />
      <span className="bar"></span>
      <label className="label" htmlFor={inputId}>
        {labelText.split('').map((char, index) => (
          <span key={index} className="label-char" style={{'--index': index}}>
            {char}
          </span>
        ))}
      </label>
    </div>
  );
}

// Helper function to create wave textarea components
function WaveTextarea({ value, onChange, placeholder, required = false, className = "" }) {
  const labelText = placeholder || "Textarea";
  const inputId = `textarea-${Math.random().toString(36).substr(2, 9)}`;
  
  return (
    <div className={`wave-group ${className}`}>
      <textarea
        id={inputId}
        required={required}
        className="input"
        value={value}
        onChange={onChange}
        rows="3"
      />
      <span className="bar"></span>
      <label className="label" htmlFor={inputId}>
        {labelText.split('').map((char, index) => (
          <span key={index} className="label-char" style={{'--index': index}}>
            {char}
          </span>
        ))}
      </label>
    </div>
  );
}

// Helper function to create styled file upload components
function FileUpload({ onChange, accept = ".csv", required = false, className = "" }) {
  const inputId = `file-${Math.random().toString(36).substr(2, 9)}`;
  
  return (
    <form className={`file-upload-form ${className}`}>
      <label htmlFor={inputId} className="file-upload-label">
        <div className="file-upload-design">
          <svg viewBox="0 0 640 512" height="1em">
            <path
              d="M144 480C64.5 480 0 415.5 0 336c0-62.8 40.2-116.2 96.2-135.9c-.1-2.7-.2-5.4-.2-8.1c0-88.4 71.6-160 160-160c59.3 0 111 32.2 138.7 80.2C409.9 102 428.3 96 448 96c53 0 96 43 96 96c0 12.2-2.3 23.8-6.4 34.6C596 238.4 640 290.1 640 352c0 70.7-57.3 128-128 128H144zm79-217c-9.4 9.4-9.4 24.6 0 33.9s24.6 9.4 33.9 0l39-39V392c0 13.3 10.7 24 24 24s24-10.7 24-24V257.9l39 39c9.4 9.4 24.6 9.4 33.9 0s9.4-24.6 0-33.9l-80-80c-9.4-9.4-24.6-9.4-33.9 0l-80 80z"
            ></path>
          </svg>
          <p>Drag and Drop</p>
          <p>or</p>
          <span className="browse-button">Browse file</span>
        </div>
        <input 
          id={inputId} 
          type="file" 
          onChange={onChange}
          accept={accept}
          required={required}
        />
      </label>
    </form>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [apiKey, setApiKey] = useState(localStorage.getItem('apiKey'));
  const [currentPage, setCurrentPage] = useState('login');

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser && apiKey) {
      setUser(JSON.parse(savedUser));
      setCurrentPage('dashboard');
    }
  }, [apiKey]);

  const logout = () => {
    localStorage.removeItem('user');
    localStorage.removeItem('apiKey');
    setUser(null);
    setApiKey(null);
    setCurrentPage('login');
  };

  if (!user) {
    return <LoginPage setUser={setUser} setApiKey={setApiKey} setCurrentPage={setCurrentPage} />;
  }

  return (
    <div className="App">
      <header className="header">
        <h1>E2I Data Platform</h1>
        <div className="user-info">
          <span>{user.username} ({user.role})</span>
          <button onClick={logout}>Logout</button>
        </div>
      </header>

      <nav className="nav">
        <button 
          className={currentPage === 'dashboard' ? 'active' : ''}
          onClick={() => setCurrentPage('dashboard')}
        >
          Dashboard
        </button>
        <button 
          className={currentPage === 'upload' ? 'active' : ''}
          onClick={() => setCurrentPage('upload')}
        >
          Upload
        </button>
        {user.role === 'admin' && (
          <button 
            className={currentPage === 'templates' ? 'active' : ''}
            onClick={() => setCurrentPage('templates')}
          >
            Templates
          </button>
        )}
      </nav>

      <main className="main">
        {currentPage === 'dashboard' && <Dashboard user={user} />}
        {currentPage === 'upload' && <UploadPage apiKey={apiKey} />}
        {currentPage === 'templates' && user.role === 'admin' && <TemplatesPage apiKey={apiKey} />}
      </main>
    </div>
  );
}

// Login Component
function LoginPage({ setUser, setApiKey, setCurrentPage }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      
      // Store user and API key
      localStorage.setItem('user', JSON.stringify(data.user || { username, role: data.role || 'user' }));
      localStorage.setItem('apiKey', data.apiKey || data.api_key);
      
      setUser(data.user || { username, role: data.role || 'user' });
      setApiKey(data.apiKey || data.api_key);
      setCurrentPage('dashboard');
    } catch (err) {
      setError('Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <form onSubmit={handleLogin} className="login-form">
        <h2>Login to E2I Platform</h2>
        {error && <div className="error">{error}</div>}
        
        <WaveInput
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Username"
          required
        />
        
        <WaveInput
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          required
        />
        
        <button type="submit" disabled={loading}>
          {loading ? (
            <>
              <div className="loading-spinner"></div>
              Logging in...
            </>
          ) : (
            'Login'
          )}
        </button>
        
        <div className="demo-accounts">
          <p>Demo accounts:</p>
          <p>Admin: safira / 123</p>
          <p>User: areyan / 123</p>
        </div>
      </form>
    </div>
  );
}

// Dashboard Component
function Dashboard({ user }) {
  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h2>Welcome back, {user.username}!</h2>
        <p className="dashboard-subtitle">Manage your data warehouse operations</p>
      </div>
      
      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-content">
            <h3>24</h3>
            <p>Files Processed Today</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-content">
            <h3>98.5%</h3>
            <p>Success Rate</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⚡</div>
          <div className="stat-content">
            <h3>2.3s</h3>
            <p>Avg Processing Time</p>
          </div>
        </div>
        {user.role === 'admin' && (
          <div className="stat-card">
            <div className="stat-icon">🔧</div>
            <div className="stat-content">
              <h3>12</h3>
              <p>Active Templates</p>
            </div>
          </div>
        )}
      </div>
      
      <div className="dashboard-cards">
        <div className="dashboard-card" style={{cursor: 'pointer'}} onClick={() => window.location.reload()}>
          <div className="dashboard-card-icon upload">📤</div>
          <h3>Upload Data</h3>
          <p>Upload CSV files for processing and transformation</p>
        </div>
        {user.role === 'admin' && (
          <div className="dashboard-card" style={{cursor: 'pointer'}} onClick={() => window.location.reload()}>
            <div className="dashboard-card-icon templates">📋</div>
            <h3>Manage Templates</h3>
            <p>Create and manage data processing templates</p>
          </div>
        )}
        <div className="dashboard-card" style={{cursor: 'pointer'}} onClick={() => window.location.reload()}>
          <div className="dashboard-card-icon analytics">📈</div>
          <h3>View Analytics</h3>
          <p>Monitor processing performance and data insights</p>
        </div>
      </div>
    </div>
  );
}

// Upload Page Component
function UploadPage({ apiKey }) {
  const [file, setFile] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [uploadedFile, setUploadedFile] = useState(null);
  const [step, setStep] = useState('upload'); // upload, template, mapping
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchTemplates();
  }, []);

const fetchTemplates = async () => {
  try {
    setLoading(true);
    
    const response = await fetch(`${API_BASE}/templates/`, {
      headers: { 'X-API-Key': apiKey }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch templates: ${response.status}`);
    }
    
    const data = await response.json();
    const templatesList = data.templates || [];
    
    // Filter for active templates only
    const activeTemplates = templatesList.filter(t => t.status === 'active');
    setTemplates(activeTemplates);
    
  } catch (err) {
    console.error('Templates fetch error:', err);
    setTemplates([]);
    setMessage('Failed to fetch templates: ' + err.message);
  } finally {
    setLoading(false);
  }
};

  const handleFileUpload = async (e) => {
  console.log('=== FILE UPLOAD STARTING ===');
  e.preventDefault();
  if (!file) return;

  setLoading(true);
  try {
    console.log('Uploading file:', file.name);
    
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/ingest/upload`, {
      method: 'POST',
      headers: { 'X-API-Key': apiKey },
      body: formData
    });

    console.log('Upload response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Upload failed:', errorText);
      throw new Error('Upload failed: ' + response.status);
    }

    const data = await response.json();
    console.log('=== UPLOAD RESPONSE DATA ===');
    console.log('Full response:', data);
    console.log('Available keys:', Object.keys(data));
    
    // Extract the upload ID
    const extractedUploadId = data.uploadId || data.id || data.upload_id || data.file_id || data.uuid;
    console.log('Extracted uploadId:', extractedUploadId);
    
    if (!extractedUploadId) {
      console.error('No upload ID found in response!');
      throw new Error('No upload ID received from server');
    }
    
    // CORRECT: Use setUploadedFile, not setUploadId
    setUploadedFile({
      id: extractedUploadId,
      file_name: data.fileName || file.name,
      ...data
    });
    
    setStep('template');
    setMessage('File uploaded successfully!');
    console.log('Upload successful, moving to template step');
    
    // Refresh templates list
    fetchTemplates();
  } catch (err) {
    console.error('Upload error:', err);
    setMessage('Upload failed: ' + err.message);
  } finally {
    setLoading(false);
  }
};

  const handleTemplateSelect = async () => {
    if (!selectedTemplate || !uploadedFile) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/ingest/uploads/${uploadedFile.id}/select-template`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ template_id: selectedTemplate })
      });

      if (!response.ok) throw new Error('Template selection failed');

      setStep('mapping');
      setMessage('Template selected successfully!');
    } catch (err) {
      setMessage('Template selection failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-page">
      <h2>Upload Data</h2>
      
      {message && <div className={message.includes('failed') ? 'error' : 'success'}>{message}</div>}
      
      {step === 'upload' && (
        <div className="upload-step">
          <h3>Upload Data File</h3>
          <form onSubmit={handleFileUpload}>
            <FileUpload
              onChange={(e) => setFile(e.target.files[0])}
              accept=".csv"
              required
            />
            <button type="submit" disabled={loading || !file}>
              {loading ? (
                <>
                  <div className="loading-spinner"></div>
                  Uploading...
                </>
              ) : (
                'Upload File'
              )}
            </button>
          </form>
        </div>
      )}

      {step === 'template' && (
        <div className="template-step">
          <h3>Select Template</h3>
          <p>File: {uploadedFile?.file_name}</p>
          
          {templates.length === 0 ? (
            <div>
              <p>No active templates available.</p>
              <div className="actions">
                <button onClick={() => setStep('upload')} className="secondary">
                  Back to Upload
                </button>
                <button onClick={fetchTemplates} className="secondary">
                  Retry Fetch Templates
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div className="form-group">
                <label>Choose template:</label>
                <select 
                  value={selectedTemplate} 
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                >
                  <option value="">Select a template...</option>
                  {templates.map(template => (
                    <option key={template.id} value={template.id}>
                      {template.name} - {template.target_table}
                    </option>
                  ))}
                </select>
              </div>
              <div className="actions">
                <button onClick={() => setStep('upload')} className="secondary">
                  Back to Upload
                </button>
                <button 
                  onClick={handleTemplateSelect} 
                  disabled={loading || !selectedTemplate}
                >
                  {loading ? 'Selecting...' : 'Continue'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {step === 'mapping' && uploadedFile?.id && selectedTemplate && (
        <ColumnMapping
          uploadId={uploadedFile.id}
          templateId={selectedTemplate}
          apiKey={apiKey}
          onComplete={() => {
            setStep('upload');
            setFile(null);
            setUploadedFile(null);
            setSelectedTemplate('');
            setMessage('Processing started successfully!');
          }}
          onBack={() => setStep('template')}
        />
      )}
    </div>
  );
}

// Column Mapping Component
function ColumnMapping({ uploadId, templateId, apiKey, onComplete, onBack }) {
  const [template, setTemplate] = useState(null);
  const [csvColumns, setCsvColumns] = useState([]);
  const [mappings, setMappings] = useState({});
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (templateId && uploadId) {
      fetchTemplateDetails();
    }
  }, [templateId, uploadId]);

  const fetchTemplateDetails = async () => {
    console.log('Fetching template details for:', { templateId, uploadId });
    
    try {
      // Fetch template details using user-accessible endpoint
      const response = await fetch(`${API_BASE}/templates/${templateId}/details`, {
        headers: { 'X-API-Key': apiKey }
      });
      
      if (!response.ok) {
        throw new Error(`Template fetch failed: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Template data loaded:', data);
      setTemplate(data);
      
      // Get actual CSV columns from the uploaded file using preview endpoint
      try {
        const uploadResponse = await fetch(`${API_BASE}/ingest/uploads/${uploadId}/preview`, {
          headers: { 'X-API-Key': apiKey }
        });
        
        if (uploadResponse.ok) {
          const previewData = await uploadResponse.json();
          console.log('CSV headers from uploaded file:', previewData.headers);
          setCsvColumns(previewData.headers || []);
        } else {
          console.error('Upload preview failed:', uploadResponse.status, uploadResponse.statusText);
          setCsvColumns([]);
        }
      } catch (err) {
        console.error('Failed to fetch CSV headers:', err);
        setCsvColumns([]);
      }
    } catch (err) {
      console.error('Template fetch error:', err);
      setMessage('Failed to load template: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMapping = (columnId, csvColumn) => {
    setMappings(prev => ({
      ...prev,
      [columnId]: csvColumn
    }));
  };

  const handleSubmit = async () => {
    const requiredColumns = template.columns?.filter(col => col.is_required) || [];
  const unmappedRequired = [];

  requiredColumns.forEach(column => {
    if (column.merged_from_columns && column.merged_from_columns.length > 0) {
      // Check merged columns - all merge sources must be mapped
      const allMergesMapped = column.merged_from_columns.every((_, mergeIndex) => {
        const mappingKey = `${column.id}_${mergeIndex}`;
        return mappings[mappingKey] && mappings[mappingKey].trim() !== '';
      });
      
      if (!allMergesMapped) {
        unmappedRequired.push(column.display_name || column.name);
      }
    } else {
      // Check regular columns
      if (!mappings[column.id] || mappings[column.id].trim() === '') {
        unmappedRequired.push(column.display_name || column.name);
      }
    }
  });

  if (unmappedRequired.length > 0) {
    setMessage(`Please map all required fields: ${unmappedRequired.join(', ')}`);
    return; // Stop submission
  }
    setProcessing(true);
    setMessage('');

    try {
      const columnMappings = [];
      
      Object.entries(mappings).forEach(([key, source]) => {
        if (source) {
          if (key.includes('_')) {
            // Handle merged column mapping
            const [columnId, mergeIndex] = key.split('_');
            const existingMapping = columnMappings.find(m => m.target_column_id === columnId);
            
            if (existingMapping) {
              if (!existingMapping.merged_sources) {
                existingMapping.merged_sources = [];
              }
              // Ensure the array is large enough and set the source at the correct index
              const index = parseInt(mergeIndex);
              while (existingMapping.merged_sources.length <= index) {
                existingMapping.merged_sources.push(null);
              }
              existingMapping.merged_sources[index] = source;
            } else {
              // Create new mapping with proper array structure
              const index = parseInt(mergeIndex);
              const mergedSources = [];
              while (mergedSources.length <= index) {
                mergedSources.push(null);
              }
              mergedSources[index] = source;
              
              columnMappings.push({
                target_column_id: columnId,
                merged_sources: mergedSources
              });
            }
          } else {
            // Handle regular column mapping
            columnMappings.push({
              source,
              target_column_id: key
            });
          }
        }
      });

      console.log('Submitting column mappings:', columnMappings);

      const response = await fetch(`${API_BASE}/ingest/uploads/${uploadId}/mappings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify({ mappings: columnMappings })
      });

      if (!response.ok) throw new Error('Mapping creation failed');

      onComplete();
    } catch (err) {
      setMessage('Failed to create mappings: ' + err.message);
    } finally {
      setProcessing(false);
    }
  };

  if (loading) return <div>Loading template details...</div>;
  if (!template) return <div>Failed to load template: {message}</div>;

  return (
    <div className="column-mapping">
      <h3>Map Columns</h3>
      <p>Map your CSV columns to template columns:</p>
      
      {message && <div className="error">{message}</div>}
      
      <div className="mappings">
        {template.columns?.map(column => (
          <div key={column.id} className="mapping-row">
            <div className="column-info">
              <strong>{column.display_name || column.name}</strong>
              {column.is_required && <span className="required">*</span>}
              <br />
              <small>{column.data_type} | {column.processing_type}</small>
              {column.merged_from_columns && column.merged_from_columns.length > 0 && (
                <div style={{marginTop: '0.5rem', fontSize: '0.75rem', color: '#666'}}>
                  Merges: {column.merged_from_columns.join(', ')}
                </div>
              )}
            </div>
            
            <div style={{display: 'flex', flexDirection: 'column', gap: '0.5rem'}}>
              {/* FIXED: Show multiple dropdowns for merged columns */}
              {column.merged_from_columns && column.merged_from_columns.length > 0 ? (
                // Multiple dropdowns for merged columns
                column.merged_from_columns.map((mergeCol, mergeIndex) => (
                  <div key={`${column.id}-${mergeIndex}`}>
                    <label style={{fontSize: '0.75rem', color: '#666'}}>
                      Map "{mergeCol}":
                    </label>
                    <select 
                      value={mappings[`${column.id}_${mergeIndex}`] || ''} 
                      onChange={(e) => handleMapping(`${column.id}_${mergeIndex}`, e.target.value)}
                    >
                      <option value="">Select CSV column for {mergeCol}...</option>
                      {csvColumns.map(csvCol => (
                        <option key={csvCol} value={csvCol}>{csvCol}</option>
                      ))}
                    </select>
                  </div>
                ))
              ) : (
                // Single dropdown for regular columns
                <select 
                  value={mappings[column.id] || ''} 
                  onChange={(e) => handleMapping(column.id, e.target.value)}
                >
                  <option value="">Select CSV column...</option>
                  {csvColumns.map(csvCol => (
                    <option key={csvCol} value={csvCol}>{csvCol}</option>
                  ))}
                </select>
              )}
            </div>
          </div>
        ))}
      </div>
      
      <div className="actions">
        <button onClick={onBack} className="secondary">Back</button>
        <button 
    onClick={handleSubmit} 
    disabled={processing || (() => {
      // Check if any required fields are unmapped
      const requiredColumns = template.columns?.filter(col => col.is_required) || [];
      return requiredColumns.some(column => {
        if (column.merged_from_columns && column.merged_from_columns.length > 0) {
          // Check merged columns
          return column.merged_from_columns.some((_, mergeIndex) => {
            const mappingKey = `${column.id}_${mergeIndex}`;
            return !mappings[mappingKey] || mappings[mappingKey].trim() === '';
          });
        } else {
          // Check regular columns
          return !mappings[column.id] || mappings[column.id].trim() === '';
        }
      });
    })()}
  >
    {processing ? 'Processing...' : 'Start Processing'}
  </button>
      </div>
    </div>
  );
}

// Templates Page Component
function TemplatesPage({ apiKey }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
  try {
    setLoading(true);
    
    const response = await fetch(`${API_BASE}/templates/`, {
      headers: { 'X-API-Key': apiKey }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch templates: ${response.status}`);
    }
    
    const data = await response.json();
    const templatesList = data.templates || [];
    
    // Show all templates (active, draft, etc.) for admin management
    setTemplates(templatesList);
    
  } catch (err) {
    console.error('Templates fetch error:', err);
    setTemplates([]);
    setMessage('Failed to fetch templates: ' + err.message);
  } finally {
    setLoading(false);
  }
};

  const handleActivate = async (templateId) => {
    try {
      console.log('Activating template:', templateId);
      
      const response = await fetch(`${API_BASE}/templates/${templateId}/activate`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey }
      });
      
      console.log('Activate response:', response.status);
      
      if (response.ok) {
        setMessage('Template activated successfully');
        fetchTemplates();
      } else {
        const errorText = await response.text();
        console.error('Activate failed:', errorText);
        setMessage('Failed to activate template: ' + response.status);
      }
    } catch (err) {
      console.error('Activate error:', err);
      setMessage('Failed to activate template: ' + err.message);
    }
  };

  const handleDeactivate = async (templateId) => {
  try {
    console.log('Deactivating template:', templateId);
    
    const response = await fetch(`${API_BASE}/templates/${templateId}/deactivate`, {
      method: 'POST',
      headers: { 'X-API-Key': apiKey }
    });
    
    console.log('Deactivate response:', response.status);
    
    if (response.ok) {
      setMessage('Template deactivated successfully');
      fetchTemplates(); // Refresh the list to update status
    } else {
      const errorText = await response.text();
      console.error('Deactivate failed:', errorText);
      setMessage('Failed to deactivate template: ' + response.status);
    }
  } catch (err) {
    console.error('Deactivate error:', err);
    setMessage('Failed to deactivate template: ' + err.message);
  }
};

const handleEdit = async (templateId) => {
    try {
      console.log('Fetching template for edit:', templateId);
      
      const response = await fetch(`${API_BASE}/templates/${templateId}`, {
        headers: { 'X-API-Key': apiKey }
      });
      
      if (response.ok) {
        const templateData = await response.json();
        console.log('Template data for edit:', templateData);
        setEditingTemplate(templateData);
        setShowEditForm(true);
        setShowCreateForm(false); // Hide create form if open
      } else {
        setMessage('Failed to fetch template for editing');
      }
    } catch (err) {
      console.error('Edit fetch error:', err);
      setMessage('Failed to fetch template for editing');
    }
  };

  const handleDelete = async (templateId, templateName) => {
    if (!window.confirm(`Delete "${templateName}"?`)) return;

    try {
      console.log('Deleting template:', templateId);
      
      const response = await fetch(`${API_BASE}/templates/${templateId}/delete`, {
        method: 'DELETE',
        headers: { 'X-API-Key': apiKey }
      });
      
      console.log('Delete response:', response.status);
      
      if (response.ok) {
        setMessage('Template deleted successfully');
        fetchTemplates();
      } else {
        const errorText = await response.text();
        console.error('Delete failed:', errorText);
        setMessage('Failed to delete template: ' + response.status);
      }
    } catch (err) {
      console.error('Delete error:', err);
      setMessage('Failed to delete template: ' + err.message);
    }
  };

  if (loading) return <div>Loading templates...</div>;

  return (
    <div className="templates-page">
      <div className="templates-header">
        <h2>Templates</h2>
        <button onClick={() => {
          console.log('Create template button clicked');
          console.log('Current showCreateForm state:', showCreateForm);
          setShowCreateForm(!showCreateForm);
          console.log('Setting showCreateForm to:', !showCreateForm);
        }}>
          {showCreateForm ? 'Cancel' : 'Create Template'}
        </button>
      </div>
      
      {message && <div className={message.includes('Failed') ? 'error' : 'success'}>{message}</div>}
      
      {showCreateForm && (
        <CreateTemplateForm 
          apiKey={apiKey} 
          onSuccess={() => {
            setShowCreateForm(false);
            fetchTemplates();
            setMessage('Template created successfully');
          }}
        />
      )}

      {/* NEW: Add edit form */}
      {showEditForm && editingTemplate && (
        <EditTemplateForm 
          apiKey={apiKey}
          template={editingTemplate}
          onSuccess={() => {
            setShowEditForm(false);
            setEditingTemplate(null);
            fetchTemplates();
            setMessage('Template updated successfully');
          }}
          onCancel={() => {
            setShowEditForm(false);
            setEditingTemplate(null);
          }}
        />
      )}
      
      <div className="templates-list">
        {!Array.isArray(templates) ? (
          <div className="error">
            <p>Error: Templates data is not in expected format</p>
            <p>Type: {typeof templates}</p>
            <p>Value: {JSON.stringify(templates)}</p>
          </div>
        ) : templates.length === 0 ? (
          <p>No templates found.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Target Table</th>
                <th>Status</th>
                <th>Columns</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
  {templates.map(template => (
    <tr key={template.id}>
      <td>
        <strong>{template.name}</strong>
        <br />
        <small>{template.description}</small>
      </td>
      <td>{template.target_table}</td>
      <td>
        <span className={`status ${template.status || 'unknown'}`}>
          {template.status || 'Unknown'}
        </span>
      </td>
      <td>{template.columns?.length || 0}</td>
      <td>
        {/* DRAFT: Show Activate button */}
        {template.status === 'draft' && (
          <button 
            onClick={() => handleActivate(template.id)}
            className="danger"
            style={{backgroundColor: '#2563eb', marginRight: '0.5rem'}}
          >
            Activate
          </button>
        )}
        
        {/* ACTIVE: Show Deactivate button */}
        {template.status === 'active' && (
          <button 
            onClick={() => handleDeactivate(template.id)}
            className="danger"
            style={{marginRight: '0.5rem'}}
          >
            Deactivate
          </button>
        )}
        
        {/* EDIT: Always show edit button */}
        <button 
          onClick={() => handleEdit(template.id)}
          style={{backgroundColor: '#16a34a', color: 'white', marginRight: '0.5rem'}}
        >
          Edit
        </button>
        
        {/* DELETE: Always show delete button */}
        <button 
          onClick={() => handleDelete(template.id, template.name)}
          className="danger"
        >
          Delete
        </button>
      </td>
    </tr>
  ))}
</tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// Create Template Form
function CreateTemplateForm({ apiKey, onSuccess }) {
  const [file, setFile] = useState(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [targetTable, setTargetTable] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadId, setUploadId] = useState(null);
  const [step, setStep] = useState('upload');

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE}/ingest/upload`, {
        method: 'POST',
        headers: { 'X-API-Key': apiKey },
        body: formData
      });

      if (!response.ok) throw new Error('Upload failed');

      const data = await response.json();
      const receivedUploadId = data.uploadId || data.id || data.upload_id || data.file_id || data.uuid;
      
      if (!receivedUploadId) {
        throw new Error("No upload ID received from the server.");
      }
      
      setUploadId(receivedUploadId);
      setStep('template');

    } catch (err) {
      alert('Upload failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

const handleCreateTemplate = async (e) => {
  console.log('=== CREATE TEMPLATE FUNCTION CALLED ===');
  console.log('Event:', e);
  e.preventDefault();
  
  console.log('Current state:', { uploadId, name, targetTable });
  
  if (!uploadId || !name || !targetTable) {
    console.log('Validation failed:', { uploadId, name, targetTable });
    alert('Missing required fields');
    return;
  }

  console.log('Starting template creation...');
  setLoading(true);
  
  try {
    console.log('Making API request...');
    const response = await fetch(`${API_BASE}/templates/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      },
      body: JSON.stringify({
        upload_id: uploadId,
        name,
        description,
        target_table: targetTable
      })
    });

    console.log('API response:', response);

    if (!response.ok) throw new Error('Template creation failed');

    console.log('Template created successfully');
    onSuccess();
  } catch (err) {
    console.error('Template creation error:', err);
    alert('Template creation failed: ' + err.message);
  } finally {
    setLoading(false);
  }
};

  return (
    <div className="create-template-form">
      <h3>Create New Template</h3>
      
      {step === 'upload' && (
        <form onSubmit={handleFileUpload}>
          <FileUpload
            onChange={(e) => setFile(e.target.files[0])}
            accept=".csv"
            required
          />
          <button type="submit" disabled={loading || !file}>
            {loading ? 'Uploading...' : 'Upload File'}
          </button>
        </form>
      )}
      
      {step === 'template' && (
        <form onSubmit={handleCreateTemplate}>
          <WaveInput
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Template Name"
            required
          />
          <WaveTextarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description"
          />
          <WaveInput
            type="text"
            value={targetTable}
            onChange={(e) => setTargetTable(e.target.value)}
            placeholder="Target Table"
            required
          />
          <button 
  type="submit" 
  disabled={loading}
  onClick={(e) => {
    console.log('=== BUTTON CLICKED ===');
    console.log('Button click event:', e);
    console.log('Form data:', { name, description, targetTable, uploadId });
  }}
>
  {loading ? 'Creating...' : 'Create Template'}
</button>
        </form>
      )}
    </div>
  );
}

// Edit Template Form Component
function EditTemplateForm({ apiKey, template, onSuccess, onCancel }) {
  const [name, setName] = useState(template.name || '');
  const [description, setDescription] = useState(template.description || '');

  // Initialize a state for columns with proper defaults and a parsed merged field
  const [columns, setColumns] = useState(() => {
    return (template.columns || []).map(col => ({
      // Use unique ID to prevent React from re-rendering incorrectly
      id: col.id, 
      name: col.name || '',
      display_name: col.display_name || col.name || '',
      data_type: col.data_type || 'string',
      processing_type: col.processing_type || 'none',
      is_required: Boolean(col.is_required),
      // Store the merged columns as a string for the input field
      merged_from_columns: Array.isArray(col.merged_from_columns) ? col.merged_from_columns.join(', ') : ''
    }));
  });

  const [loading, setLoading] = useState(false);

  const dataTypes = ['string', 'integer', 'float', 'datetime', 'date', 'boolean'];
  const processingTypes = ['none', 'tokenize', 'hash'];

  const handleColumnChange = (index, field, value) => {
    setColumns(prevColumns => {
      const updatedColumns = [...prevColumns];
      
      // Update the state based on the field name
      updatedColumns[index][field] = value;
      
      return updatedColumns;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Prepare the data to be sent to the API
      const updateData = {
        name,
        description,
        columns: columns.map(col => ({
          name: col.name,
          display_name: col.display_name,
          data_type: col.data_type,
          processing_type: col.processing_type,
          is_required: col.is_required,
          // Split the comma-separated string back into an array for the API
          merged_from_columns: col.merged_from_columns ? 
            col.merged_from_columns.split(',').map(s => s.trim()).filter(s => s) : []
        }))
      };

      console.log('Submitting update data:', JSON.stringify(updateData, null, 2));

      const response = await fetch(`${API_BASE}/templates/${template.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey
        },
        body: JSON.stringify(updateData)
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Update failed response:', errorText);
        throw new Error(`Update failed: ${response.status} - ${errorText}`);
      }

      onSuccess();
    } catch (err) {
      console.error('Template update error:', err);
      alert('Template update failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-template-form">
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <h3>Edit Template: {template.name}</h3>
        <button onClick={onCancel} style={{backgroundColor: '#6b7280'}}>
          Cancel
        </button>
      </div>
      
      <form onSubmit={handleSubmit}>
        <WaveInput
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Template Name"
          required
        />
        
        <WaveTextarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Description"
        />

        <h4>Columns Configuration</h4>
        
        {columns.map((column, index) => (
          <div key={column.id || index} style={{
            border: '1px solid #ddd', 
            padding: '1rem', 
            marginBottom: '1rem',
            borderRadius: '4px'
          }}>
            <h5>Column: {column.name}</h5>
            
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem'}}>
              <WaveInput
                type="text"
                value={column.display_name}
                onChange={(e) => handleColumnChange(index, 'display_name', e.target.value)}
                placeholder="Display Name"
              />
              
              <div className="form-group">
                <label>Data Type:</label>
                <select
                  value={column.data_type}
                  onChange={(e) => handleColumnChange(index, 'data_type', e.target.value)}
                >
                  {dataTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>
              
              <div className="form-group">
                <label>Processing Type:</label>
                <select
                  // FIXED: Changed defaultValue to value
                  value={column.processing_type}
                  onChange={(e) => {
                    handleColumnChange(index, 'processing_type', e.target.value);
                  }}
                >
                  {processingTypes.map(type => (
                    <option key={type} value={type}>{type}</option>
                  ))}
                </select>
              </div>
              
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={column.is_required}
                    onChange={(e) => {
                      handleColumnChange(index, 'is_required', e.target.checked);
                    }}
                    style={{marginRight: '0.5rem'}}
                  />
                  Required Field
                </label>
              </div>
            </div>
            
            <div className="form-group">
              <WaveInput
                type="text"
                value={column.merged_from_columns} 
                onChange={(e) => {
                  handleColumnChange(index, 'merged_from_columns', e.target.value);
                }}
                placeholder="Merge From Columns (comma-separated)"
              />
              <small>Enter column names to merge into this column, separated by commas</small>
            </div>
          </div>
        ))}
        
        <div style={{display: 'flex', gap: '1rem', marginTop: '1rem'}}>
          <button type="submit" disabled={loading}>
            {loading ? 'Updating...' : 'Update Template'}
          </button>
          <button type="button" onClick={onCancel} style={{backgroundColor: '#6b7280', color: 'white'}}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

export default App;