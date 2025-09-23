"use client"

import { useAuth } from "@/lib/auth"
import { LoginForm } from "@/components/login-form"
import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import {
  Upload,
  Database,
  Settings,
  BarChart3,
  FileText,
  CheckCircle,
  Clock,
  AlertCircle,
  Users,
  Activity,
  LogOut,
} from "lucide-react"
import { FileUpload } from "@/components/file-upload"
import { TemplateManagement } from "@/components/template-management"
import { ColumnMapping } from "@/components/column-mapping"
import { DataReporting } from "@/components/data-reporting"

export default function ETLPlatform() {
  const { user, logout, isLoading } = useAuth()
  const [activeTab, setActiveTab] = useState("dashboard")

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!user?.isAuthenticated) {
    return <LoginForm />
  }

  // Enhanced mock data for professional dashboard
  const recentUploads = [
    { id: "1", filename: "customer_data.csv", status: "completed", timestamp: "2 hours ago", size: "2.3 MB", rows: 15420 },
    { id: "2", filename: "sales_report.csv", status: "processing", timestamp: "1 hour ago", size: "5.1 MB", rows: 28950 },
    { id: "3", filename: "inventory.csv", status: "failed", timestamp: "30 minutes ago", size: "1.8 MB", rows: 8750 },
    { id: "4", filename: "financial_data.csv", status: "completed", timestamp: "4 hours ago", size: "3.7 MB", rows: 22100 },
    { id: "5", filename: "product_catalog.csv", status: "processing", timestamp: "15 minutes ago", size: "4.2 MB", rows: 18650 },
  ]

  const stats = {
    totalUploads: 1247,
    activeTemplates: 23,
    processedToday: 89,
    successRate: 94.2,
    totalDataProcessed: "2.4 TB",
    avgProcessingTime: "2.3s",
    systemUptime: "99.9%",
    activeConnections: 156,
  }

  const availableTabs = [
    { id: "dashboard", label: "Dashboard", icon: BarChart3, roles: ["admin", "user"] },
    { id: "upload", label: "Upload", icon: Upload, roles: ["admin", "user"] },
    { id: "templates", label: "Templates", icon: FileText, roles: ["admin"] },
    { id: "mapping", label: "Mapping", icon: Settings, roles: ["admin", "user"] },
    { id: "reports", label: "Reports", icon: BarChart3, roles: ["admin", "user"] },
  ].filter((tab) => tab.roles.includes(user.role))

  return (
    <div className="min-h-screen bg-background">
      {/* Enhanced Professional Header */}
      <header className="border-b border-border bg-card shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-gradient-to-br from-primary to-secondary rounded-lg">
                  <Database className="h-6 w-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-foreground">DataFlow ETL</h1>
                  <p className="text-xs text-muted-foreground">Enterprise Data Warehouse Platform</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              {/* System Status Indicator */}
              <div className="flex items-center space-x-2 px-3 py-1 bg-green-50 border border-green-200 rounded-full">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-medium text-green-700">System Online</span>
              </div>
              
              {/* User Info */}
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <div className="text-sm font-medium text-foreground">{user.name}</div>
                  <div className="text-xs text-muted-foreground">Last active: now</div>
                </div>
                <Badge
                  variant="secondary"
                  className={
                    user.role === "admin"
                      ? "bg-gradient-to-r from-purple-100 to-purple-200 text-purple-800 border-purple-300"
                      : "bg-gradient-to-r from-blue-100 to-blue-200 text-blue-800 border-blue-300"
                  }
                >
                  <Users className="h-3 w-3 mr-1" />
                  {user.role === "admin" ? "Administrator" : "User"}
                </Badge>
              </div>
              
              <Button 
                variant="outline" 
                size="sm" 
                onClick={logout}
                className="hover:bg-red-50 hover:border-red-200 hover:text-red-700 transition-colors"
              >
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className={`grid w-full grid-cols-${availableTabs.length}`}>
            {availableTabs.map((tab) => {
              const Icon = tab.icon
              return (
                <TabsTrigger key={tab.id} value={tab.id} className="flex items-center space-x-2">
                  <Icon className="h-4 w-4" />
                  <span>{tab.label}</span>
                </TabsTrigger>
              )
            })}
          </TabsList>

          {/* Enhanced Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-6">
            {/* Welcome Section */}
            <div className="bg-gradient-to-r from-primary/10 to-secondary/10 rounded-lg p-6 border border-primary/20">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-foreground mb-2">
                    Welcome back, {user.name}! 👋
                  </h2>
                  <p className="text-muted-foreground">
                    Your data warehouse is running smoothly. Here's what's happening today.
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-sm text-muted-foreground">System Status</div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-medium text-green-600">All Systems Operational</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Enhanced Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="relative overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Uploads</CardTitle>
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Upload className="h-4 w-4 text-blue-600" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.totalUploads.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <span className="text-green-500">↗</span> +12% from last month
                  </p>
                </CardContent>
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-blue-500/10 to-transparent rounded-bl-full"></div>
              </Card>

              <Card className="relative overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Data Processed</CardTitle>
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Database className="h-4 w-4 text-green-600" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.totalDataProcessed}</div>
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <span className="text-green-500">↗</span> +8% this week
                  </p>
                </CardContent>
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-green-500/10 to-transparent rounded-bl-full"></div>
              </Card>

              {user.role === "admin" && (
                <Card className="relative overflow-hidden">
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Active Templates</CardTitle>
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <FileText className="h-4 w-4 text-purple-600" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stats.activeTemplates}</div>
                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                      <span className="text-green-500">↗</span> 3 created this week
                    </p>
                  </CardContent>
                  <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-purple-500/10 to-transparent rounded-bl-full"></div>
                </Card>
              )}

              <Card className="relative overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                  <div className="p-2 bg-emerald-100 rounded-lg">
                    <CheckCircle className="h-4 w-4 text-emerald-600" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.successRate}%</div>
                  <Progress value={stats.successRate} className="mt-2" />
                  <p className="text-xs text-muted-foreground mt-1">Excellent performance</p>
                </CardContent>
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-emerald-500/10 to-transparent rounded-bl-full"></div>
              </Card>

              <Card className="relative overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Processing Speed</CardTitle>
                  <div className="p-2 bg-orange-100 rounded-lg">
                    <Activity className="h-4 w-4 text-orange-600" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.avgProcessingTime}</div>
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <span className="text-green-500">↗</span> 15% faster than last month
                  </p>
                </CardContent>
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-orange-500/10 to-transparent rounded-bl-full"></div>
              </Card>

              <Card className="relative overflow-hidden">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">System Uptime</CardTitle>
                  <div className="p-2 bg-cyan-100 rounded-lg">
                    <Activity className="h-4 w-4 text-cyan-600" />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.systemUptime}</div>
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <span className="text-green-500">●</span> 30 days without downtime
                  </p>
                </CardContent>
                <div className="absolute top-0 right-0 w-20 h-20 bg-gradient-to-br from-cyan-500/10 to-transparent rounded-bl-full"></div>
              </Card>
            </div>

            {/* Enhanced Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Recent Uploads
                </CardTitle>
                <CardDescription>Latest file processing activity and system performance</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentUploads.map((upload) => (
                    <div
                      key={upload.id}
                      className="flex items-center justify-between p-4 border border-border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0">
                          {upload.status === "completed" && (
                            <div className="p-2 bg-green-100 rounded-full">
                              <CheckCircle className="h-4 w-4 text-green-600" />
                            </div>
                          )}
                          {upload.status === "processing" && (
                            <div className="p-2 bg-yellow-100 rounded-full">
                              <Clock className="h-4 w-4 text-yellow-600 animate-pulse" />
                            </div>
                          )}
                          {upload.status === "failed" && (
                            <div className="p-2 bg-red-100 rounded-full">
                              <AlertCircle className="h-4 w-4 text-red-600" />
                            </div>
                          )}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-foreground">{upload.filename}</p>
                            <Badge
                              variant={
                                upload.status === "completed"
                                  ? "secondary"
                                  : upload.status === "processing"
                                    ? "outline"
                                    : "destructive"
                              }
                              className={
                                upload.status === "completed" 
                                  ? "bg-green-100 text-green-800 border-green-200" 
                                  : upload.status === "processing"
                                    ? "bg-yellow-100 text-yellow-800 border-yellow-200"
                                    : ""
                              }
                            >
                              {upload.status}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                            <span>📅 {upload.timestamp}</span>
                            <span>📊 {upload.size}</span>
                            <span>📋 {upload.rows.toLocaleString()} rows</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {upload.status === "processing" && (
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                            <span>Processing...</span>
                          </div>
                        )}
                        {upload.status === "completed" && (
                          <div className="flex items-center gap-2 text-sm text-green-600">
                            <CheckCircle className="h-4 w-4" />
                            <span>Complete</span>
                          </div>
                        )}
                        {upload.status === "failed" && (
                          <div className="flex items-center gap-2 text-sm text-red-600">
                            <AlertCircle className="h-4 w-4" />
                            <span>Failed</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Performance Summary */}
                <div className="mt-6 pt-4 border-t border-border">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-green-600">
                        {recentUploads.filter(u => u.status === "completed").length}
                      </div>
                      <div className="text-sm text-muted-foreground">Completed</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-yellow-600">
                        {recentUploads.filter(u => u.status === "processing").length}
                      </div>
                      <div className="text-sm text-muted-foreground">Processing</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-red-600">
                        {recentUploads.filter(u => u.status === "failed").length}
                      </div>
                      <div className="text-sm text-muted-foreground">Failed</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Upload Tab */}
          <TabsContent value="upload">
            <FileUpload />
          </TabsContent>

          {/* Templates Tab - Admin Only */}
          {user.role === "admin" && (
            <TabsContent value="templates">
              <TemplateManagement />
            </TabsContent>
          )}

          {/* Mapping Tab */}
          <TabsContent value="mapping">
            <ColumnMapping />
          </TabsContent>

          {/* Reports Tab */}
          <TabsContent value="reports">
            <DataReporting />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
