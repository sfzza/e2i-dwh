// Shared TypeScript interfaces for the ETL platform

export interface User {
  id: string
  email: string
  name: string
  role: "admin" | "user"
  isAuthenticated: boolean
}

export interface Upload {
  id: string
  filename: string
  file_size: number
  status: "pending" | "uploading" | "completed" | "processing" | "failed"
  uploaded_at: string
  processed_at?: string
  error_message?: string
}

export interface Template {
  id: string
  name: string
  description: string
  target_table: string
  is_active: boolean
  column_count: number
  created_by: string
  created_at: string
  updated_at: string
}

export interface TemplateColumn {
  id: string
  template_id: string
  name: string
  data_type: string
  processing_type: "none" | "hash" | "tokenize" | "encrypt"
  is_required: boolean
  max_length?: number
  default_value?: string
}

export interface ColumnMapping {
  source_column: string
  target_column: string
  transform_function?: string
  is_valid: boolean
}

export interface Dataset {
  name: string
  table: string
  row_count: number
  last_updated: string
  schema?: DatasetColumn[]
}

export interface DatasetColumn {
  name: string
  type: string
  nullable: boolean
  description?: string
}

export interface QueryResult {
  id: string
  query: string
  status: "running" | "completed" | "failed"
  row_count?: number
  execution_time?: string
  created_at: string
  error_message?: string
  result_data?: any[]
}

export interface APIResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}
