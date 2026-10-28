import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Alert } from '../../components/ui/Alert';
import { Modal } from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { resumeService } from '../../services/resumeService';
import { reportService } from '../../services/reportService';
import { Resume, ResumeDiagnosticReport } from '../../types';
import {
  FileText,
  CheckCircle2,
  Edit3,
  GraduationCap,
  Briefcase,
  FolderGit2,
  Sparkles,
  ArrowLeft,
  Plus,
  X,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';
import { getErrorMessage } from '../../services/api';

export const ResumeDetailPage: React.FC = () => {
  const { resumeId } = useParams<{ resumeId: string }>();
  const navigate = useNavigate();

  const [resume, setResume] = useState<Resume | null>(null);
  const [diagnostic, setDiagnostic] = useState<ResumeDiagnosticReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Edit Skills Modal State
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [skillsList, setSkillsList] = useState<string[]>([]);
  const [newSkillInput, setNewSkillInput] = useState('');
  const [savingSkills, setSavingSkills] = useState(false);

  const fetchResumeData = async () => {
    if (!resumeId) return;
    setLoading(true);
    try {
      const id = parseInt(resumeId, 10);
      const [resumeData, diagnosticData] = await Promise.all([
        resumeService.getResume(id),
        reportService.getResumeDiagnostic(id),
      ]);
      setResume(resumeData);
      setDiagnostic(diagnosticData);
      // Initialize skills for editor
      const activeSkills = resumeData.is_reviewed_by_candidate
        ? resumeData.candidate_corrected_data?.skills || resumeData.extracted_skills
        : resumeData.extracted_skills;
      setSkillsList(activeSkills || []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResumeData();
  }, [resumeId]);

  const handleAddSkill = () => {
    const trimmed = newSkillInput.trim();
    if (trimmed && !skillsList.some((s) => s.toLowerCase() === trimmed.toLowerCase())) {
      setSkillsList([...skillsList, trimmed]);
      setNewSkillInput('');
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setSkillsList(skillsList.filter((s) => s !== skillToRemove));
  };

  const handleSaveVerifiedSkills = async () => {
    if (!resume) return;
    setSavingSkills(true);
    setError(null);
    try {
      const updated = await resumeService.reviewAndCorrect(resume.id, {
        skills: skillsList,
      });
      setResume(updated);
      setIsEditModalOpen(false);
      setSuccessMsg('Resume skills updated and verified successfully! Your verification bonus is now active.');
      // Refresh diagnostic
      const updatedDiag = await reportService.getResumeDiagnostic(resume.id);
      setDiagnostic(updatedDiag);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSavingSkills(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Analyzing parsed resume content..." />
      </AppLayout>
    );
  }

  if (!resume) {
    return (
      <AppLayout>
        <Alert type="error">Resume not found or access denied.</Alert>
      </AppLayout>
    );
  }

  const currentSkills = resume.is_reviewed_by_candidate
    ? resume.candidate_corrected_data?.skills || resume.extracted_skills
    : resume.extracted_skills;

  return (
    <AppLayout>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
        <div>
          <button
            onClick={() => navigate('/candidate/resumes')}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1.5 mb-2 cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to resumes
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold text-white truncate max-w-lg">
              {resume.filename}
            </h1>
            {resume.is_reviewed_by_candidate ? (
              <Badge variant="success">Verified by You</Badge>
            ) : (
              <Badge variant="warning">Auto-extracted (Unreviewed)</Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="primary"
            size="sm"
            onClick={() => setIsEditModalOpen(true)}
            leftIcon={<Edit3 className="w-3.5 h-3.5" />}
          >
            Verify / Edit Skills
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate('/candidate/jobs')}
          >
            Find Matching Jobs
          </Button>
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

      {/* Diagnostics Banner */}
      {diagnostic && (
        <div className="mb-6 p-4 rounded-xl border border-indigo-500/20 bg-indigo-950/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex flex-col items-center justify-center shrink-0">
              <span className="text-lg font-bold text-indigo-300">
                {diagnostic.completeness_score}
              </span>
              <span className="text-[9px] uppercase tracking-wider text-indigo-400 font-semibold">
                Score
              </span>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">
                Resume Completeness Diagnostic
              </h4>
              <p className="text-xs text-slate-400 mt-0.5">
                Word count: {diagnostic.word_count} • Skills detected:{' '}
                {diagnostic.extracted_skills.length} • Education credentials:{' '}
                {diagnostic.education_records_count}
              </p>
            </div>
          </div>

          {!resume.is_reviewed_by_candidate && (
            <div className="flex items-center gap-2 text-xs text-amber-300 bg-amber-500/10 border border-amber-500/20 px-3 py-1.5 rounded-lg">
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
              <span>Verifying your skills adds +15% to your completeness rating.</span>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Extracted Skills & Sections */}
        <div className="lg:col-span-2 space-y-6">
          {/* Extracted Technical Skills */}
          <Card>
            <CardHeader
              title={
                <div className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span>Technical Skills</span>
                  <span className="text-xs text-slate-500 font-normal">
                    ({currentSkills?.length || 0})
                  </span>
                </div>
              }
              subtitle={
                resume.is_reviewed_by_candidate
                  ? 'Candidate-verified technical skills'
                  : 'Automatically extracted by NLP taxonomy pipeline'
              }
              action={
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsEditModalOpen(true)}
                  leftIcon={<Edit3 className="w-3.5 h-3.5" />}
                >
                  Edit
                </Button>
              }
            />

            {currentSkills?.length === 0 ? (
              <p className="text-xs text-slate-500 italic py-2">
                No technical skills were detected. Click "Edit" to add your skills manually.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {currentSkills?.map((skill, idx) => (
                  <Badge key={idx} variant="purple" size="md">
                    {skill}
                  </Badge>
                ))}
              </div>
            )}
          </Card>

          {/* Extracted Work Experience */}
          <Card>
            <CardHeader
              title={
                <div className="flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-cyan-400" />
                  <span>Work & Professional Experience</span>
                </div>
              }
              subtitle="Roles and tenure parsed from resume text"
            />

            {resume.extracted_experience?.roles && resume.extracted_experience.roles.length > 0 ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <span className="text-slate-500">Estimated Tenure:</span>
                  <span className="font-semibold text-cyan-400">
                    {resume.extracted_experience.years !== undefined
                      ? `${resume.extracted_experience.years} years`
                      : 'Not specified'}
                  </span>
                </div>
                <div className="space-y-1.5">
                  <p className="text-xs text-slate-400 font-medium">Identified Roles:</p>
                  <div className="flex flex-wrap gap-1.5">
                    {resume.extracted_experience.roles.map((role, idx) => (
                      <Badge key={idx} variant="cyan" size="sm">
                        {role}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">
                No distinct roles were parsed from the experience section.
              </p>
            )}
          </Card>

          {/* Extracted Education */}
          <Card>
            <CardHeader
              title={
                <div className="flex items-center gap-2">
                  <GraduationCap className="w-4 h-4 text-emerald-400" />
                  <span>Education & Academic Credentials</span>
                </div>
              }
              subtitle="Degree patterns, graduation years, and GPAs"
            />

            {resume.extracted_education && resume.extracted_education.length > 0 ? (
              <div className="divide-y divide-slate-800/60">
                {resume.extracted_education.map((edu, idx) => (
                  <div key={idx} className="py-2.5 first:pt-0 last:pb-0">
                    <div className="flex items-center justify-between">
                      <h5 className="text-xs font-semibold text-slate-200">
                        {edu.degree || 'Degree credential'}
                      </h5>
                      {edu.year && <Badge size="sm" variant="neutral">{edu.year}</Badge>}
                    </div>
                    {edu.institution && (
                      <p className="text-xs text-slate-400 mt-0.5">{edu.institution}</p>
                    )}
                    {(edu.cgpa || edu.percentage) && (
                      <p className="text-[11px] text-emerald-400 mt-1">
                        Score: {edu.cgpa ? `CGPA ${edu.cgpa}` : `${edu.percentage}%`}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic">
                No formal educational degree patterns detected.
              </p>
            )}
          </Card>

          {/* Extracted Projects */}
          {resume.extracted_projects && resume.extracted_projects.length > 0 && (
            <Card>
              <CardHeader
                title={
                  <div className="flex items-center gap-2">
                    <FolderGit2 className="w-4 h-4 text-amber-400" />
                    <span>Projects & Implementations</span>
                  </div>
                }
              />
              <div className="space-y-3">
                {resume.extracted_projects.map((proj, idx) => (
                  <div key={idx} className="p-3 rounded-lg border border-slate-800 bg-slate-950/40">
                    <h5 className="text-xs font-semibold text-slate-200">{proj.title}</h5>
                    {proj.description && (
                      <p className="text-xs text-slate-400 mt-1">{proj.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Right 1 Col: Recommendations & Summary */}
        <div className="space-y-6">
          <Card>
            <CardHeader title="Improvement Recommendations" />
            {diagnostic?.formatting_recommendations && diagnostic.formatting_recommendations.length > 0 ? (
              <ul className="space-y-2.5 text-xs text-slate-300">
                {diagnostic.formatting_recommendations.map((rec, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-indigo-400 font-bold">•</span>
                    <span className="leading-relaxed">{rec}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="flex items-center gap-2 text-xs text-emerald-400">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>Your resume meets all core structural completeness standards!</span>
              </div>
            )}
          </Card>

          {/* Raw Text View */}
          <Card>
            <CardHeader
              title="Raw Extracted Text"
              subtitle="Text extracted by PyMuPDF"
            />
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 max-h-60 overflow-y-auto text-[11px] font-mono text-slate-400 leading-relaxed whitespace-pre-wrap">
              {resume.raw_text || 'No raw text available'}
            </div>
          </Card>
        </div>
      </div>

      {/* Edit Skills Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Verify and Edit Extracted Skills"
        subtitle="Review the skills automatically identified from your resume. Add missing skills or remove inaccurate ones."
        footer={
          <>
            <Button variant="outline" size="sm" onClick={() => setIsEditModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              isLoading={savingSkills}
              onClick={handleSaveVerifiedSkills}
              leftIcon={<ShieldCheck className="w-4 h-4" />}
            >
              Save & Verify Skills
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              type="text"
              placeholder="e.g. Kubernetes, React, GraphQL"
              value={newSkillInput}
              onChange={(e) => setNewSkillInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddSkill();
                }
              }}
            />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleAddSkill}
              leftIcon={<Plus className="w-3.5 h-3.5" />}
            >
              Add
            </Button>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-2">
              Active Verified Skills ({skillsList.length}):
            </label>
            <div className="flex flex-wrap gap-2 max-h-56 overflow-y-auto p-2 rounded-lg bg-slate-950 border border-slate-800">
              {skillsList.map((skill, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                >
                  <span>{skill}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(skill)}
                    className="hover:text-rose-400 cursor-pointer"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          </div>
        </div>
      </Modal>
    </AppLayout>
  );
};
