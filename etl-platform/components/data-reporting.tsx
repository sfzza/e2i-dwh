"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  BarChart3,
  Download,
  Play,
  Database,
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  Eye,
  Loader2,
} from "lucide-react"
import { apiClient } from "@/lib/api"
import { useAuth } from "@/lib/auth"

interface Dataset {
  name: string
  table: string
  row_count: number
  last_updated: string
}

interface QueryResult {
  id: string
  query: string
  status: "running" | "completed" | "failed"
  row_count?: number
  execution_time?: string
  created_at: string
  error_message?: string
}

interface QueryLimits {
  max_rows: number
  timeout_seconds: number
  max_query_length: number
}

export function DataReporting() {
  const { user } = useAuth()
  const [selectedDataset, setSelectedDataset] = useState<string>("")
  const [sqlQuery, setSqlQuery] = useState<string>("")
  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [queryResults, setQueryResults] = useState<QueryResult[]>([])
  const [queryLimits, setQueryLimits] = useState<QueryLimits | null>(null)
  const [sampleData, setSampleData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isExecuting, setIsExecuting] = useState(false)

  useEffect(() => {
    loadInitialData()
  }, [])

  const loadInitialData = async () => {
    try {
      setLoading(true)

      // Load available datasets
      const datasetsResponse = await apiClient.getDatasets()
      setDatasets(datasetsResponse.datasets || [])

      // Load query limits
      const limitsResponse = await apiClient.getQueryLimits()
      setQueryLimits(limitsResponse)

      console.log("[v0] Loaded datasets and limits:", { datasetsResponse, limitsResponse })
    } catch (err) {
      console.error("[v0] Failed to load initial data:", err)
      setError("Failed to load datasets. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const loadSampleData = async (datasetName: string) => {
    try {
      setLoading(true)
      const response = await apiClient.getDatasetSample(datasetName)
      setSampleData(response.sample_data || [])
      console.log("[v0] Loaded sample data:", response)
    } catch (err) {
      console.error("[v0] Failed to load sample data:", err)
      setError("Failed to load sample data. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const executeQuery = async () => {
    if (!sqlQuery.trim()) return

    try {
      setIsExecuting(true)
      setError(null)

      const response = await apiClient.runQuery(sqlQuery)

      const newQuery: QueryResult = {
        id: response.query_id || Date.now().toString(),
        query: sqlQuery,
        status: "running",
        created_at: "Just now",
      }

      setQueryResults((prev) => [newQuery, ...prev])
      console.log("[v0] Query submitted:", response)

      // Poll for query status (simplified - in real app you'd use websockets or polling)
      setTimeout(async () => {
        try {
          const statusResponse = await apiClient.getReportStatus(newQuery.id)
          setQueryResults((prev) =>
            prev.map((q) =>
              q.id === newQuery.id
                ? {
                    ...q,
                    status: statusResponse.status,
                    row_count: statusResponse.row_count,
                    execution_time: statusResponse.execution_time,
                    error_message: statusResponse.error_message,
                  }
                : q,
            ),
          )
        } catch (err) {
          console.error("[v0] Failed to get query status:", err)
        }
      }, 2000)
    } catch (err) {
      console.error("[v0] Failed to execute query:", err)
      setError("Failed to execute query. Please try again.")
    } finally {
      setIsExecuting(false)
    }
  }

  const explainQuery = async () => {
    if (!sqlQuery.trim()) return

    try {
      const response = await apiClient.explainQuery(sqlQuery)
      alert(`Query Explanation:\n${response.explanation || "No explanation available"}`)
      console.log("[v0] Query explanation:", response)
    } catch (err) {
      console.error("[v0] Failed to explain query:", err)
      setError("Failed to explain query. Please try again.")
    }
  }

  const downloadReport = async (reportId: string) => {
    try {
      const blob = await apiClient.downloadReport(reportId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.style.display = "none"
      a.href = url
      a.download = `report_${reportId}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      console.log("[v0] Report downloaded:", reportId)
    } catch (err) {
      console.error("[v0] Failed to download report:", err)
      setError("Failed to download report. Please try again.")
    }
  }

  if (loading && !datasets.length) {
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

      <Tabs defaultValue="datasets" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="datasets">Datasets</TabsTrigger>
          <TabsTrigger value="query">Query Builder</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>

        {/* Datasets Tab */}
        <TabsContent value="datasets">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Database className="h-5 w-5" />
                <span>Available Datasets</span>
              </CardTitle>
              <CardDescription>Browse and explore processed datasets in your data warehouse</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {datasets.map((dataset) => (
                  <Card key={dataset.name} className="cursor-pointer hover:shadow-md transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-medium text-foreground">{dataset.name}</h3>
                        <Badge variant="outline">{dataset.table}</Badge>
                      </div>
                      <div className="space-y-1 text-sm text-muted-foreground">
                        <p>{dataset.row_count?.toLocaleString() || 0} rows</p>
                        <p>Updated {dataset.last_updated}</p>
                      </div>
                      <div className="flex justify-end mt-3 space-x-2">
                        <Button variant="outline" size="sm" onClick={() => loadSampleData(dataset.table)}>
                          <Eye className="h-4 w-4 mr-1" />
                          Preview
                        </Button>
                        <Button variant="outline" size="sm">
                          <Download className="h-4 w-4 mr-1" />
                          Export
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* Sample Data Preview */}
              {sampleData.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Sample Data Preview</CardTitle>
                    <CardDescription>First few rows from the selected dataset</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            {Object.keys(sampleData[0] || {}).map((key) => (
                              <TableHead key={key}>{key}</TableHead>
                            ))}
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {sampleData.slice(0, 5).map((row, index) => (
                            <TableRow key={index}>
                              {Object.values(row).map((value: any, cellIndex) => (
                                <TableCell key={cellIndex} className="font-mono text-xs">
                                  {String(value)}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Query Builder Tab */}
        <TabsContent value="query">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="h-5 w-5" />
                <span>SQL Query Builder</span>
              </CardTitle>
              <CardDescription>Execute custom SQL queries against your processed datasets</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="dataset-select">Select Dataset</Label>
                <Select value={selectedDataset} onValueChange={setSelectedDataset}>
                  <SelectTrigger>
                    <SelectValue placeholder="Choose a dataset to query" />
                  </SelectTrigger>
                  <SelectContent>
                    {datasets.map((dataset) => (
                      <SelectItem key={dataset.name} value={dataset.table}>
                        {dataset.name} ({dataset.table})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="sql-query">SQL Query</Label>
                <Textarea
                  id="sql-query"
                  placeholder="Enter your SQL query here..."
                  value={sqlQuery}
                  onChange={(e) => setSqlQuery(e.target.value)}
                  className="font-mono text-sm min-h-[120px]"
                />
              </div>

              <div className="flex justify-between items-center">
                <div className="text-sm text-muted-foreground">
                  {queryLimits && (
                    <>
                      Query limits: {queryLimits.max_rows.toLocaleString()} rows max, {queryLimits.timeout_seconds}s
                      timeout
                    </>
                  )}
                </div>
                <div className="space-x-2">
                  <Button variant="outline" onClick={explainQuery} disabled={!sqlQuery.trim()}>
                    <FileText className="h-4 w-4 mr-2" />
                    Explain Query
                  </Button>
                  <Button onClick={executeQuery} disabled={!sqlQuery.trim() || isExecuting}>
                    {isExecuting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    <Play className="h-4 w-4 mr-2" />
                    Execute Query
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reports Tab */}
        <TabsContent value="reports">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>Query History & Reports</span>
              </CardTitle>
              <CardDescription>View executed queries and download results</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {queryResults.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    No queries executed yet. Use the Query Builder to run your first query.
                  </div>
                ) : (
                  queryResults.map((result) => (
                    <div
                      key={result.id}
                      className="flex items-center justify-between p-4 border border-border rounded-lg"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0">
                          {result.status === "completed" && <CheckCircle className="h-5 w-5 text-green-500" />}
                          {result.status === "running" && <Clock className="h-5 w-5 text-yellow-500" />}
                          {result.status === "failed" && <AlertCircle className="h-5 w-5 text-red-500" />}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="font-mono text-sm truncate">{result.query}</p>
                          <div className="flex items-center space-x-4 mt-1 text-xs text-muted-foreground">
                            <span>{result.created_at}</span>
                            {result.row_count !== undefined && <span>{result.row_count.toLocaleString()} rows</span>}
                            {result.execution_time && <span>{result.execution_time}</span>}
                          </div>
                          {result.error_message && <p className="text-xs text-red-500 mt-1">{result.error_message}</p>}
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge
                          variant={
                            result.status === "completed"
                              ? "secondary"
                              : result.status === "running"
                                ? "outline"
                                : "destructive"
                          }
                          className={
                            result.status === "completed" ? "bg-green-100 text-green-800 border-green-200" : ""
                          }
                        >
                          {result.status}
                        </Badge>
                        {result.status === "completed" && (
                          <Button variant="outline" size="sm" onClick={() => downloadReport(result.id)}>
                            <Download className="h-4 w-4 mr-1" />
                            Download
                          </Button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
