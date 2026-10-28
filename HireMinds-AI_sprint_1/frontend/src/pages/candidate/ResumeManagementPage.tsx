import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { resumeService } from '../../services/resumeService';
import { Resume } from '../../types';
import {
  FileText,
  UploadCloud,
  CheckCircle2,
  Trash2,
  Eye,
  AlertCircle,
  FileCheck,
} from 'lucide-react';
import { getErrorMessage } from '../../services/api';

export const ResumeManagementPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchResumes = async () => {
    setLoading(true);
    try {
      const data = await resumeService.getMyResumes();
      setResumes(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResumes();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        setError('Only valid PDF files (.pdf) are supported.');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setError('File size exceeds the 10MB limit.');
        return;
      }
      setSelectedFile(file);
      setError(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setUploading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const uploaded = await resumeService.upload(selectedFile);
      setSuccessMsg(`"${uploaded.filename}" uploaded and parsed successfully!`);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchResumes();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (resumeId: number, filename: string) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"?`)) return;

    try {
      await resumeService.deleteResume(resumeId);
      setSuccessMsg(`Resume "${filename}" deleted.`);
      setResumes(resumes.filter((r) => r.id !== resumeId));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes) return '0 KB';
    const kb = bytes / 1024;
    return kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb.toFixed(0)} KB`;
  };

  return (
    <AppLayout>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">My Resumes</h1>
          <p className="text-xs text-slate-400 mt-1">
            Upload, inspect, and verify your parsed technical skills and experience credentials.
          </p>
        </div>
      </div>

      {error && (
        <Alert type="error" className="mb-6" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {successMsg && (
        <Alert type="success" className="mb-6" onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      {/* Upload Zone */}
      <Card className="mb-8">
        <form onSubmit={handleUpload}>
          <div className="border-2 border-dashed border-slate-700 hover:border-indigo-500/60 rounded-xl p-8 text-center transition-colors">
            <UploadCloud className="w-10 h-10 text-indigo-400 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-slate-200 mb-1">
              Upload a new PDF Resume
            </h3>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mb-4">
              Our NLP pipeline securely parses your skills, education, and experience using PyMuPDF and spaCy.
            </p>

            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,application/pdf"
              className="hidden"
              id="resume-file-input"
            />

            <div className="flex items-center justify-center gap-3">
              <label htmlFor="resume-file-input">
                <span className="inline-flex items-center justify-center font-medium rounded-lg text-xs px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 cursor-pointer transition-colors">
                  Choose PDF Document
                </span>
              </label>

              {selectedFile && (
                <Button
                  type="submit"
                  size="sm"
                  variant="primary"
                  isLoading={uploading}
                  leftIcon={<CheckCircle2 className="w-3.5 h-3.5" />}
                >
                  Upload & Analyze ({formatFileSize(selectedFile.size)})
                </Button>
              )}
            </div>

            {selectedFile && (
              <p className="text-xs text-indigo-300 mt-3 font-medium">
                Selected: {selectedFile.name}
              </p>
            )}
          </div>
        </form>
      </Card>

      {/* Resumes List */}
      <Card>
        <CardHeader
          title="Uploaded Documents"
          subtitle={`${resumes.length} total resumes on file`}
        />

        {loading ? (
          <div className="py-12">
            <LoadingSpinner label="Fetching your resumes..." />
          </div>
        ) : resumes.length === 0 ? (
          <EmptyState
            icon={<FileText className="w-6 h-6" />}
            title="No resumes uploaded yet"
            description="Upload your PDF resume above to view skill extractions, run ATS matching, and practice mock interviews."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-3">Filename</th>
                  <th className="py-3 px-3">Size</th>
                  <th className="py-3 px-3">Extracted Skills</th>
                  <th className="py-3 px-3">Review Status</th>
                  <th className="py-3 px-3">Uploaded</th>
                  <th className="py-3 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {resumes.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-850/40 transition-colors">
                    <td className="py-3.5 px-3 font-medium text-slate-200 flex items-center gap-2">
                      <FileCheck className="w-4 h-4 text-indigo-400 shrink-0" />
                      <span className="truncate max-w-xs">{r.filename}</span>
                    </td>
                    <td className="py-3.5 px-3 text-slate-400">{formatFileSize(r.file_size)}</td>
                    <td className="py-3.5 px-3">
                      <span className="font-semibold text-slate-200">
                        {r.extracted_skills?.length || 0}
                      </span>{' '}
                      <span className="text-slate-500 text-[11px]">skills</span>
                    </td>
                    <td className="py-3.5 px-3">
                      {r.is_reviewed_by_candidate ? (
                        <Badge size="sm" variant="success">
                          Verified
                        </Badge>
                      ) : (
                        <Badge size="sm" variant="warning">
                          Auto-extracted (Unreviewed)
                        </Badge>
                      )}
                    </td>
                    <td className="py-3.5 px-3 text-slate-400">
                      {new Date(r.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => navigate(`/candidate/resumes/${r.id}`)}
                          leftIcon={<Eye className="w-3.5 h-3.5" />}
                        >
                          Inspect & Verify
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDelete(r.id, r.filename)}
                          className="text-rose-400 hover:text-rose-300 hover:bg-rose-950/20"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </AppLayout>
  );
};
