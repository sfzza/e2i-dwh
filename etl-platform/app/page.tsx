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

  // Mock data for dashboard
  const recentUploads = [
    { id: "1", filename: "customer_data.csv", status: "completed", timestamp: "2 hours ago" },
    { id: "2", filename: "sales_report.csv", status: "processing", timestamp: "1 hour ago" },
    { id: "3", filename: "inventory.csv", status: "failed", timestamp: "30 minutes ago" },
  ]

  const stats = {
    totalUploads: 1247,
    activeTemplates: 23,
    processedToday: 89,
    successRate: 94.2,
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
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Database className="h-8 w-8 text-primary" />
                <h1 className="text-2xl font-bold text-foreground">DataFlow ETL</h1>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <span className="text-sm text-muted-foreground">Welcome, {user.name}</span>
                <Badge
                  variant="secondary"
                  className={
                    user.role === "admin"
                      ? "bg-purple-100 text-purple-800 border-purple-200"
                      : "bg-blue-100 text-blue-800 border-blue-200"
                  }
                >
                  <Users className="h-3 w-3 mr-1" />
                  {user.role === "admin" ? "Administrator" : "User"}
                </Badge>
              </div>
              <Button variant="outline" size="sm" onClick={logout}>
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

          {/* Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Uploads</CardTitle>
                  <Upload className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.totalUploads.toLocaleString()}</div>
                  <p className="text-xs text-muted-foreground">+12% from last month</p>
                </CardContent>
              </Card>

              {user.role === "admin" && (
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">Active Templates</CardTitle>
                    <FileText className="h-4 w-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{stats.activeTemplates}</div>
                    <p className="text-xs text-muted-foreground">3 created this week</p>
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Processed Today</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.processedToday}</div>
                  <p className="text-xs text-muted-foreground">+5 from yesterday</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
                  <CheckCircle className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.successRate}%</div>
                  <Progress value={stats.successRate} className="mt-2" />
                </CardContent>
              </Card>
            </div>

            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Uploads</CardTitle>
                <CardDescription>Latest file processing activity</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentUploads.map((upload) => (
                    <div
                      key={upload.id}
                      className="flex items-center justify-between p-4 border border-border rounded-lg"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="flex-shrink-0">
                          {upload.status === "completed" && <CheckCircle className="h-5 w-5 text-green-500" />}
                          {upload.status === "processing" && <Clock className="h-5 w-5 text-yellow-500" />}
                          {upload.status === "failed" && <AlertCircle className="h-5 w-5 text-red-500" />}
                        </div>
                        <div>
                          <p className="font-medium text-foreground">{upload.filename}</p>
                          <p className="text-sm text-muted-foreground">{upload.timestamp}</p>
                        </div>
                      </div>
                      <Badge
                        variant={
                          upload.status === "completed"
                            ? "secondary"
                            : upload.status === "processing"
                              ? "outline"
                              : "destructive"
                        }
                        className={upload.status === "completed" ? "bg-green-100 text-green-800 border-green-200" : ""}
                      >
                        {upload.status}
                      </Badge>
                    </div>
                  ))}
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
