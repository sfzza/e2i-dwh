import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { toast } from 'react-hot-toast';
import { ArrowLeft, Play, CheckCircle, AlertCircle, FileText } from 'lucide-react';
import { useTemplateStore } from '../store/templateStore';
import { useUploadStore } from '../store/uploadStore';
import { useAuth } from '../hooks/useAuth';
import { apiService } from '../services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ColumnMappingInterface } from '../components/ColumnMappingInterface';

export const ProcessingPage: React.FC = () => {
  const { uploadId } = useParams<{ uploadId: string }>();
  const navigate = useNavigate();
  const { templates, fetchTemplates } = useTemplateStore();
  const { 
    processingStatus, 
    selectTemplate, 
    processFile, 
    getProcessingStatus,
    isLoading 
  } = useUploadStore();
  const { isAuthenticated, user, isLoading: authLoading } = useAuth();
  
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadData, setUploadData] = useState<any>(null);
  const [uploadLoading, setUploadLoading] = useState(true);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Check authentication
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      toast.error('Please log in to process files');
      navigate('/login');
    }
  }, [isAuthenticated, authLoading, navigate]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  // Fetch upload data when component mounts
  useEffect(() => {
    const fetchUploadData = async () => {
      if (!uploadId) return;
      
      setUploadLoading(true);
      setUploadError(null);
      
      try {
        const status = await apiService.getUploadStatus(uploadId);
        setUploadData(status);
        setUploadLoading(false);
      } catch (error: any) {
        console.error('Failed to fetch upload data:', error);
        setUploadError(error.message || 'Failed to load upload data');
        setUploadLoading(false);
      }
    };

    fetchUploadData();
  }, [uploadId]);

  useEffect(() => {
    if (uploadId && uploadData) {
      // Check if we already have processing status
      getProcessingStatus(uploadId);
    }
  }, [uploadId, uploadData, getProcessingStatus]);

  const activeTemplates = templates.filter(t => t.isActive);
  const selectedTemplate = templates.find(t => t.id === selectedTemplateId);

  const handleTemplateSelect = async () => {
    if (!selectedTemplateId || !uploadId) return;
    
    try {
      await selectTemplate(uploadId, selectedTemplateId);
      toast.success('Template selected successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to select template');
    }
  };

  const handleProcess = async () => {
    if (!uploadId || !selectedTemplateId || !mappings) return;
    
    setIsProcessing(true);
    try {
      const columnMappings = Object.entries(mappings).map(([source, target]) => ({
        sourceColumn: source,
        targetColumn: target,
        transformFunction: 'none',
        transformParams: {}
      }));

      await processFile(uploadId, {
        templateId: selectedTemplateId,
        mappings: columnMappings,
      });
      
      toast.success('Processing started successfully');
    } catch (error: any) {
      toast.error(error.message || 'Failed to start processing');
    } finally {
      setIsProcessing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success">Completed</Badge>;
      case 'processing':
        return <Badge variant="warning">Processing</Badge>;
      case 'failed':
        return <Badge variant="error">Failed</Badge>;
      default:
        return <Badge variant="default">Pending</Badge>;
    }
  };

  // Show loading while checking authentication
  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Show access denied if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center py-12">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Access Denied</h1>
          <p className="text-gray-600 mb-6">You need to be logged in to process files.</p>
          <Button onClick={() => navigate('/login')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Go to Login
          </Button>
        </div>
      </div>
    );
  }

  // Show loading while fetching upload data
  if (uploadLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center py-12">
          <LoadingSpinner size="lg" />
          <p className="text-gray-600 mt-4">Loading upload data...</p>
        </div>
      </div>
    );
  }

  // Show error if upload not found or failed to load
  if (uploadError || !uploadData) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center py-12">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-4">Upload Not Found</h1>
          <p className="text-gray-600 mb-6">
            {uploadError || "The upload you're looking for doesn't exist."}
          </p>
          <Button onClick={() => navigate('/upload')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Upload
          </Button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }


  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="outline" onClick={() => navigate('/uploads')}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Uploads
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Process File</h1>
            <p className="text-gray-600">{uploadData.fileName}</p>
            {user && (
              <p className="text-sm text-gray-500 mt-1">
                User: <span className="font-medium">{user.username}</span> ({user.role})
              </p>
            )}
          </div>
        </div>
        {getStatusBadge(uploadData.status)}
      </div>

      {/* Processing Status */}
      {processingStatus && (
        <Card>
          <CardHeader>
            <CardTitle>Processing Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">Status:</span>
                {getStatusBadge(processingStatus.status)}
              </div>
              
              {processingStatus.progress > 0 && (
                <div>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Progress</span>
                    <span>{processingStatus.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${processingStatus.progress}%` }}
                    />
                  </div>
                </div>
              )}
              
              {processingStatus.message && (
                <div className="flex items-start">
                  <CheckCircle className="h-5 w-5 text-green-500 mr-2 mt-0.5" />
                  <p className="text-sm text-gray-600">{processingStatus.message}</p>
                </div>
              )}
              
              {processingStatus.errorMessage && (
                <div className="flex items-start">
                  <AlertCircle className="h-5 w-5 text-red-500 mr-2 mt-0.5" />
                  <p className="text-sm text-red-600">{processingStatus.errorMessage}</p>
                </div>
              )}
              
              {processingStatus.result && (
                <div className="grid grid-cols-3 gap-4 pt-4 border-t">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-600">
                      {processingStatus.result.rowsProcessed}
                    </p>
                    <p className="text-sm text-gray-600">Rows Processed</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-yellow-600">
                      {processingStatus.result.rowsSkipped}
                    </p>
                    <p className="text-sm text-gray-600">Rows Skipped</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-blue-600">
                      {processingStatus.result.processingTime}s
                    </p>
                    <p className="text-sm text-gray-600">Processing Time</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Template Selection */}
      {!uploadData.templateId && (
        <Card>
          <CardHeader>
            <CardTitle>Select Template</CardTitle>
            <CardDescription>
              Choose a template to process your uploaded file
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <label className="label">Available Templates</label>
                <select
                  value={selectedTemplateId}
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  className="input"
                >
                  <option value="">Select a template...</option>
                  {activeTemplates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name} - {template.description}
                    </option>
                  ))}
                </select>
              </div>
              
              {selectedTemplate && (
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-medium mb-2">{selectedTemplate.name}</h4>
                  <p className="text-sm text-gray-600 mb-2">{selectedTemplate.description}</p>
                  <p className="text-sm text-gray-600">
                    Target Table: <span className="font-medium">{selectedTemplate.targetTable}</span>
                  </p>
                  <p className="text-sm text-gray-600">
                    Columns: <span className="font-medium">{selectedTemplate.columns.length}</span>
                  </p>
                </div>
              )}
              
              <Button 
                onClick={handleTemplateSelect}
                disabled={!selectedTemplateId || isLoading}
                loading={isLoading}
                className="w-full"
              >
                Select Template
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Column Mapping */}
      {uploadData.templateId && selectedTemplate && (
        <Card>
          <CardHeader>
            <CardTitle>Column Mapping</CardTitle>
            <CardDescription>
              Map your file columns to template columns
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedTemplate ? (
              <ColumnMappingInterface 
                template={selectedTemplate}
                onMappingsChange={setMappings}
              />
            ) : (
              <div className="text-center py-8 text-gray-500">
                <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
                <p className="text-lg font-medium">No Template Selected</p>
                <p className="text-sm">Please select a template first to configure column mappings.</p>
              </div>
            )}
            
            <div className="mt-6 flex justify-end">
              <Button 
                onClick={handleProcess}
                disabled={isProcessing || Object.keys(mappings).length === 0 || !uploadData.templateId}
                loading={isProcessing}
              >
                <Play className="h-4 w-4 mr-2" />
                Start Processing
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
