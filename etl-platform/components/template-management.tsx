"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  Plus,
  Edit,
  Trash2,
  FileText,
  Database,
  Settings,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
} from "lucide-react"
import { apiClient } from "@/lib/api"
import { useAuth } from "@/lib/auth"

interface Template {
  id: string
  name: string
  description: string
  target_table: string
  is_active: boolean
  column_count: number
  last_used?: string
  created_by: string
  created_at: string
}

interface TemplateColumn {
  id: string
  name: string
  data_type: string
  processing_type: string
  is_required: boolean
  max_length?: number
}

export function TemplateManagement() {
  const { user } = useAuth()
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [templateColumns, setTemplateColumns] = useState<TemplateColumn[]>([])
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form states
  const [newTemplate, setNewTemplate] = useState({
    name: "",
    description: "",
    target_table: "",
  })

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getTemplates()
      setTemplates(response.templates || [])
      console.log("[v0] Templates loaded:", response)
    } catch (err) {
      console.error("[v0] Failed to load templates:", err)
      setError("Failed to load templates. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const createTemplate = async () => {
    if (!newTemplate.name || !newTemplate.target_table) {
      setError("Please fill in all required fields")
      return
    }

    try {
      setIsSubmitting(true)
      const response = await apiClient.createTemplate(newTemplate)
      console.log("[v0] Template created:", response)

      await loadTemplates() // Refresh the list
      setIsCreateDialogOpen(false)
      setNewTemplate({ name: "", description: "", target_table: "" })
      setError(null)
    } catch (err) {
      console.error("[v0] Failed to create template:", err)
      setError("Failed to create template. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  const deleteTemplate = async (id: string) => {
    if (!confirm("Are you sure you want to delete this template?")) return

    try {
      await apiClient.deleteTemplate(id)
      console.log("[v0] Template deleted:", id)
      await loadTemplates() // Refresh the list
    } catch (err) {
      console.error("[v0] Failed to delete template:", err)
      setError("Failed to delete template. Please try again.")
    }
  }

  const toggleTemplateStatus = async (id: string) => {
    try {
      await apiClient.activateTemplate(id)
      console.log("[v0] Template status toggled:", id)
      await loadTemplates() // Refresh the list
    } catch (err) {
      console.error("[v0] Failed to toggle template status:", err)
      setError("Failed to update template status. Please try again.")
    }
  }

  const loadTemplateUsage = async (templateId: string) => {
    try {
      const response = await apiClient.getTemplateUsage(templateId)
      console.log("[v0] Template usage:", response)
      // You can use this data to show usage statistics
    } catch (err) {
      console.error("[v0] Failed to load template usage:", err)
    }
  }

  if (loading) {
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
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>Template Management</span>
              </CardTitle>
              <CardDescription>
                Create and manage data processing templates for consistent ETL operations
              </CardDescription>
            </div>
            <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
              <DialogTrigger asChild>
                <Button className="bg-primary text-primary-foreground">
                  <Plus className="h-4 w-4 mr-2" />
                  Create Template
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Create New Template</DialogTitle>
                  <DialogDescription>
                    Define a new data processing template with column mappings and transformations
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="template-name">Template Name *</Label>
                      <Input
                        id="template-name"
                        placeholder="Enter template name"
                        value={newTemplate.name}
                        onChange={(e) => setNewTemplate((prev) => ({ ...prev, name: e.target.value }))}
                      />
                    </div>
                    <div>
                      <Label htmlFor="target-table">Target Table *</Label>
                      <Input
                        id="target-table"
                        placeholder="Enter target table name"
                        value={newTemplate.target_table}
                        onChange={(e) => setNewTemplate((prev) => ({ ...prev, target_table: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Textarea
                      id="description"
                      placeholder="Describe the template purpose"
                      value={newTemplate.description}
                      onChange={(e) => setNewTemplate((prev) => ({ ...prev, description: e.target.value }))}
                    />
                  </div>
                  <div className="flex justify-end space-x-2">
                    <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button
                      className="bg-primary text-primary-foreground"
                      onClick={createTemplate}
                      disabled={isSubmitting}
                    >
                      {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Create Template
                    </Button>
                  </div>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {templates.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No templates found. Create your first template to get started.
              </div>
            ) : (
              templates.map((template) => (
                <div
                  key={template.id}
                  className="flex items-center justify-between p-4 border border-border rounded-lg"
                >
                  <div className="flex items-center space-x-4">
                    <div className="flex-shrink-0">
                      <Database className="h-8 w-8 text-muted-foreground" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="font-medium text-foreground">{template.name}</h3>
                        <Badge variant={template.is_active ? "secondary" : "outline"}>
                          {template.is_active ? "active" : "inactive"}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{template.description}</p>
                      <div className="flex items-center space-x-4 mt-1 text-xs text-muted-foreground">
                        <span>Table: {template.target_table}</span>
                        <span>Columns: {template.column_count || 0}</span>
                        {template.last_used && <span>Last used: {template.last_used}</span>}
                        <span>Created by: {template.created_by}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setSelectedTemplate(template)
                        setIsEditDialogOpen(true)
                        loadTemplateUsage(template.id)
                      }}
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      Edit
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => toggleTemplateStatus(template.id)}>
                      {template.is_active ? (
                        <>
                          <Clock className="h-4 w-4 mr-1" />
                          Deactivate
                        </>
                      ) : (
                        <>
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Activate
                        </>
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => deleteTemplate(template.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Template Details Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Template: {selectedTemplate?.name}</DialogTitle>
            <DialogDescription>Configure column mappings and processing rules for this template</DialogDescription>
          </DialogHeader>

          {selectedTemplate && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="edit-name">Template Name</Label>
                  <Input id="edit-name" defaultValue={selectedTemplate.name} />
                </div>
                <div>
                  <Label htmlFor="edit-table">Target Table</Label>
                  <Input id="edit-table" defaultValue={selectedTemplate.target_table} />
                </div>
              </div>

              <div>
                <Label htmlFor="edit-description">Description</Label>
                <Textarea id="edit-description" defaultValue={selectedTemplate.description} />
              </div>

              <div>
                <h3 className="text-lg font-medium mb-4">Column Configuration</h3>
                {templateColumns.length === 0 ? (
                  <div className="text-center py-4 text-muted-foreground">No columns configured for this template.</div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Column Name</TableHead>
                        <TableHead>Data Type</TableHead>
                        <TableHead>Processing</TableHead>
                        <TableHead>Required</TableHead>
                        <TableHead>Max Length</TableHead>
                        <TableHead>Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {templateColumns.map((column) => (
                        <TableRow key={column.id}>
                          <TableCell className="font-medium">{column.name}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{column.data_type}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={column.processing_type === "none" ? "secondary" : "default"}>
                              {column.processing_type}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {column.is_required ? (
                              <CheckCircle className="h-4 w-4 text-green-500" />
                            ) : (
                              <span className="text-muted-foreground">Optional</span>
                            )}
                          </TableCell>
                          <TableCell>{column.max_length || "N/A"}</TableCell>
                          <TableCell>
                            <Button variant="ghost" size="sm">
                              <Settings className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>

              <div className="flex justify-end space-x-2">
                <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                  Cancel
                </Button>
                <Button className="bg-primary text-primary-foreground">Save Changes</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
