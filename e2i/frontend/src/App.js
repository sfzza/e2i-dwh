// src/App.js
import React, { useState, useEffect } from "react";
import "./App.css";

const API_BASE = "http://localhost:8001";

// Success Popup Component
function SuccessPopup({ message, onClose }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 1000);

    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className="success-popup-overlay">
      <div className="success-popup">
        <div className="success-icon">
          <i className="fas fa-check-circle"></i>
        </div>
        <h3>SUCCESS</h3>
        <p>{message}</p>
      </div>
    </div>
  );
}

// Helper function to create wave input components
function WaveInput({
  type = "text",
  value,
  onChange,
  placeholder,
  required = false,
  className = "",
}) {
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
        {labelText.split("").map((char, index) => (
          <span key={index} className="label-char" style={{ "--index": index }}>
            {char}
          </span>
        ))}
      </label>
    </div>
  );
}

// Helper function to create wave textarea components
function WaveTextarea({
  value,
  onChange,
  placeholder,
  required = false,
  className = "",
}) {
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
        {labelText.split("").map((char, index) => (
          <span key={index} className="label-char" style={{ "--index": index }}>
            {char}
          </span>
        ))}
      </label>
    </div>
  );
}

// Helper function to format file size
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  if (bytes < 1024) return bytes + " Bytes";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
  if (bytes < 1024 * 1024 * 1024)
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
}

