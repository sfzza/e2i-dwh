"use client"

import { useState, useCallback } from "react"
import { useDropzone } from "react-dropzone"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Upload, CheckCircle, AlertCircle, X, FileText } from "lucide-react"
import { apiClient } from "@/lib/api"
import { useAuth } from "@/lib/auth"

interface UploadFile {
  id: string
  file: File
  status: "pending" | "uploading" | "completed" | "error"
  progress: number
  error?: string
  uploadId?: string
}

export function FileUpload() {
  const { user } = useAuth()
  const [files, setFiles] = useState<UploadFile[]>([])
  const [isUploading, setIsUploading] = useState(false)

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      status: "pending" as const,
      progress: 0,
    }))
    setFiles((prev) => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/csv": [".csv"],
      "application/vnd.ms-excel": [".xls"],
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
    },
    multiple: true,
  })

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((file) => file.id !== id))
  }

  const uploadFiles = async () => {
    setIsUploading(true)

    for (const uploadFile of files.filter((f) => f.status === "pending")) {
      setFiles((prev) => prev.map((f) => (f.id === uploadFile.id ? { ...f, status: "uploading" } : f)))

      try {
        // Step 1: Upload file to Django backend
        const response = await apiClient.uploadFile(uploadFile.file, (progress) => {
          setFiles((prev) => prev.map((f) => (f.id === uploadFile.id ? { ...f, progress } : f)))
        })

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`)
        }

        const result = await response.json()

        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id ? { ...f, status: "completed", progress: 100, uploadId: result.upload_id } : f,
          ),
        )

        console.log("[v0] File uploaded successfully:", result)
      } catch (error) {
        console.error("[v0] Upload error:", error)
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id
              ? {
                  ...f,
                  status: "error",
                  error: error instanceof Error ? error.message : "Upload failed. Please try again.",
                }
              : f,
          ),
        )
      }
    }

    setIsUploading(false)
  }

  const pendingFiles = files.filter((f) => f.status === "pending")
  const completedFiles = files.filter((f) => f.status === "completed")

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Upload className="h-5 w-5" />
            <span>File Upload</span>
          </CardTitle>
          <CardDescription>
            Upload CSV, XLS, or XLSX files for processing. Files will be validated and processed through your configured
            templates.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Drop Zone */}
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragActive ? "border-accent bg-accent/10" : "border-border hover:border-accent/50"
            }`}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center space-y-4">
              <div className="p-4 bg-muted rounded-full">
                <Upload className="h-8 w-8 text-muted-foreground" />
              </div>
              <div>
                <p className="text-lg font-medium">{isDragActive ? "Drop files here" : "Drag & drop files here"}</p>
                <p className="text-sm text-muted-foreground">or click to browse files</p>
              </div>
              <Badge variant="secondary">CSV, XLS, XLSX supported</Badge>
            </div>
          </div>

          {/* File List */}
          {files.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Files ({files.length})</h3>
                {pendingFiles.length > 0 && (
                  <Button onClick={uploadFiles} disabled={isUploading} className="bg-primary text-primary-foreground">
                    {isUploading
                      ? "Uploading..."
                      : `Upload ${pendingFiles.length} file${pendingFiles.length > 1 ? "s" : ""}`}
                  </Button>
                )}
              </div>

              <div className="space-y-3">
                {files.map((uploadFile) => (
                  <div key={uploadFile.id} className="flex items-center space-x-4 p-4 border border-border rounded-lg">
                    <div className="flex-shrink-0">
                      <FileText className="h-8 w-8 text-muted-foreground" />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="font-medium truncate">{uploadFile.file.name}</p>
                        <div className="flex items-center space-x-2">
                          {uploadFile.status === "completed" && <CheckCircle className="h-5 w-5 text-green-500" />}
                          {uploadFile.status === "error" && <AlertCircle className="h-5 w-5 text-red-500" />}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(uploadFile.id)}
                            disabled={uploadFile.status === "uploading"}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>

                      <div className="flex items-center space-x-4 mt-2">
                        <p className="text-sm text-muted-foreground">
                          {(uploadFile.file.size / 1024 / 1024).toFixed(2)} MB
                        </p>
                        <Badge
                          variant={
                            uploadFile.status === "completed"
                              ? "secondary"
                              : uploadFile.status === "error"
                                ? "destructive"
                                : uploadFile.status === "uploading"
                                  ? "outline"
                                  : "outline"
                          }
                          className={
                            uploadFile.status === "completed" ? "bg-green-100 text-green-800 border-green-200" : ""
                          }
                        >
                          {uploadFile.status}
                        </Badge>
                        {uploadFile.uploadId && (
                          <Badge variant="outline" className="text-xs">
                            ID: {uploadFile.uploadId.slice(0, 8)}...
                          </Badge>
                        )}
                      </div>

                      {uploadFile.status === "uploading" && <Progress value={uploadFile.progress} className="mt-2" />}

                      {uploadFile.error && (
                        <Alert className="mt-2">
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>{uploadFile.error}</AlertDescription>
                        </Alert>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Instructions */}
          {completedFiles.length > 0 && (
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                {completedFiles.length} file{completedFiles.length > 1 ? "s" : ""} uploaded successfully. You can now
                proceed to the Mapping tab to configure column mappings.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
