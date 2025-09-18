"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ArrowRight, Settings, CheckCircle, AlertCircle, FileText, Database, Shuffle, Loader2 } from "lucide-react"
import { apiClient } from "@/lib/api"
import { useAuth } from "@/lib/auth"

interface SourceColumn {
  name: string
  type: string
  sample_data: string[]
}

interface TargetColumn {
  name: string
  data_type: string
  processing_type: string
  is_required: boolean
}

interface ColumnMapping {
  source_column: string
  target_column: string
  transform_function?: string
  is_valid: boolean
}

interface Upload {
  id: string
  filename: string
  uploaded_at: string
  status: string
}

interface Template {
  id: string
  name: string
  target_table: string
  is_active: boolean
}

export function ColumnMapping() {
  const { user } = useAuth()
  const [selectedUpload, setSelectedUpload] = useState<string>("")
  const [selectedTemplate, setSelectedTemplate] = useState<string>("")
  const [uploads, setUploads] = useState<Upload[]>([])
  const [templates, setTemplates] = useState<Template[]>([])
  const [sourceColumns, setSourceColumns] = useState<SourceColumn[]>([])
  const [targetColumns, setTargetColumns] = useState<TargetColumn[]>([])
  const [mappings, setMappings] = useState<ColumnMapping[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    try {
      setLoading(true)
      // Load completed uploads (mock for now - you'd get this from upload status API)
      const mockUploads: Upload[] = [
        { id: "1", filename: "customer_data.csv", uploaded_at: "2 hours ago", status: "completed" },
        { id: "2", filename: "sales_report.csv", uploaded_at: "1 hour ago", status: "completed" },
      ]
      setUploads(mockUploads)

      // Load active templates
      const templatesResponse = await apiClient.getTemplates()
      setTemplates(templatesResponse.templates?.filter((t: Template) => t.is_active) || [])
      console.log("[v0] Loaded templates for mapping:", templatesResponse)
    } catch (err) {
      console.error("[v0] Failed to load initial data:", err)
      setError("Failed to load data. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedUpload) {
      loadUploadPreview()
    }
  }, [selectedUpload])

  const loadUploadPreview = async () => {
    if (!selectedUpload) return

    try {
      setLoading(true)
      const response = await apiClient.getUploadPreview(selectedUpload)
      setSourceColumns(response.columns || [])
      console.log("[v0] Loaded upload preview:", response)
    } catch (err) {
      console.error("[v0] Failed to load upload preview:", err)
      setError("Failed to load file preview. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedTemplate) {
      loadTemplateColumns()
    }
  }, [selectedTemplate])

  const loadTemplateColumns = async () => {
    if (!selectedTemplate) return

    try {
      // Mock template columns - in real implementation, you'd get this from template details API
      const mockTargetColumns: TargetColumn[] = [
        { name: "customer_id", data_type: "string", processing_type: "none", is_required: true },
        { name: "first_name", data_type: "string", processing_type: "none", is_required: true },
        { name: "last_name", data_type: "string", processing_type: "none", is_required: true },
        { name: "email", data_type: "string", processing_type: "hash", is_required: true },
        { name: "phone", data_type: "string", processing_type: "tokenize", is_required: false },
        { name: "birth_date", data_type: "date", processing_type: "none", is_required: false },
      ]
      setTargetColumns(mockTargetColumns)

      // Initialize mappings
      const initialMappings: ColumnMapping[] = sourceColumns.map((sourceCol, index) => ({
        source_column: sourceCol.name,
        target_column: mockTargetColumns[index]?.name || "",
        is_valid: !!mockTargetColumns[index]?.name,
      }))
      setMappings(initialMappings)
    } catch (err) {
      console.error("[v0] Failed to load template columns:", err)
      setError("Failed to load template columns. Please try again.")
    }
  }

  const selectTemplate = async () => {
    if (!selectedUpload || !selectedTemplate) return

    try {
      await apiClient.selectTemplate(selectedUpload, selectedTemplate)
      console.log("[v0] Template selected for upload:", { selectedUpload, selectedTemplate })
    } catch (err) {
      console.error("[v0] Failed to select template:", err)
      setError("Failed to select template. Please try again.")
    }
  }

  const updateMapping = (index: number, field: keyof ColumnMapping, value: string | boolean) => {
    setMappings((prev) => prev.map((mapping, i) => (i === index ? { ...mapping, [field]: value } : mapping)))
  }

  const applyMappings = async () => {
    if (!selectedUpload || !isConfigurationValid) return

    try {
      setIsProcessing(true)

      // First select the template
      await selectTemplate()

      // Then set the column mappings
      const mappingData = mappings.reduce(
        (acc, mapping) => {
          if (mapping.source_column && mapping.target_column) {
            acc[mapping.source_column] = {
              target_column: mapping.target_column,
              transform_function: mapping.transform_function || null,
            }
          }
          return acc
        },
        {} as Record<string, any>,
      )

      await apiClient.setColumnMappings(selectedUpload, mappingData)
      console.log("[v0] Column mappings applied:", mappingData)

      // Show success message
      setError(null)
      alert("Column mappings applied successfully! The file will now be processed through the ETL pipeline.")
    } catch (err) {
      console.error("[v0] Failed to apply mappings:", err)
      setError("Failed to apply mappings. Please try again.")
    } finally {
      setIsProcessing(false)
    }
  }

  const isConfigurationValid =
    mappings.every((m) => m.is_valid) &&
    targetColumns
      .filter((tc) => tc.is_required)
      .every((tc) => mappings.some((m) => m.target_column === tc.name && m.source_column))

  if (loading && !sourceColumns.length) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Shuffle className="h-5 w-5" />
            <span>Column Mapping</span>
          </CardTitle>
          <CardDescription>
            Map source file columns to target template columns and configure data transformations
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* File and Template Selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Select Upload</label>
              <Select value={selectedUpload} onValueChange={setSelectedUpload}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose uploaded file" />
                </SelectTrigger>
                <SelectContent>
                  {uploads.map((upload) => (
                    <SelectItem key={upload.id} value={upload.id}>
                      <div className="flex items-center space-x-2">
                        <FileText className="h-4 w-4" />
                        <span>{upload.filename}</span>
                        <span className="text-xs text-muted-foreground">({upload.uploaded_at})</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">Select Template</label>
              <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose target template" />
                </SelectTrigger>
                <SelectContent>
                  {templates.map((template) => (
                    <SelectItem key={template.id} value={template.id}>
                      <div className="flex items-center space-x-2">
                        <Database className="h-4 w-4" />
                        <span>{template.name}</span>
                        <span className="text-xs text-muted-foreground">({template.target_table})</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {selectedUpload && selectedTemplate && sourceColumns.length > 0 && (
            <>
              {/* Mapping Configuration */}
              <div className="border border-border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-1/3">Source Column</TableHead>
                      <TableHead className="w-16 text-center"></TableHead>
                      <TableHead className="w-1/3">Target Column</TableHead>
                      <TableHead className="w-1/6">Transform</TableHead>
                      <TableHead className="w-16">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mappings.map((mapping, index) => {
                      const sourceCol = sourceColumns.find((sc) => sc.name === mapping.source_column)
                      const targetCol = targetColumns.find((tc) => tc.name === mapping.target_column)

                      return (
                        <TableRow key={index}>
                          <TableCell>
                            <div className="space-y-1">
                              <Select
                                value={mapping.source_column}
                                onValueChange={(value) => updateMapping(index, "source_column", value)}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="Select source column" />
                                </SelectTrigger>
                                <SelectContent>
                                  {sourceColumns.map((col) => (
                                    <SelectItem key={col.name} value={col.name}>
                                      <div>
                                        <div className="font-medium">{col.name}</div>
                                        <div className="text-xs text-muted-foreground">
                                          {col.type} • Sample: {col.sample_data?.[0] || "N/A"}
                                        </div>
                                      </div>
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {sourceCol && (
                                <div className="text-xs text-muted-foreground">
                                  Sample: {sourceCol.sample_data?.join(", ") || "No sample data"}
                                </div>
                              )}
                            </div>
                          </TableCell>

                          <TableCell className="text-center">
                            <ArrowRight className="h-4 w-4 text-muted-foreground" />
                          </TableCell>

                          <TableCell>
                            <div className="space-y-1">
                              <Select
                                value={mapping.target_column}
                                onValueChange={(value) => updateMapping(index, "target_column", value)}
                              >
                                <SelectTrigger>
                                  <SelectValue placeholder="Select target column" />
                                </SelectTrigger>
                                <SelectContent>
                                  {targetColumns.map((col) => (
                                    <SelectItem key={col.name} value={col.name}>
                                      <div className="flex items-center justify-between w-full">
                                        <span>{col.name}</span>
                                        <div className="flex items-center space-x-1">
                                          <Badge variant="outline" className="text-xs">
                                            {col.data_type}
                                          </Badge>
                                          {col.is_required && (
                                            <Badge variant="destructive" className="text-xs">
                                              Required
                                            </Badge>
                                          )}
                                        </div>
                                      </div>
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              {targetCol && (
                                <div className="flex items-center space-x-2 text-xs">
                                  <Badge variant="outline">{targetCol.data_type}</Badge>
                                  {targetCol.processing_type !== "none" && (
                                    <Badge variant="secondary">{targetCol.processing_type}</Badge>
                                  )}
                                  {targetCol.is_required && <Badge variant="destructive">Required</Badge>}
                                </div>
                              )}
                            </div>
                          </TableCell>

                          <TableCell>
                            <Select
                              value={mapping.transform_function || "none"}
                              onValueChange={(value) =>
                                updateMapping(index, "transform_function", value === "none" ? undefined : value)
                              }
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="none">None</SelectItem>
                                <SelectItem value="upper">Uppercase</SelectItem>
                                <SelectItem value="lower">Lowercase</SelectItem>
                                <SelectItem value="trim">Trim</SelectItem>
                                <SelectItem value="title">Title Case</SelectItem>
                              </SelectContent>
                            </Select>
                          </TableCell>

                          <TableCell>
                            {mapping.is_valid ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <AlertCircle className="h-4 w-4 text-red-500" />
                            )}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>

              {/* Validation Status */}
              <Alert>
                {isConfigurationValid ? (
                  <>
                    <CheckCircle className="h-4 w-4" />
                    <AlertDescription>
                      Column mapping configuration is valid. All required fields are mapped.
                    </AlertDescription>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Please ensure all required target columns are mapped to source columns.
                    </AlertDescription>
                  </>
                )}
              </Alert>

              {/* Action Buttons */}
              <div className="flex justify-end space-x-2">
                <Button variant="outline">
                  <Settings className="h-4 w-4 mr-2" />
                  Preview Mapping
                </Button>
                <Button
                  disabled={!isConfigurationValid || isProcessing}
                  className="bg-primary text-primary-foreground"
                  onClick={applyMappings}
                >
                  {isProcessing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Apply Mapping & Process
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