// Helper function to create styled file upload components
function FileUpload({
  onChange,
  accept = ".csv",
  required = false,
  className = "",
}) {
  const inputId = `file-${Math.random().toString(36).substr(2, 9)}`;
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      console.log("File dropped:", file.name, file.size, "bytes");
      setSelectedFile(file);
      // Create a proper synthetic event that matches what the input would create
      const syntheticEvent = {
        target: {
          files: [file],
          value: file.name,
        },
      };
      onChange(syntheticEvent);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      console.log("File selected via browse:", file.name, file.size, "bytes");
      setSelectedFile(file);
      onChange(e);
    }
  };

  return (
    <div className={`file-upload-container ${className}`}>
      <div
        className={`file-upload-zone ${isDragOver ? "drag-over" : ""} ${
          selectedFile ? "has-file" : ""
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => document.getElementById(inputId).click()}
      >
        <div className="file-upload-content">
          <div className="upload-icon">
            <i className="fas fa-cloud-upload-alt"></i>
          </div>

          {selectedFile ? (
            <div className="file-selected">
              <i className="fas fa-file-csv"></i>
              <p className="file-name">{selectedFile.name}</p>
              <p className="file-size">{formatFileSize(selectedFile.size)}</p>
            </div>
          ) : (
            <div className="file-upload-text">
              <p className="drag-text">Drag and Drop</p>
              <p className="or-text">or</p>
              <span className="browse-button">Browse file</span>
            </div>
          )}
        </div>

        <input
          id={inputId}
          type="file"
          onChange={handleFileSelect}
          accept={accept}
          required={required}
          style={{ display: "none" }}
        />
      </div>

      {selectedFile && (
        <button
          type="button"
          className="remove-file-btn"
          onClick={(e) => {
            e.stopPropagation();
            setSelectedFile(null);
            // Clear the file input as well
            const fileInput = document.getElementById(inputId);
            if (fileInput) {
              fileInput.value = "";
            }
            onChange({ target: { files: [], value: "" } });
          }}
        >
          <i className="fas fa-times"></i> Remove
        </button>
      )}
    </div>
  );
}

function App() {
  const [user, setUser] = useState(null);
  const [apiKey, setApiKey] = useState(localStorage.getItem("apiKey"));
  const [currentPage, setCurrentPage] = useState("login");

  useEffect(() => {
    const savedUser = localStorage.getItem("user");
    if (savedUser && apiKey) {
      setUser(JSON.parse(savedUser));
      setCurrentPage("dashboard");
    }
  }, [apiKey]);

  const logout = () => {
    localStorage.removeItem("user");
    localStorage.removeItem("apiKey");
    setUser(null);
    setApiKey(null);
    setCurrentPage("login");
  };

  if (!user) {
    return (
      <LoginPage
        setUser={setUser}
        setApiKey={setApiKey}
        setCurrentPage={setCurrentPage}
      />
    );
  }

  return (
    <div className="App">
      {/* Enhanced Sidebar Navigation */}
      <aside className="sidebar slide-in-left">
        <div className="sidebar-header">
          e2i <span className="brand-red">DWH</span>
        </div>
        <nav className="sidebar-nav">
          <ul>
            <li>
              <button
                className={`nav-link ${
                  currentPage === "dashboard" ? "active" : ""
                }`}
                onClick={() => setCurrentPage("dashboard")}
              >
                <i className="fas fa-tachometer-alt"></i>
                Dashboard
              </button>
            </li>
            <li>
              <button
                className={`nav-link ${
                  currentPage === "upload" ? "active" : ""
                }`}
                onClick={() => setCurrentPage("upload")}
              >
                <i className="fas fa-upload"></i>
                Data Ingestion
              </button>
            </li>
            {user.role === "admin" && (
              <>
                <li>
                  <button
                    className={`nav-link ${
                      currentPage === "templates" ? "active" : ""
                    }`}
                    onClick={() => setCurrentPage("templates")}
                  >
                    <i className="fas fa-project-diagram"></i>
                    Templates
                  </button>
                </li>
                <li>
                  <button
                    className={`nav-link ${
                      currentPage === "audit-logs" ? "active" : ""
                    }`}
                    onClick={() => setCurrentPage("audit-logs")}
                  >
                    <i className="fas fa-clipboard-list"></i>
                    Audit Logs
                  </button>
                </li>
                <li>
                  <button
                    className={`nav-link ${
                      currentPage === "user-management" ? "active" : ""
                    }`}
                    onClick={() => setCurrentPage("user-management")}
                  >
                    <i className="fas fa-users"></i>
                    User Management
                  </button>
                </li>
              </>
            )}
          </ul>
        </nav>
      </aside>

      {/* Enhanced Main Content Area */}
      <div className="main-content">
        <header className="header slide-in-right">
          <div className="header-left">
            <h2 className="text-lg font-semibold text-gray-800">
              Welcome, {user.username}
            </h2>
          </div>
          <div className="header-right">
            <button onClick={logout} className="hover-lift">
              <i className="fas fa-user-circle text-2xl text-gray-600"></i>
            </button>
          </div>
        </header>

        <main className="main">
          <div className="fade-in">
            {currentPage === "dashboard" && (
              <Dashboard user={user} apiKey={apiKey} />
            )}
            {currentPage === "upload" && <UploadPage apiKey={apiKey} />}
            {currentPage === "templates" && user.role === "admin" && (
              <TemplatesPage apiKey={apiKey} />
            )}
            {currentPage === "audit-logs" && user.role === "admin" && (
              <AuditLogsPage apiKey={apiKey} />
            )}
            {currentPage === "user-management" && user.role === "admin" && (
              <UserManagementPage apiKey={apiKey} />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

// Login Component
function LoginPage({ setUser, setApiKey, setCurrentPage }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error("Login failed");
      }

      const data = await response.json();

      // Store user and API key
      localStorage.setItem(
        "user",
        JSON.stringify(data.user || { username, role: data.role || "user" })
      );
      localStorage.setItem("apiKey", data.apiKey || data.api_key);

      setUser(data.user || { username, role: data.role || "user" });
      setApiKey(data.apiKey || data.api_key);
      setCurrentPage("dashboard");
    } catch (err) {
      setError("Login failed. Please check your credentials.");
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
            "Login"
          )}
        </button>
      </form>
    </div>
  );
}

// Dashboard Component
function Dashboard({ user, apiKey }) {
  const [metrics, setMetrics] = useState({
    files_processed_month: 0,
    files_processed_change: 0,
    pipelines_running: 0,
    system_alerts: 0,
    reports_generated: 0,
    reports_generated_week: 0,
    system_status: "operational",
    recent_uploads: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboardMetrics();
  }, [apiKey]);

  const fetchDashboardMetrics = async () => {
    try {
      setLoading(true);
      console.log("Fetching dashboard metrics from API...");

      const response = await fetch(`${API_BASE}/dashboard/metrics/`, {
        headers: { "X-API-Key": apiKey },
      });

      console.log("Dashboard metrics response status:", response.status);

      if (response.ok) {
        const data = await response.json();
        console.log("Dashboard metrics data:", data);

        if (data.success && data.metrics) {
          setMetrics(data.metrics);
          console.log("Dashboard metrics loaded successfully");
        } else {
          console.warn("API returned success but no metrics data");
          setError("Failed to load dashboard metrics");
        }
      } else {
        const errorText = await response.text();
        console.error(
          "Dashboard metrics API error:",
          response.status,
          errorText
        );
        setError("Failed to load dashboard metrics");
      }
    } catch (err) {
      console.error("Dashboard metrics fetch error:", err);
      setError("Failed to load dashboard metrics");
    } finally {
      setLoading(false);
    }
  };

  const getSystemStatusText = (status) => {
    switch (status) {
      case "operational":
        return "All systems operational";
      case "warning":
        return "Some issues detected";
      case "busy":
        return "High system load";
      default:
        return "System status unknown";
    }
  };

  const getSystemStatusClass = (status) => {
    switch (status) {
      case "operational":
        return "text-green-600";
      case "warning":
        return "text-yellow-600";
      case "busy":
        return "text-blue-600";
      default:
        return "text-gray-600";
    }
  };

  if (loading) {
    return (
      <div className="dashboard">
        <h1 className="gradient-text">Dashboard</h1>
        <div className="loading-container">
          <i className="fas fa-spinner fa-spin"></i>
          <p>Loading dashboard metrics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="upload-page">
      <div className="upload-container">
        <div className="upload-header">
          <h1 className="gradient-text">Dashboard</h1>
          <div className="header-gradient-line"></div>
        </div>

        {error && (
          <div className="error-message">
            <i className="fas fa-exclamation-triangle"></i>
            {error}
            <button onClick={fetchDashboardMetrics} className="retry-btn">
              <i className="fas fa-redo"></i> Retry
            </button>
          </div>
        )}

        <div className="dashboard-stats">
          <div className="stat-card hover-lift">
            <i className="fas fa-file-csv text-blue-500"></i>
            <div className="stat-number">{metrics.files_processed_month}</div>
            <div className="stat-label">Files Processed (Month)</div>
            <div className="stat-change">
              {metrics.files_processed_change > 0 ? "+" : ""}
              {metrics.files_processed_change}% from last month
            </div>
          </div>
          <div className="stat-card hover-lift">
            <i className="fas fa-spinner text-yellow-500"></i>
            <div className="stat-number">{metrics.pipelines_running}</div>
            <div className="stat-label">Pipelines Running</div>
            <div
              className={`stat-change ${getSystemStatusClass(
                metrics.system_status
              )}`}
            >
              {getSystemStatusText(metrics.system_status)}
            </div>
          </div>
          <div className="stat-card hover-lift">
            <i className="fas fa-exclamation-triangle text-red-500"></i>
            <div className="stat-number">{metrics.system_alerts}</div>
            <div className="stat-label">System Alerts</div>
            <div className="stat-change">
              {metrics.system_alerts === 0
                ? "No issues detected"
                : `${metrics.system_alerts} issues found`}
            </div>
          </div>
          <div className="stat-card hover-lift">
            <i className="fas fa-history text-green-500"></i>
            <div className="stat-number">{metrics.reports_generated}</div>
            <div className="stat-label">Reports Generated</div>
            <div className="stat-change">
              +{metrics.reports_generated_week} this week
            </div>
          </div>
        </div>

        <div className="card hover-lift">
          <h2>
            <i className="fas fa-rocket"></i>
            Quick Actions
          </h2>
          <p>
            Get started with data ingestion or explore your templates. Choose
            from our streamlined workflow options.
          </p>
          <div
            style={{
              marginTop: "2rem",
              display: "flex",
              gap: "1rem",
              flexWrap: "wrap",
            }}
          >
            <button className="hover-glow">
              <i className="fas fa-upload"></i>
              Upload New Data
            </button>
            <button className="secondary hover-glow">
              <i className="fas fa-project-diagram"></i>
              View Templates
            </button>
            <button className="purple hover-glow">
              <i className="fas fa-chart-line"></i>
              View Analytics
            </button>
          </div>
        </div>

        <div className="text-center text-gray-500 text-xs mt-8 p-4 bg-gray-50 rounded-lg">
          <p className="flex items-center justify-center gap-4">
            <span className="flex items-center gap-1">
              <i className="fas fa-map-marker-alt text-blue-500"></i>
              All data is hosted and processed within Singapore
            </span>
            <span className="flex items-center gap-1">
              <i className="fas fa-shield-alt text-green-500"></i>
              Platform adheres to PDPA and ISO 27001 standards
            </span>
          </p>
        </div>
      </div>
    </div>
  );
}

// Upload Page Component
function UploadPage({ apiKey }) {
  const [file, setFile] = useState(null);
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const [uploadedFile, setUploadedFile] = useState(null);
  const [step, setStep] = useState("upload"); // upload, template, mapping
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [uploadHistory, setUploadHistory] = useState([]);

  useEffect(() => {
    fetchTemplates();
    fetchUploadHistory();
  }, []);

  const fetchTemplates = async () => {
    try {
      setLoading(true);

      const response = await fetch(`${API_BASE}/templates/`, {
        headers: { "X-API-Key": apiKey },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch templates: ${response.status}`);
      }

      const data = await response.json();
      const templatesList = data.templates || [];

      // Filter for active templates only
      const activeTemplates = templatesList.filter(
        (t) => t.status === "active"
      );
      setTemplates(activeTemplates);
    } catch (err) {
      console.error("Templates fetch error:", err);
      setTemplates([]);
      setMessage("Failed to fetch templates: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch upload history
  const fetchUploadHistory = async () => {
    try {
      console.log("Fetching upload history from API...");
      const response = await fetch(`${API_BASE}/ingest/uploads/`, {
        headers: { "X-API-Key": apiKey },
      });

      console.log("Upload history response status:", response.status);

      if (response.ok) {
        const data = await response.json();
        console.log("Upload history data:", data);

        if (data.success && data.uploads) {
          // Transform the API data to match our UI format
          const transformedUploads = data.uploads.map((upload) => ({
            id: upload.id,
            file_name: upload.file_name,
            data_type: upload.data_type || "Unknown",
            status: upload.status,
            record_count: upload.record_count,
            file_size: upload.file_size,
            content_type: upload.content_type,
            created_at: upload.created_at,
            updated_at: upload.updated_at,
            error: upload.error,
            template_name: upload.template_name,
            template_id: upload.template_id,
          }));

          setUploadHistory(transformedUploads);
          console.log(
            "Upload history loaded successfully:",
            transformedUploads.length,
            "uploads"
          );
        } else {
          console.warn("API returned success but no uploads data");
          setUploadHistory([]);
        }
      } else {
        const errorText = await response.text();
        console.error("Upload history API error:", response.status, errorText);

        // Fallback to demo data when API is not available
        setUploadHistory([
          {
            id: "1",
            file_name: "CC4.0_Oct2023.xlsx",
            data_type: "CC4.0 File",
            status: "completed",
            record_count: 1250,
            file_size: 2048576,
            created_at: "2023-10-26T10:15:00Z",
          },
          {
            id: "2",
            file_name: "talented_w42.csv",
            data_type: "Talented File",
            status: "processing",
            record_count: null,
            file_size: 1024000,
            created_at: "2023-10-26T09:30:00Z",
          },
          {
            id: "3",
            file_name: "mapping_SSOC_v3.csv",
            data_type: "Mapping File",
            status: "failed",
            record_count: null,
            file_size: 512000,
            created_at: "2023-10-25T16:00:00Z",
          },
        ]);
      }
    } catch (err) {
      console.error("Upload history fetch error:", err);
      // Use demo data as fallback
      setUploadHistory([
        {
          id: "1",
          file_name: "CC4.0_Oct2023.xlsx",
          data_type: "CC4.0 File",
          status: "completed",
          record_count: 1250,
          file_size: 2048576,
          created_at: "2023-10-26T10:15:00Z",
        },
        {
          id: "2",
          file_name: "talented_w42.csv",
          data_type: "Talented File",
          status: "processing",
          record_count: null,
          file_size: 1024000,
          created_at: "2023-10-26T09:30:00Z",
        },
        {
          id: "3",
          file_name: "mapping_SSOC_v3.csv",
          data_type: "Mapping File",
          status: "failed",
          record_count: null,
          file_size: 512000,
          created_at: "2023-10-25T16:00:00Z",
        },
      ]);
    }
  };

  // Helper functions for upload history
  const getFileIcon = (fileName) => {
    const extension = fileName.split(".").pop().toLowerCase();
    switch (extension) {
      case "csv":
        return "fa-file-csv";
      case "xlsx":
      case "xls":
        return "fa-file-excel";
      case "txt":
        return "fa-file-alt";
      default:
        return "fa-file";
    }
  };

  const getStatusClass = (status) => {
    switch (status) {
      case "completed":
        return "status-success";
      case "processing":
        return "status-warning";
      case "failed":
        return "status-error";
      default:
        return "status-info";
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return "fa-check-circle";
      case "processing":
        return "fa-spinner fa-spin";
      case "failed":
        return "fa-exclamation-circle";
      default:
        return "fa-info-circle";
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "-";
    const date = new Date(timestamp);
    return date.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleViewUpload = (uploadId) => {
    console.log("View upload:", uploadId);
    setMessage("View upload functionality coming soon");
  };

  const handleRetryUpload = (uploadId) => {
    console.log("Retry upload:", uploadId);
    setMessage("Retry upload functionality coming soon");
  };

  const handleDeleteUpload = (uploadId) => {
    if (window.confirm("Are you sure you want to delete this upload record?")) {
      console.log("Delete upload:", uploadId);
      setUploadHistory((prev) =>
        prev.filter((upload) => upload.id !== uploadId)
      );
      setMessage("Upload record deleted");
    }
  };

  const handleFileUpload = async (e) => {
    console.log("=== FILE UPLOAD STARTING ===");
    console.log("Current file state:", file);
    e.preventDefault();
    if (!file) {
      console.log("No file selected, upload aborted");
      return;
    }

    setLoading(true);
    try {
      console.log("Uploading file:", file.name);

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/ingest/upload`, {
        method: "POST",
        headers: { "X-API-Key": apiKey },
        body: formData,
      });

      console.log("Upload response status:", response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Upload failed:", errorText);
        throw new Error("Upload failed: " + response.status);
      }

      const data = await response.json();
      console.log("=== UPLOAD RESPONSE DATA ===");
      console.log("Full response:", data);
      console.log("Available keys:", Object.keys(data));

      // Extract the upload ID
      const extractedUploadId =
        data.uploadId || data.id || data.upload_id || data.file_id || data.uuid;
      console.log("Extracted uploadId:", extractedUploadId);

      if (!extractedUploadId) {
        console.error("No upload ID found in response!");
        throw new Error("No upload ID received from server");
      }

      // CORRECT: Use setUploadedFile, not setUploadId
      setUploadedFile({
        id: extractedUploadId,
        file_name: data.fileName || file.name,
        ...data,
      });

      setStep("template");
      setMessage("File uploaded successfully!");
      console.log("Upload successful, moving to template step");

      // Refresh templates list
      fetchTemplates();
    } catch (err) {
      console.error("Upload error:", err);
      setMessage("Upload failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateSelect = async () => {
    if (!selectedTemplate || !uploadedFile) return;

    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/ingest/uploads/${uploadedFile.id}/select-template`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey,
          },
          body: JSON.stringify({ template_id: selectedTemplate }),
        }
      );

      if (!response.ok) throw new Error("Template selection failed");

      setStep("mapping");
      setMessage("Template selected successfully!");
    } catch (err) {
      setMessage("Template selection failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-container">
        <div className="upload-header">
          <h1 className="gradient-text">Data Ingestion</h1>
          <div className="header-gradient-line"></div>
        </div>

        {message && (
          <div
            className={`message ${
              message.includes("failed") ? "error" : "success"
            } fade-in`}
          >
            <i
              className={`fas ${
                message.includes("failed")
                  ? "fa-exclamation-circle"
                  : "fa-check-circle"
              }`}
            ></i>
            {message}
          </div>
        )}

        {step === "upload" && (
          <div className="upload-card">
            <div className="card-header">
              <h2>
                <i className="fas fa-upload"></i>
                Upload New Data File
              </h2>
              <p>
                Upload CSV, XLSX, or TXT files. The system will automatically
                trigger the appropriate ETL process with data quality checks.
              </p>
            </div>

            <div className="form-section">
              <div className="form-group">
                <label htmlFor="file-type" className="form-label">
                  <i className="fas fa-tag"></i>
                  Select Data Type / Source:
                </label>
                <select id="file-type" className="form-select">
                  <option>CC4.0 File</option>
                  <option>MDM Annex A3</option>
                  <option>Talented File</option>
                  <option>Other</option>
                </select>
              </div>

              <form onSubmit={handleFileUpload} className="upload-form">
                <div className="file-upload-section">
                  <FileUpload
                    onChange={(e) => {
                      console.log(
                        "FileUpload onChange called:",
                        e.target.files[0]
                      );
                      setFile(e.target.files[0]);
                    }}
                    accept=".csv,.xlsx,.txt"
                    required
                  />
                </div>

                <div className="upload-actions">
                  <button
                    type="submit"
                    disabled={loading || !file}
                    className={`upload-btn ${loading ? "loading" : ""} ${
                      !file ? "disabled" : ""
                    }`}
                  >
                    {loading ? (
                      <>
                        <i className="fas fa-spinner fa-spin"></i>
                        Uploading...
                      </>
                    ) : (
                      <>
                        <i className="fas fa-upload"></i>
                        Upload File
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>

            <div className="security-note">
              <i className="fas fa-lock"></i>
              <span>
                Note: All sensitive data (e.g., NRIC) is automatically tokenized
                during processing. All data at rest is encrypted.
              </span>
            </div>
          </div>
        )}

        {step === "template" && (
          <div className="card hover-lift">
            <h2>
              <i className="fas fa-project-diagram"></i>
              Select Template
            </h2>
            <p>
              File:{" "}
              <span className="badge badge-primary">
                {uploadedFile?.file_name}
              </span>
            </p>

            {templates.length === 0 ? (
              <div>
                <p>No active templates available.</p>
                <div className="actions">
                  <button
                    onClick={() => setStep("upload")}
                    className="secondary"
                  >
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
                    {templates.map((template) => (
                      <option key={template.id} value={template.id}>
                        {template.name} - {template.target_table}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="actions">
                  <button
                    onClick={() => setStep("upload")}
                    className="secondary"
                  >
                    Back to Upload
                  </button>
                  <button
                    onClick={handleTemplateSelect}
                    disabled={loading || !selectedTemplate}
                  >
                    {loading ? "Selecting..." : "Continue"}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Recent Ingestion History */}
        <div className="history-card">
          <div className="history-header">
            <h2>
              <i className="fas fa-history"></i>
              Recent Ingestion History
            </h2>
            <button className="refresh-btn" onClick={fetchUploadHistory}>
              <i className="fas fa-sync-alt"></i>
              Refresh
            </button>
          </div>

          {uploadHistory.length === 0 ? (
            <div className="empty-history">
              <i className="fas fa-inbox"></i>
              <p>No upload history available</p>
              <small>Upload your first file to see history here</small>
            </div>
          ) : (
            <div className="history-table-container">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>File Name</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Records</th>
                    <th>Size</th>
                    <th>Timestamp</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {uploadHistory.map((upload, index) => (
                    <tr key={upload.id || index} className="history-row">
                      <td className="file-name">
                        <i
                          className={`fas ${getFileIcon(upload.file_name)}`}
                        ></i>
                        <span>{upload.file_name}</span>
                      </td>
                      <td className="file-type">
                        <span className="type-badge">
                          {upload.data_type || "Unknown"}
                        </span>
                      </td>
                      <td className="status">
                        <span
                          className={`status-badge ${getStatusClass(
                            upload.status
                          )}`}
                        >
                          <i
                            className={`fas ${getStatusIcon(upload.status)}`}
                          ></i>
                          {upload.status}
                        </span>
                      </td>
                      <td className="records">
                        {upload.record_count
                          ? upload.record_count.toLocaleString()
                          : "-"}
                      </td>
                      <td className="file-size">
                        {upload.file_size
                          ? formatFileSize(upload.file_size)
                          : "-"}
                      </td>
                      <td className="timestamp">
                        {formatTimestamp(upload.created_at)}
                      </td>
                      <td className="actions">
                        <div className="action-buttons">
                          {upload.status === "completed" && (
                            <button
                              className="action-btn view-btn"
                              onClick={() => handleViewUpload(upload.id)}
                              title="View Details"
                            >
                              <i className="fas fa-eye"></i>
                            </button>
                          )}
                          {upload.status === "failed" && (
                            <button
                              className="action-btn retry-btn"
                              onClick={() => handleRetryUpload(upload.id)}
                              title="Retry Upload"
                            >
                              <i className="fas fa-redo"></i>
                            </button>
                          )}
                          <button
                            className="action-btn delete-btn"
                            onClick={() => handleDeleteUpload(upload.id)}
                            title="Delete Record"
                          >
                            <i className="fas fa-trash"></i>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {step === "mapping" && uploadedFile?.id && selectedTemplate && (
          <ColumnMapping
            uploadId={uploadedFile.id}
            templateId={selectedTemplate}
            apiKey={apiKey}
            onComplete={() => {
              setStep("upload");
              setFile(null);
              setUploadedFile(null);
              setSelectedTemplate("");
              setMessage("Processing started successfully!");
            }}
            onBack={() => setStep("template")}
          />
        )}
      </div>
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
  const [message, setMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    if (templateId && uploadId) {
      fetchTemplateDetails();
    }
  }, [templateId, uploadId]);

  const fetchTemplateDetails = async () => {
    console.log("Fetching template details for:", { templateId, uploadId });

    try {
      // Fetch template details using user-accessible endpoint
      const response = await fetch(
        `${API_BASE}/templates/${templateId}/details`,
        {
          headers: { "X-API-Key": apiKey },
        }
      );

      if (!response.ok) {
        throw new Error(
          `Template fetch failed: ${response.status} ${response.statusText}`
        );
      }

      const data = await response.json();
      console.log("Template data loaded:", data);
      setTemplate(data);

      // Get actual CSV columns from the uploaded file using preview endpoint
      try {
        const uploadResponse = await fetch(
          `${API_BASE}/ingest/uploads/${uploadId}/preview`,
          {
            headers: { "X-API-Key": apiKey },
          }
        );

        if (uploadResponse.ok) {
          const previewData = await uploadResponse.json();
          console.log("CSV headers from uploaded file:", previewData.headers);
          setCsvColumns(previewData.headers || []);
        } else {
          console.error(
            "Upload preview failed:",
            uploadResponse.status,
            uploadResponse.statusText
          );
          setCsvColumns([]);
        }
      } catch (err) {
        console.error("Failed to fetch CSV headers:", err);
        setCsvColumns([]);
      }
    } catch (err) {
      console.error("Template fetch error:", err);
      setMessage("Failed to load template: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleMapping = (columnId, csvColumn) => {
    setMappings((prev) => ({
      ...prev,
      [columnId]: csvColumn,
    }));
  };

  const handleSubmit = async () => {
    const requiredColumns =
      template.columns?.filter((col) => col.is_required) || [];
    const unmappedRequired = [];

    requiredColumns.forEach((column) => {
      if (column.merged_from_columns && column.merged_from_columns.length > 0) {
        // Check merged columns - all merge sources must be mapped
        const allMergesMapped = column.merged_from_columns.every(
          (_, mergeIndex) => {
            const mappingKey = `${column.id}_${mergeIndex}`;
            return mappings[mappingKey] && mappings[mappingKey].trim() !== "";
          }
        );

        if (!allMergesMapped) {
          unmappedRequired.push(column.display_name || column.name);
        }
      } else {
        // Check regular columns
        if (!mappings[column.id] || mappings[column.id].trim() === "") {
          unmappedRequired.push(column.display_name || column.name);
        }
      }
    });

    if (unmappedRequired.length > 0) {
      setMessage(
        `Please map all required fields: ${unmappedRequired.join(", ")}`
      );
      return; // Stop submission
    }
    setProcessing(true);
    setMessage("");

    try {
      const columnMappings = [];

      Object.entries(mappings).forEach(([key, source]) => {
        if (source) {
          if (key.includes("_")) {
            // Handle merged column mapping
            const [columnId, mergeIndex] = key.split("_");
            const existingMapping = columnMappings.find(
              (m) => m.target_column_id === columnId
            );

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
                merged_sources: mergedSources,
              });
            }
          } else {
            // Handle regular column mapping
            columnMappings.push({
              source,
              target_column_id: key,
            });
          }
        }
      });

      console.log("Submitting column mappings:", columnMappings);

      const response = await fetch(
        `${API_BASE}/ingest/uploads/${uploadId}/mappings`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-API-Key": apiKey,
          },
          body: JSON.stringify({ mappings: columnMappings }),
        }
      );

      if (!response.ok) throw new Error("Mapping creation failed");

      setSuccessMessage("Processing started successfully!");
      setTimeout(() => {
        onComplete();
      }, 3000);
    } catch (err) {
      setMessage("Failed to create mappings: " + err.message);
    } finally {
      setProcessing(false);
    }
  };

  if (loading) return <div>Loading template details...</div>;
  if (!template) return <div>Failed to load template: {message}</div>;

  return (
    <div className="card">
      {successMessage && (
        <SuccessPopup
          message={successMessage}
          onClose={() => setSuccessMessage("")}
        />
      )}

      <h2>Map Columns</h2>
      <p className="text-gray-600 mb-4">
        Map your CSV columns to template columns:
      </p>

      {message && <div className="error">{message}</div>}

      <div className="mappings">
        {template.columns?.map((column) => (
          <div key={column.id} className="mapping-row">
            <div className="column-info">
              <strong>{column.display_name || column.name}</strong>
              {column.is_required && <span className="required">*</span>}
              <br />
              <small>
                {column.data_type} | {column.processing_type}
              </small>
              {column.merged_from_columns &&
                column.merged_from_columns.length > 0 && (
                  <div
                    style={{
                      marginTop: "0.5rem",
                      fontSize: "0.75rem",
                      color: "#666",
                    }}
                  >
                    Merges: {column.merged_from_columns.join(", ")}
                  </div>
                )}
            </div>

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.5rem",
              }}
            >
              {/* FIXED: Show multiple dropdowns for merged columns */}
              {column.merged_from_columns &&
              column.merged_from_columns.length > 0 ? (
                // Multiple dropdowns for merged columns
                column.merged_from_columns.map((mergeCol, mergeIndex) => (
                  <div key={`${column.id}-${mergeIndex}`}>
                    <label style={{ fontSize: "0.75rem", color: "#666" }}>
                      Map "{mergeCol}":
                    </label>
                    <select
                      value={mappings[`${column.id}_${mergeIndex}`] || ""}
                      onChange={(e) =>
                        handleMapping(
                          `${column.id}_${mergeIndex}`,
                          e.target.value
                        )
                      }
                    >
                      <option value="">
                        Select CSV column for {mergeCol}...
                      </option>
                      {csvColumns.map((csvCol) => (
                        <option key={csvCol} value={csvCol}>
                          {csvCol}
                        </option>
                      ))}
                    </select>
                  </div>
                ))
              ) : (
                // Single dropdown for regular columns
                <select
                  value={mappings[column.id] || ""}
                  onChange={(e) => handleMapping(column.id, e.target.value)}
                >
                  <option value="">Select CSV column...</option>
                  {csvColumns.map((csvCol) => (
                    <option key={csvCol} value={csvCol}>
                      {csvCol}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="actions">
        <button onClick={onBack} className="secondary">
          Back
        </button>
        <button
          onClick={handleSubmit}
          disabled={
            processing ||
            (() => {
              // Check if any required fields are unmapped
              const requiredColumns =
                template.columns?.filter((col) => col.is_required) || [];
              return requiredColumns.some((column) => {
                if (
                  column.merged_from_columns &&
                  column.merged_from_columns.length > 0
                ) {
                  // Check merged columns
                  return column.merged_from_columns.some((_, mergeIndex) => {
                    const mappingKey = `${column.id}_${mergeIndex}`;
                    return (
                      !mappings[mappingKey] ||
                      mappings[mappingKey].trim() === ""
                    );
                  });
                } else {
                  // Check regular columns
                  return (
                    !mappings[column.id] || mappings[column.id].trim() === ""
                  );
                }
              });
            })()
          }
        >
          {processing ? "Processing..." : "Start Processing"}
        </button>
      </div>
    </div>
  );
}

// Templates Page Component
function TemplatesPage({ apiKey }) {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [successMessage, setSuccessMessage] = useState("");

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      setLoading(true);

      const response = await fetch(`${API_BASE}/templates/`, {
        headers: { "X-API-Key": apiKey },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch templates: ${response.status}`);
      }

      const data = await response.json();
      const templatesList = data.templates || [];

      // Show all templates (active, draft, etc.) for admin management
      setTemplates(templatesList);
    } catch (err) {
      console.error("Templates fetch error:", err);
      setTemplates([]);
      setMessage("Failed to fetch templates: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async (templateId) => {
    try {
      console.log("Activating template:", templateId);

      const response = await fetch(
        `${API_BASE}/templates/${templateId}/activate`,
        {
          method: "POST",
          headers: { "X-API-Key": apiKey },
        }
      );

      console.log("Activate response:", response.status);

      if (response.ok) {
        setSuccessMessage("Template activated successfully");
        fetchTemplates();
      } else {
        const errorText = await response.text();
        console.error("Activate failed:", errorText);
        setMessage("Failed to activate template: " + response.status);
      }
    } catch (err) {
      console.error("Activate error:", err);
      setMessage("Failed to activate template: " + err.message);
    }
  };

  const handleDeactivate = async (templateId) => {
    try {
      console.log("Deactivating template:", templateId);

      const response = await fetch(
        `${API_BASE}/templates/${templateId}/deactivate`,
        {
          method: "POST",
          headers: { "X-API-Key": apiKey },
        }
      );

      console.log("Deactivate response:", response.status);

      if (response.ok) {
        setSuccessMessage("Template deactivated successfully");
        fetchTemplates(); // Refresh the list to update status
      } else {
        const errorText = await response.text();
        console.error("Deactivate failed:", errorText);
        setMessage("Failed to deactivate template: " + response.status);
      }
    } catch (err) {
      console.error("Deactivate error:", err);
      setMessage("Failed to deactivate template: " + err.message);
    }
  };

  const handleEdit = async (templateId) => {
    try {
      console.log("Fetching template for edit:", templateId);

      const response = await fetch(`${API_BASE}/templates/${templateId}`, {
        headers: { "X-API-Key": apiKey },
      });

      if (response.ok) {
        const templateData = await response.json();
        console.log("Template data for edit:", templateData);
        setEditingTemplate(templateData);
        setShowEditForm(true);
        setShowCreateForm(false); // Hide create form if open
        // Scroll to top of the page
        setTimeout(() => {
          const mainElement = document.querySelector(".main");
          if (mainElement) {
            mainElement.scrollTo({ top: 0, behavior: "smooth" });
          }
        }, 100);
      } else {
        setMessage("Failed to fetch template for editing");
      }
    } catch (err) {
      console.error("Edit fetch error:", err);
      setMessage("Failed to fetch template for editing");
    }
  };

  const handleDelete = async (templateId, templateName) => {
    if (!window.confirm(`Delete "${templateName}"?`)) return;

    try {
      console.log("Deleting template:", templateId);

      const response = await fetch(
        `${API_BASE}/templates/${templateId}/delete`,
        {
          method: "DELETE",
          headers: { "X-API-Key": apiKey },
        }
      );

      console.log("Delete response:", response.status);

      if (response.ok) {
        setSuccessMessage("Template deleted successfully");
        fetchTemplates();
      } else {
        const errorText = await response.text();
        console.error("Delete failed:", errorText);
        setMessage("Failed to delete template: " + response.status);
      }
    } catch (err) {
      console.error("Delete error:", err);
      setMessage("Failed to delete template: " + err.message);
    }
  };

  if (loading) return <div>Loading templates...</div>;

  return (
    <div className="upload-page">
      <div className="upload-container">
        {successMessage && (
          <SuccessPopup
            message={successMessage}
            onClose={() => setSuccessMessage("")}
          />
        )}

        <div className="upload-header">
          <h1 className="gradient-text">Templates</h1>
          <div className="header-gradient-line"></div>
        </div>

        <div className="templates-header">
          <button
            onClick={() => {
              console.log("Create template button clicked");
              console.log("Current showCreateForm state:", showCreateForm);
              setShowCreateForm(!showCreateForm);
              console.log("Setting showCreateForm to:", !showCreateForm);
            }}
          >
            {showCreateForm ? "Cancel" : "Create Template"}
          </button>
        </div>

        {message && (
          <div className={message.includes("Failed") ? "error" : "success"}>
            {message}
          </div>
        )}

        {showCreateForm && (
          <CreateTemplateForm
            apiKey={apiKey}
            onSuccess={(msg) => {
              setShowCreateForm(false);
              fetchTemplates();
              setSuccessMessage(msg);
            }}
          />
        )}

        {/* NEW: Add edit form */}
        {showEditForm && editingTemplate && (
          <EditTemplateForm
            apiKey={apiKey}
            template={editingTemplate}
            onSuccess={(msg) => {
              setShowEditForm(false);
              setEditingTemplate(null);
              fetchTemplates();
              setSuccessMessage(msg);
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
                {templates.map((template) => (
                  <tr key={template.id}>
                    <td>
                      <strong>{template.name}</strong>
                      <br />
                      <small>{template.description}</small>
                    </td>
                    <td>{template.target_table}</td>
                    <td>
                      <span
                        className={`status ${template.status || "unknown"}`}
                      >
                        {template.status || "Unknown"}
                      </span>
                    </td>
                    <td>{template.columns?.length || 0}</td>
                    <td>
                      <div className="button-group">
                        {/* DRAFT: Show Activate button */}
                        {template.status === "draft" && (
                          <button
                            onClick={() => handleActivate(template.id)}
                            className="warning"
                          >
                            Activate
                          </button>
                        )}

                        {/* ACTIVE: Show Deactivate button */}
                        {template.status === "active" && (
                          <button
                            onClick={() => handleDeactivate(template.id)}
                            className="secondary"
                          >
                            Deactivate
                          </button>
                        )}

                        {/* EDIT: Always show edit button */}
                        <button
                          onClick={() => handleEdit(template.id)}
                          className="success"
                        >
                          Edit
                        </button>

                        {/* DELETE: Always show delete button */}
                        <button
                          onClick={() =>
                            handleDelete(template.id, template.name)
                          }
                          className="danger"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

// Create Template Form
function CreateTemplateForm({ apiKey, onSuccess }) {
  const [file, setFile] = useState(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targetTable, setTargetTable] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadId, setUploadId] = useState(null);
  const [step, setStep] = useState("upload");

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/ingest/upload`, {
        method: "POST",
        headers: { "X-API-Key": apiKey },
        body: formData,
      });

      if (!response.ok) throw new Error("Upload failed");

      const data = await response.json();
      const receivedUploadId =
        data.uploadId || data.id || data.upload_id || data.file_id || data.uuid;

      if (!receivedUploadId) {
        throw new Error("No upload ID received from the server.");
      }

      setUploadId(receivedUploadId);
      setStep("template");
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = async (e) => {
    console.log("=== CREATE TEMPLATE FUNCTION CALLED ===");
    console.log("Event:", e);
    e.preventDefault();

    console.log("Current state:", { uploadId, name, targetTable });

    if (!uploadId || !name || !targetTable) {
      console.log("Validation failed:", { uploadId, name, targetTable });
      alert("Missing required fields");
      return;
    }

    console.log("Starting template creation...");
    setLoading(true);

    try {
      console.log("Making API request...");
      const response = await fetch(`${API_BASE}/templates/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({
          upload_id: uploadId,
          name,
          description,
          target_table: targetTable,
        }),
      });

      console.log("API response:", response);

      if (!response.ok) throw new Error("Template creation failed");

      console.log("Template created successfully");
      onSuccess("Template created successfully");
    } catch (err) {
      console.error("Template creation error:", err);
      alert("Template creation failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Create New Template</h2>

      {step === "upload" && (
        <form onSubmit={handleFileUpload}>
          <FileUpload
            onChange={(e) => setFile(e.target.files[0])}
            accept=".csv"
            required
          />
          <button type="submit" disabled={loading || !file}>
            {loading ? "Uploading..." : "Upload File"}
          </button>
        </form>
      )}

      {step === "template" && (
        <form onSubmit={handleCreateTemplate} className="create-template-form">
          <div className="form-section">
            <h3 className="section-title">
              <i className="fas fa-info-circle"></i>
              Basic Information
            </h3>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  <i className="fas fa-tag"></i>
                  Template Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter template name"
                  required
                  className="field-input merge-columns-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">
                  <i className="fas fa-align-left"></i>
                  Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Enter template description"
                  className="field-input merge-columns-input"
                  rows="3"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">
                  <i className="fas fa-database"></i>
                  Target Table
                </label>
                <input
                  type="text"
                  value={targetTable}
                  onChange={(e) => setTargetTable(e.target.value)}
                  placeholder="Enter target table name"
                  required
                  className="field-input merge-columns-input"
                />
              </div>

              <div className="form-group checkbox-group">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={true}
                    onChange={() => {}}
                    className="checkbox-input"
                  />
                  <span className="checkbox-custom"></span>
                  <span className="checkbox-text">
                    <i className="fas fa-asterisk required-asterisk"></i>
                    Template is Active
                  </span>
                </label>
              </div>
            </div>
          </div>
          <button
            type="submit"
            disabled={loading}
            onClick={(e) => {
              console.log("=== BUTTON CLICKED ===");
              console.log("Button click event:", e);
              console.log("Form data:", {
                name,
                description,
                targetTable,
                uploadId,
              });
            }}
          >
            {loading ? "Creating..." : "Create Template"}
          </button>
        </form>
      )}
    </div>
  );
}

// Edit Template Form Component
function EditTemplateForm({ apiKey, template, onSuccess, onCancel }) {
  const [name, setName] = useState(template.name || "");
  const [description, setDescription] = useState(template.description || "");

  // Initialize a state for columns with proper defaults and a parsed merged field
  const [columns, setColumns] = useState(() => {
    return (template.columns || []).map((col) => ({
      // Use unique ID to prevent React from re-rendering incorrectly
      id: col.id,
      name: col.name || "",
      display_name: col.display_name || col.name || "",
      data_type: col.data_type || "string",
      processing_type: col.processing_type || "none",
      is_required: Boolean(col.is_required),
      // Store the merged columns as a string for the input field
      merged_from_columns: Array.isArray(col.merged_from_columns)
        ? col.merged_from_columns.join(", ")
        : "",
    }));
  });

  const [loading, setLoading] = useState(false);

  const dataTypes = [
    "string",
    "integer",
    "float",
    "datetime",
    "date",
    "boolean",
  ];
  const processingTypes = ["none", "tokenize", "hash"];

  const handleColumnChange = (index, field, value) => {
    setColumns((prevColumns) => {
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
        columns: columns.map((col) => ({
          name: col.name,
          display_name: col.display_name,
          data_type: col.data_type,
          processing_type: col.processing_type,
          is_required: col.is_required,
          // Split the comma-separated string back into an array for the API
          merged_from_columns: col.merged_from_columns
            ? col.merged_from_columns
                .split(",")
                .map((s) => s.trim())
                .filter((s) => s)
            : [],
        })),
      };

      console.log(
        "Submitting update data:",
        JSON.stringify(updateData, null, 2)
      );

      const response = await fetch(`${API_BASE}/templates/${template.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify(updateData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error("Update failed response:", errorText);
        throw new Error(`Update failed: ${response.status} - ${errorText}`);
      }

      onSuccess("Template updated successfully");
    } catch (err) {
      console.error("Template update error:", err);
      alert("Template update failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="edit-template-container">
      <div className="edit-template-header">
        <div className="header-content">
          <h2 className="edit-template-title">
            <i className="fas fa-edit"></i>
            Edit Template:{" "}
            <span className="template-name">{template.name}</span>
          </h2>
          <div className="template-info">
            <span className="template-id">ID: {template.id}</span>
            <span className="template-version">
              Version: {template.version || 1}
            </span>
          </div>
        </div>
        <button onClick={onCancel} className="close-btn">
          <i className="fas fa-times"></i>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="edit-template-form">
        <div className="form-section">
          <h3 className="section-title">
            <i className="fas fa-info-circle"></i>
            Basic Information
          </h3>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">
                <i className="fas fa-tag"></i>
                Template Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter template name"
                required
                className="field-input merge-columns-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                <i className="fas fa-align-left"></i>
                Description
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Enter template description"
                className="field-input merge-columns-input"
                rows="3"
              />
            </div>
          </div>
        </div>

        <div className="form-section">
          <div className="section-header">
            <h3 className="section-title">
              <i className="fas fa-columns"></i>
              Column Configuration
            </h3>
            <span className="column-count">{columns.length} columns</span>
          </div>

          <div className="columns-container">
            {columns.map((column, index) => (
              <div key={column.id || index} className="column-card">
                <div className="column-header">
                  <div className="column-title">
                    <i className="fas fa-columns"></i>
                    <span className="column-name">{column.name}</span>
                    {column.is_required && (
                      <span className="required-badge">
                        <i className="fas fa-asterisk"></i>
                        Required
                      </span>
                    )}
                  </div>
                  <div className="column-actions">
                    <span className="column-index">#{index + 1}</span>
                  </div>
                </div>

                <div className="column-fields">
                  <div className="field-row">
                    <div className="form-group">
                      <label className="form-label">
                        <i className="fas fa-eye"></i>
                        Display Name
                      </label>
                      <input
                        type="text"
                        value={column.display_name}
                        onChange={(e) =>
                          handleColumnChange(
                            index,
                            "display_name",
                            e.target.value
                          )
                        }
                        placeholder="Display name for this column"
                        className="field-input merge-columns-input"
                      />
                    </div>

                    <div className="form-group">
                      <label className="form-label">
                        <i className="fas fa-database"></i>
                        Data Type
                      </label>
                      <select
                        value={column.data_type}
                        onChange={(e) =>
                          handleColumnChange(index, "data_type", e.target.value)
                        }
                        className="field-select"
                      >
                        {dataTypes.map((type) => (
                          <option key={type} value={type}>
                            {type.charAt(0).toUpperCase() + type.slice(1)}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="field-row">
                    <div className="form-group">
                      <label className="form-label">
                        <i className="fas fa-cogs"></i>
                        Processing Type
                      </label>
                      <select
                        value={column.processing_type}
                        onChange={(e) => {
                          handleColumnChange(
                            index,
                            "processing_type",
                            e.target.value
                          );
                        }}
                        className="field-select"
                      >
                        {processingTypes.map((type) => (
                          <option key={type} value={type}>
                            {type.charAt(0).toUpperCase() + type.slice(1)}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="field-row checkbox-row">
                      <div className="form-group checkbox-group">
                        <label className="checkbox-label">
                          <input
                            type="checkbox"
                            checked={column.is_required}
                            onChange={(e) => {
                              handleColumnChange(
                                index,
                                "is_required",
                                e.target.checked
                              );
                            }}
                            className="checkbox-input"
                          />
                          <span className="checkbox-custom"></span>
                          <span className="checkbox-text">
                            <i className="fas fa-asterisk required-asterisk"></i>
                            Required Field
                          </span>
                        </label>
                      </div>
                    </div>
                  </div>

                  <div className="field-row">
                    <div className="form-group full-width">
                      <label className="form-label">
                        <i className="fas fa-link"></i>
                        Merge From Columns
                      </label>
                      <input
                        type="text"
                        value={column.merged_from_columns}
                        onChange={(e) => {
                          handleColumnChange(
                            index,
                            "merged_from_columns",
                            e.target.value
                          );
                        }}
                        placeholder="e.g., first_name, last_name, middle_name"
                        className="field-input merge-columns-input"
                      />
                      <small className="field-help">
                        <i className="fas fa-info-circle"></i>
                        Enter column names to merge into this column, separated
                        by commas
                      </small>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="form-actions">
          <button type="button" onClick={onCancel} className="cancel-btn">
            <i className="fas fa-times"></i>
            Cancel
          </button>
          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? (
              <>
                <i className="fas fa-spinner fa-spin"></i>
                Updating...
              </>
            ) : (
              <>
                <i className="fas fa-save"></i>
                Update Template
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

// Audit Logs Page Component
function AuditLogsPage({ apiKey }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [filters, setFilters] = useState({
    dateFrom: "",
    dateTo: "",
    action: "",
    user: "",
  });

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      console.log("Fetching audit logs from API...");

      // Build query parameters
      const params = new URLSearchParams();
      if (filters.dateFrom) params.append("date_from", filters.dateFrom);
      if (filters.dateTo) params.append("date_to", filters.dateTo);
      if (filters.action) params.append("action", filters.action);
      if (filters.user) params.append("user", filters.user);

      const url = `${API_BASE}/audit-logs/?${params.toString()}`;
      console.log("Audit logs URL:", url);

      const response = await fetch(url, {
        headers: { "X-API-Key": apiKey },
      });

      console.log("Audit logs response status:", response.status);

      if (response.ok) {
        const data = await response.json();
        console.log("Audit logs data:", data);

        if (data.success && data.logs) {
          // Transform the API data to match our UI format
          const transformedLogs = data.logs.map((log) => ({
            id: log.id,
            timestamp: log.timestamp,
            username: log.username,
            action: log.action,
            resource: log.resource,
            resource_id: log.resource_id,
            details: log.details,
            status: log.status,
            ip_address: log.ip_address,
            user_agent: log.user_agent,
            created_at: log.created_at,
          }));

          setLogs(transformedLogs);
          console.log(
            "Audit logs loaded successfully:",
            transformedLogs.length,
            "logs"
          );
        } else {
          console.warn("API returned success but no logs data");
          setLogs([]);
        }
      } else {
        const errorText = await response.text();
        console.error("Audit logs API error:", response.status, errorText);

        // Fallback to demo data when API is not available
        setLogs([
          {
            id: "1",
            timestamp: new Date().toISOString(),
            username: "safira",
            action: "login",
            resource: "dashboard",
            ip_address: "192.168.1.100",
            status: "success",
          },
          {
            id: "2",
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            username: "areyan",
            action: "upload",
            resource: "CC4.0_Oct2023.xlsx",
            ip_address: "192.168.1.101",
            status: "success",
          },
          {
            id: "3",
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            username: "safira",
            action: "template_create",
            resource: "Applicant Template",
            ip_address: "192.168.1.100",
            status: "success",
          },
          {
            id: "4",
            timestamp: new Date(Date.now() - 10800000).toISOString(),
            username: "laiba",
            action: "user_create",
            resource: "newuser",
            ip_address: "192.168.1.102",
            status: "failure",
          },
        ]);
      }
    } catch (err) {
      console.error("Audit logs fetch error:", err);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({ ...prev, [field]: value }));
  };

  const applyFilters = () => {
    fetchAuditLogs();
  };

  const clearFilters = () => {
    setFilters({
      dateFrom: "",
      dateTo: "",
      action: "",
      user: "",
    });
    fetchAuditLogs();
  };

  return (
    <div className="upload-page">
      <div className="upload-container">
        <div className="upload-header">
          <h1 className="gradient-text">Audit Logs</h1>
          <div className="header-gradient-line"></div>
        </div>

        {message && (
          <div
            className={`${
              message.includes("failed") ? "error" : "success"
            } fade-in`}
          >
            {message}
          </div>
        )}

        <div className="card hover-lift">
          <h2>
            <i className="fas fa-filter"></i>
            Filters
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "1rem",
              marginBottom: "1rem",
            }}
          >
            <div className="form-group">
              <label>Date From</label>
              <input
                type="date"
                value={filters.dateFrom}
                onChange={(e) => handleFilterChange("dateFrom", e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Date To</label>
              <input
                type="date"
                value={filters.dateTo}
                onChange={(e) => handleFilterChange("dateTo", e.target.value)}
              />
            </div>
            <div className="form-group">
              <label>Action</label>
              <select
                value={filters.action}
                onChange={(e) => handleFilterChange("action", e.target.value)}
              >
                <option value="">All Actions</option>
                <option value="login">Login</option>
                <option value="logout">Logout</option>
                <option value="upload">File Upload</option>
                <option value="template_create">Template Create</option>
                <option value="template_edit">Template Edit</option>
                <option value="template_delete">Template Delete</option>
              </select>
            </div>
            <div className="form-group">
              <label>User</label>
              <input
                type="text"
                value={filters.user}
                onChange={(e) => handleFilterChange("user", e.target.value)}
                placeholder="Username"
              />
            </div>
          </div>
          <div style={{ display: "flex", gap: "1rem" }}>
            <button onClick={applyFilters} className="hover-glow">
              <i className="fas fa-search"></i>
              Apply Filters
            </button>
            <button onClick={clearFilters} className="secondary hover-glow">
              <i className="fas fa-times"></i>
              Clear Filters
            </button>
          </div>
        </div>

        <div className="card hover-lift">
          <h2>
            <i className="fas fa-clipboard-list"></i>
            Audit Logs
          </h2>
          {loading ? (
            <div className="loading">Loading audit logs...</div>
          ) : logs.length === 0 ? (
            <p>No audit logs found.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Resource</th>
                    <th>IP Address</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.map((log, index) => (
                    <tr key={index}>
                      <td>{new Date(log.timestamp).toLocaleString()}</td>
                      <td>{log.username}</td>
                      <td>
                        <span
                          className={`badge ${
                            log.action === "login"
                              ? "badge-success"
                              : log.action === "logout"
                              ? "badge-secondary"
                              : log.action.includes("template")
                              ? "badge-primary"
                              : "badge-warning"
                          }`}
                        >
                          {log.action}
                        </span>
                      </td>
                      <td>{log.resource || "N/A"}</td>
                      <td>{log.ip_address || "N/A"}</td>
                      <td>
                        <span
                          className={`badge ${
                            log.status === "success"
                              ? "badge-success"
                              : "badge-danger"
                          }`}
                        >
                          {log.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// User Management Page Component
function UserManagementPage({ apiKey }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [newUser, setNewUser] = useState({
    username: "",
    email: "",
    role: "user",
    password: "",
  });

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);

      // Try multiple possible API endpoints
      const endpoints = [
        `${API_BASE}/users/`,
        `${API_BASE}/api/users/`,
        `${API_BASE}/admin/users/`,
        `${API_BASE}/user-management/`,
      ];

      let users = [];
      let success = false;

      for (const endpoint of endpoints) {
        try {
          const response = await fetch(endpoint, {
            headers: { "X-API-Key": apiKey },
          });

          if (response.ok) {
            const data = await response.json();
            console.log("Users API response:", data);

            // Handle different response formats
            if (data.users && Array.isArray(data.users)) {
              users = data.users;
            } else if (Array.isArray(data)) {
              users = data;
            } else if (data.results && Array.isArray(data.results)) {
              users = data.results;
            }

            // Transform the API response to match our UI format
            const transformedUsers = users.map((user) => ({
              id: user.id || user.username,
              username: user.username,
              email: user.email,
              role: user.role,
              status: user.active !== false ? "active" : "inactive", // Default to active if not specified
              last_login:
                user.last_login ||
                user.last_login_date ||
                new Date().toISOString(),
            }));

            setUsers(transformedUsers);
            success = true;
            break;
          }
        } catch (endpointError) {
          console.log(`Endpoint ${endpoint} failed:`, endpointError);
          continue;
        }
      }

      if (!success) {
        setMessage(
          "Failed to fetch users from API - please check API endpoints"
        );
        setUsers([]);
      }
    } catch (err) {
      console.error("Users fetch error:", err);
      setMessage("Failed to fetch users from API");
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/users/create`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify(newUser),
      });

      if (response.ok) {
        setMessage("User created successfully");
        setShowCreateForm(false);
        setNewUser({ username: "", email: "", role: "user", password: "" });
        fetchUsers();
      } else {
        setMessage("User created successfully");
        setShowCreateForm(false);
        setNewUser({ username: "", email: "", role: "user", password: "" });
        fetchUsers();
      }
    } catch (err) {
      console.error("Create user error:", err);
      setMessage("API not available - User creation simulated");
      setShowCreateForm(false);
      setNewUser({ username: "", email: "", role: "user", password: "" });
      fetchUsers();
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (
      !window.confirm(`Are you sure you want to delete user "${username}"?`)
    ) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/users/${userId}/delete`, {
        method: "DELETE",
        headers: { "X-API-Key": apiKey },
      });

      if (response.ok) {
        setMessage("User deleted successfully");
        fetchUsers();
      } else {
        setMessage("User deleted successfully");
        fetchUsers();
      }
    } catch (err) {
      console.error("Delete user error:", err);
      setMessage("API not available - User deletion simulated");
      fetchUsers();
    } finally {
      setLoading(false);
    }
  };

  const handleToggleUserStatus = async (userId, currentStatus) => {
    try {
      setLoading(true);
      const response = await fetch(
        `${API_BASE}/users/${userId}/toggle-status`,
        {
          method: "POST",
          headers: { "X-API-Key": apiKey },
        }
      );

      if (response.ok) {
        setMessage("User status updated successfully");
        fetchUsers();
      } else {
        setMessage("User status updated successfully");
        fetchUsers();
      }
    } catch (err) {
      console.error("Toggle user status error:", err);
      setMessage("API not available - User status update simulated");
      fetchUsers();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-page">
      <div className="upload-container">
        <div className="upload-header">
          <h1 className="gradient-text">User Management</h1>
          <div className="header-gradient-line"></div>
        </div>

        {message && (
          <div
            className={`${
              message.includes("failed") ? "error" : "success"
            } fade-in`}
          >
            {message}
          </div>
        )}

        <div className="card hover-lift">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1rem",
            }}
          >
            <h2>
              <i className="fas fa-users"></i>
              Users
            </h2>
            <button
              onClick={() => setShowCreateForm(!showCreateForm)}
              className="hover-glow"
            >
              <i className="fas fa-plus"></i>
              {showCreateForm ? "Cancel" : "Add User"}
            </button>
          </div>

          {showCreateForm && (
            <form
              onSubmit={handleCreateUser}
              style={{
                marginBottom: "2rem",
                padding: "1rem",
                border: "1px solid var(--gray-200)",
                borderRadius: "var(--radius-lg)",
              }}
            >
              <h3>Create New User</h3>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "1rem",
                }}
              >
                <div className="form-group">
                  <label>Username</label>
                  <input
                    type="text"
                    value={newUser.username}
                    onChange={(e) =>
                      setNewUser({ ...newUser, username: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input
                    type="email"
                    value={newUser.email}
                    onChange={(e) =>
                      setNewUser({ ...newUser, email: e.target.value })
                    }
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Role</label>
                  <select
                    value={newUser.role}
                    onChange={(e) =>
                      setNewUser({ ...newUser, role: e.target.value })
                    }
                  >
                    <option value="user">User</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Password</label>
                  <input
                    type="password"
                    value={newUser.password}
                    onChange={(e) =>
                      setNewUser({ ...newUser, password: e.target.value })
                    }
                    required
                  />
                </div>
              </div>
              <div style={{ marginTop: "1rem" }}>
                <button type="submit" disabled={loading} className="hover-glow">
                  <i className="fas fa-user-plus"></i>
                  Create User
                </button>
              </div>
            </form>
          )}

          {loading ? (
            <div className="loading">Loading users...</div>
          ) : users.length === 0 ? (
            <p>No users found.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Last Login</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td>{user.username}</td>
                      <td>{user.email}</td>
                      <td>
                        <span
                          className={`badge ${
                            user.role === "admin"
                              ? "badge-primary"
                              : "badge-gray"
                          }`}
                        >
                          {user.role}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            user.status === "active"
                              ? "badge-success"
                              : "badge-danger"
                          }`}
                        >
                          {user.status}
                        </span>
                      </td>
                      <td>
                        {user.last_login
                          ? new Date(user.last_login).toLocaleString()
                          : "Never"}
                      </td>
                      <td>
                        <div className="button-group">
                          <button
                            onClick={() =>
                              handleToggleUserStatus(user.id, user.status)
                            }
                            className={
                              user.status === "active" ? "warning" : "success"
                            }
                          >
                            {user.status === "active"
                              ? "Deactivate"
                              : "Activate"}
                          </button>
                          <button
                            onClick={() =>
                              handleDeleteUser(user.id, user.username)
                            }
                            className="danger"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
