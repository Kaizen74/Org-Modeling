import { useState, useRef } from 'react';
import { Upload as UploadIcon, FileText, CheckCircle, XCircle, Loader2, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { orgDataApi } from '../services/api';
import type { UploadResponse } from '../types';

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.csv')) {
        setError('Please select a CSV file');
        return;
      }
      setFile(selectedFile);
      setError(null);
      setResult(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      if (!droppedFile.name.endsWith('.csv')) {
        setError('Please drop a CSV file');
        return;
      }
      setFile(droppedFile);
      setError(null);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const response = await orgDataApi.uploadCsv(file);
      setResult(response);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string | { errors?: string[] } } } };
      const detail = error.response?.data?.detail;
      if (typeof detail === 'object' && detail.errors) {
        setError(detail.errors.join(', '));
      } else if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Failed to upload file');
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Upload Org Structure CSV</h1>

      <div className="card max-w-2xl">
        {/* Required Format */}
        <div className="mb-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-medium text-blue-900 mb-2">Required CSV Columns</h3>
          <ul className="text-sm text-blue-700 grid grid-cols-2 gap-1">
            <li>&#8226; Name (employee name)</li>
            <li>&#8226; Job Title</li>
            <li>&#8226; Grade (e.g., SVP, H8, TL)</li>
            <li>&#8226; Level (1, 2, 3...)</li>
            <li>&#8226; Line Manager</li>
            <li>&#8226; Salary</li>
            <li className="text-blue-500">&#8226; Department (optional)</li>
            <li className="text-blue-500">&#8226; Employee ID (optional)</li>
          </ul>
        </div>

        {/* Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          onClick={() => fileInputRef.current?.click()}
          className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary-500 transition-colors"
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
          />

          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText className="w-8 h-8 text-primary-600" />
              <div className="text-left">
                <p className="font-medium">{file.name}</p>
                <p className="text-sm text-gray-500">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
          ) : (
            <>
              <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-3" />
              <p className="font-medium text-gray-600">
                Drop your CSV file here or click to browse
              </p>
              <p className="text-sm text-gray-400 mt-1">
                Supports: .csv files
              </p>
            </>
          )}
        </div>

        {/* Upload Button */}
        {file && !result && (
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-4 w-full btn btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {uploading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <UploadIcon className="w-5 h-5" />
                Upload & Parse
              </>
            )}
          </button>
        )}

        {/* Error */}
        {error && (
          <div className="mt-4 p-4 bg-red-50 rounded-lg">
            <div className="flex items-center gap-2 text-red-700">
              <XCircle className="w-5 h-5" />
              <span className="font-medium">Upload Failed</span>
            </div>
            <p className="text-sm text-red-600 mt-1">{error}</p>
          </div>
        )}

        {/* Success */}
        {result && result.success && (
          <div className="mt-4 p-4 bg-green-50 rounded-lg">
            <div className="flex items-center gap-2 text-green-700 mb-3">
              <CheckCircle className="w-5 h-5" />
              <span className="font-medium">Upload Successful!</span>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Employees:</span>{' '}
                <span className="font-medium">{result.employee_count}</span>
              </div>
              <div>
                <span className="text-gray-500">Managers:</span>{' '}
                <span className="font-medium">{result.manager_count}</span>
              </div>
            </div>

            {result.validation_errors.length > 0 && (
              <div className="mt-3 p-2 bg-yellow-50 rounded">
                <p className="text-sm font-medium text-yellow-700">Warnings:</p>
                <ul className="text-sm text-yellow-600">
                  {result.validation_errors.map((err, i) => (
                    <li key={i}>&#8226; {err}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-4 flex gap-3">
              <Link to="/metrics" className="btn btn-primary flex items-center gap-2">
                View Metrics <ArrowRight className="w-4 h-4" />
              </Link>
              <Link to="/analysis" className="btn btn-secondary flex items-center gap-2">
                Run AI Analysis
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
