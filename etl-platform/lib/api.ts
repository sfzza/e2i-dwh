// API configuration and utilities for connecting to Django backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"

class APIClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const config: RequestInit = {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    }

    const response = await fetch(url, config)

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  // =================== INGESTION ENDPOINTS ===================

  async uploadFile(file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData()
    formData.append("file", file)

    const response = await fetch(`${this.baseURL}/ingest/upload`, {
      method: "POST",
      body: formData,
      // Don't set Content-Type header for FormData - browser will set it with boundary
    })

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.status} ${response.statusText}`)
    }

    return response.json()
  }

  async getUploadStatus(uploadId: string) {
    return this.request(`/ingest/uploads/${uploadId}/status`)
  }

  async presignUpload(filename: string, contentType: string) {
    return this.request("/ingest/presign", {
      method: "POST",
      body: JSON.stringify({ filename, content_type: contentType }),
    })
  }

  async completeUpload(uploadId: string) {
    return this.request("/ingest/complete", {
      method: "POST",
      body: JSON.stringify({ upload_id: uploadId }),
    })
  }

  // =================== TEMPLATE MANAGEMENT ===================

  async getTemplates() {
    return this.request("/templates/")
  }

  async createTemplate(templateData: any) {
    return this.request("/templates/create", {
      method: "POST",
      body: JSON.stringify(templateData),
    })
  }

  async updateTemplate(templateId: string, templateData: any) {
    return this.request(`/templates/${templateId}`, {
      method: "PUT",
      body: JSON.stringify(templateData),
    })
  }

  async activateTemplate(templateId: string) {
    return this.request(`/templates/${templateId}/activate`, {
      method: "POST",
    })
  }

  async deleteTemplate(templateId: string) {
    return this.request(`/templates/${templateId}/delete`, {
      method: "DELETE",
    })
  }

  async getTemplateUsage(templateId: string) {
    return this.request(`/templates/${templateId}/usage`)
  }

  async deleteTemplateColumn(templateId: string, mappingId: string) {
    return this.request(`/templates/${templateId}/columns/${mappingId}/delete`, {
      method: "DELETE",
    })
  }

  // =================== COLUMN MAPPING ===================

  async getUploadPreview(uploadId: string) {
    return this.request(`/ingest/uploads/${uploadId}/preview`)
  }

  async selectTemplate(uploadId: string, templateId: string) {
    return this.request(`/ingest/uploads/${uploadId}/select-template`, {
      method: "POST",
      body: JSON.stringify({ template_id: templateId }),
    })
  }

  async setColumnMappings(uploadId: string, mappings: any) {
    return this.request(`/ingest/uploads/${uploadId}/mappings`, {
      method: "POST",
      body: JSON.stringify({ mappings }),
    })
  }

  // =================== REPORTING ENDPOINTS ===================

  async ping() {
    return this.request("/api/reports/ping")
  }

  async getDatasets() {
    return this.request("/api/reports/datasets")
  }

  async getDatasetSchema(dataset: string) {
    return this.request(`/api/reports/datasets/${dataset}/schema`)
  }

  async getDatasetSample(dataset: string) {
    return this.request(`/api/reports/datasets/${dataset}/sample`)
  }

  async runQuery(query: string) {
    return this.request("/api/reports/query/run", {
      method: "POST",
      body: JSON.stringify({ query }),
    })
  }

  async explainQuery(query: string) {
    return this.request("/api/reports/query/explain", {
      method: "POST",
      body: JSON.stringify({ query }),
    })
  }

  async getQueryLimits() {
    return this.request("/api/reports/query/limits")
  }

  async detokenizeReport(reportId: string, columns: string[]) {
    return this.request("/api/reports/detokenize", {
      method: "POST",
      body: JSON.stringify({ report_id: reportId, columns }),
    })
  }

  async getReportStatus(reportId: string) {
    return this.request(`/api/reports/${reportId}/status`)
  }

  async deleteReport(reportId: string) {
    return this.request(`/api/reports/${reportId}/delete`, {
      method: "DELETE",
    })
  }

  async downloadReport(reportId: string) {
    const response = await fetch(`${this.baseURL}/api/reports/${reportId}/download`)
    return response.blob()
  }
}

export const apiClient = new APIClient(API_BASE_URL)
