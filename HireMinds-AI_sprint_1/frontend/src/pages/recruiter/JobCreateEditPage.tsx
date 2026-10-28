import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { jobService } from '../../services/jobService';
import { Job } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Briefcase,
  ArrowLeft,
  Plus,
  X,
  Save,
  Building,
  MapPin,
  Clock,
  Sparkles,
} from 'lucide-react';

export const JobCreateEditPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const isEditMode = Boolean(jobId);

  const [loading, setLoading] = useState(isEditMode);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form Fields
  const [title, setTitle] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [location, setLocation] = useState('');
  const [jobType, setJobType] = useState('full-time');
  const [minExp, setMinExp] = useState<number>(2);
  const [requiredEducation, setRequiredEducation] = useState(
    "Bachelor's Degree in Computer Science or equivalent"
  );
  const [description, setDescription] = useState('');
  const [isActive, setIsActive] = useState(true);

  // Skills
  const [requiredSkills, setRequiredSkills] = useState<string[]>([]);
  const [reqSkillInput, setReqSkillInput] = useState('');

  const [preferredSkills, setPreferredSkills] = useState<string[]>([]);
  const [prefSkillInput, setPrefSkillInput] = useState('');

  useEffect(() => {
    if (isEditMode && jobId) {
      loadJob(Number(jobId));
    }
  }, [isEditMode, jobId]);

  const loadJob = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await jobService.getJob(id);
      setTitle(data.title);
      setCompanyName(data.company_name);
      setLocation(data.location);
      setJobType(data.job_type);
      setMinExp(data.min_experience_years);
      setRequiredEducation(data.required_education || '');
      setDescription(data.description);
      setIsActive(data.is_active);
      setRequiredSkills(data.required_skills || []);
      setPreferredSkills(data.preferred_skills || []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleAddReqSkill = () => {
    const val = reqSkillInput.trim();
    if (val && !requiredSkills.includes(val)) {
      setRequiredSkills([...requiredSkills, val]);
      setReqSkillInput('');
    }
  };

  const handleRemoveReqSkill = (skill: string) => {
    setRequiredSkills(requiredSkills.filter((s) => s !== skill));
  };

  const handleAddPrefSkill = () => {
    const val = prefSkillInput.trim();
    if (val && !preferredSkills.includes(val)) {
      setPreferredSkills([...preferredSkills, val]);
      setPrefSkillInput('');
    }
  };

  const handleRemovePrefSkill = (skill: string) => {
    setPreferredSkills(preferredSkills.filter((s) => s !== skill));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !companyName.trim() || !location.trim() || !description.trim()) {
      setError('Please fill in all mandatory job details.');
      return;
    }

    if (requiredSkills.length === 0) {
      setError('Please add at least one required skill for ATS matching.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const payload: Partial<Job> = {
        title: title.trim(),
        company_name: companyName.trim(),
        location: location.trim(),
        job_type: jobType,
        min_experience_years: Number(minExp),
        required_education: requiredEducation.trim(),
        description: description.trim(),
        required_skills: requiredSkills,
        preferred_skills: preferredSkills,
        is_active: isActive,
      };

      if (isEditMode && jobId) {
        await jobService.updateJob(Number(jobId), payload);
      } else {
        await jobService.createJob(payload);
      }

      navigate('/recruiter/jobs');
    } catch (err) {
      setError(getErrorMessage(err));
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Loading job details..." />
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <button
            onClick={() => navigate('/recruiter/jobs')}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer mb-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to job postings
          </button>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Briefcase className="w-6 h-6 text-indigo-400" />
            {isEditMode ? 'Edit Job Posting' : 'Create New Job Opening'}
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Specify job requirements, experience, and competencies to enable explainable ATS candidate scoring.
          </p>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Basic Job Info Card */}
          <Card>
            <CardHeader
              title="Position Fundamentals"
              subtitle="Title, organization, and employment structure"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <Input
                  label="Job Title"
                  required
                  placeholder="e.g. Senior Backend Engineer (Python / FastAPI)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              <div>
                <Input
                  label="Company Name"
                  required
                  placeholder="e.g. TechCorp Systems"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  leftIcon={<Building className="w-4 h-4 text-slate-400" />}
                />
              </div>

              <div>
                <Input
                  label="Location"
                  required
                  placeholder="e.g. New York, NY / Remote"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  leftIcon={<MapPin className="w-4 h-4 text-slate-400" />}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Employment Type
                </label>
                <select
                  value={jobType}
                  onChange={(e) => setJobType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="full-time">Full-time</option>
                  <option value="part-time">Part-time</option>
                  <option value="contract">Contract</option>
                  <option value="remote">Remote</option>
                  <option value="internship">Internship</option>
                </select>
              </div>

              <div>
                <Input
                  label="Min Experience (Years)"
                  type="number"
                  min={0}
                  max={30}
                  value={minExp}
                  onChange={(e) => setMinExp(Number(e.target.value))}
                  leftIcon={<Clock className="w-4 h-4 text-slate-400" />}
                />
              </div>

              <div className="md:col-span-2">
                <Input
                  label="Required Education Requirement"
                  placeholder="e.g. Bachelor's in CS, IT, or related field"
                  value={requiredEducation}
                  onChange={(e) => setRequiredEducation(e.target.value)}
                />
              </div>
            </div>
          </Card>

          {/* Description */}
          <Card>
            <CardHeader
              title="Job Description & Responsibilities"
              subtitle="Detailed expectations, role overview, and day-to-day work"
            />
            <textarea
              rows={8}
              required
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide a comprehensive job description. This text is parsed for semantic ATS embedding comparison..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder:text-slate-600 resize-y leading-relaxed font-sans"
            />
          </Card>

          {/* Skills Configuration */}
          <Card>
            <CardHeader
              title="Competency & Skill Criteria"
              subtitle="Skills used directly by the ATS matcher, assessment generator, and interview simulator"
            />

            {/* Required Skills */}
            <div className="space-y-3">
              <label className="block text-xs font-medium text-slate-300">
                Required Skills <span className="text-rose-400">*</span>
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Type skill and press Enter (e.g. Python, Docker, PostgreSQL)..."
                  value={reqSkillInput}
                  onChange={(e) => setReqSkillInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddReqSkill();
                    }
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleAddReqSkill}
                  leftIcon={<Plus className="w-3.5 h-3.5" />}
                >
                  Add
                </Button>
              </div>

              <div className="flex flex-wrap gap-1.5 min-h-[32px] p-2 bg-slate-950/60 rounded-lg border border-slate-800/80">
                {requiredSkills.length === 0 ? (
                  <span className="text-xs text-slate-500 italic">No required skills added yet</span>
                ) : (
                  requiredSkills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                    >
                      {skill}
                      <button
                        type="button"
                        onClick={() => handleRemoveReqSkill(skill)}
                        className="hover:text-rose-400 cursor-pointer ml-1"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))
                )}
              </div>
            </div>

            {/* Preferred Skills */}
            <div className="space-y-3 mt-6 pt-5 border-t border-slate-800">
              <label className="block text-xs font-medium text-slate-300">
                Preferred / Nice-to-Have Skills (Optional)
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Type skill and press Enter (e.g. Kubernetes, AWS, Redis)..."
                  value={prefSkillInput}
                  onChange={(e) => setPrefSkillInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddPrefSkill();
                    }
                  }}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={handleAddPrefSkill}
                  leftIcon={<Plus className="w-3.5 h-3.5" />}
                >
                  Add
                </Button>
              </div>

              <div className="flex flex-wrap gap-1.5 min-h-[32px] p-2 bg-slate-950/60 rounded-lg border border-slate-800/80">
                {preferredSkills.length === 0 ? (
                  <span className="text-xs text-slate-500 italic">No preferred skills added</span>
                ) : (
                  preferredSkills.map((skill) => (
                    <span
                      key={skill}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      {skill}
                      <button
                        type="button"
                        onClick={() => handleRemovePrefSkill(skill)}
                        className="hover:text-rose-400 cursor-pointer ml-1"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))
                )}
              </div>
            </div>

            {/* Active Status Checkbox */}
            <div className="mt-6 pt-4 border-t border-slate-800">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <span className="text-xs text-slate-200 font-medium">
                  Active Position (Accepting candidate applications)
                </span>
              </label>
            </div>
          </Card>

          {/* Form Actions */}
          <div className="flex items-center justify-end gap-3">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate('/recruiter/jobs')}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              isLoading={submitting}
              leftIcon={<Save className="w-4 h-4" />}
            >
              {isEditMode ? 'Update Job Posting' : 'Publish Job Opening'}
            </Button>
          </div>
        </form>
      </div>
    </AppLayout>
  );
};
