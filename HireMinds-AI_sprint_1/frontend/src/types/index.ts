export type UserRole = 'candidate' | 'recruiter' | 'admin';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// Resumes
export interface Resume {
  id: number;
  user_id: number;
  filename: string;
  file_size: number;
  raw_text?: string;
  extracted_skills: string[];
  extracted_education: Array<{
    degree?: string;
    institution?: string;
    year?: string;
    percentage?: string;
    cgpa?: string;
    raw_text?: string;
  }>;
  extracted_experience: {
    roles?: string[];
    years?: number;
    raw_text?: string;
  };
  extracted_projects: Array<{
    title?: string;
    description?: string;
    technologies?: string[];
  }>;
  candidate_corrected_data?: {
    skills?: string[];
    experience_years?: number;
    education_level?: string;
  } | null;
  is_reviewed_by_candidate: boolean;
  created_at: string;
  updated_at?: string;
}

// Jobs & Applications
export type ApplicationStatus =
  | 'applied'
  | 'under_review'
  | 'shortlisted'
  | 'assessment_pending'
  | 'interview_scheduled'
  | 'accepted'
  | 'rejected';

export interface Job {
  id: number;
  recruiter_id: number;
  title: string;
  company_name: string;
  location: string;
  job_type: string;
  description: string;
  required_skills: string[];
  preferred_skills: string[];
  min_experience_years: number;
  required_education: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  application_count?: number;
}

export interface JobApplication {
  id: number;
  job_id: number;
  candidate_id: number;
  resume_id: number;
  cover_letter?: string;
  status: ApplicationStatus;
  recruiter_notes?: string;
  created_at: string;
  updated_at: string;
  job?: Job;
  candidate?: User;
  resume?: Resume;
}

// Matching & ATS
export interface MatchResult {
  id?: number;
  resume_id: number;
  job_id: number;
  candidate_id?: number;
  tfidf_score?: number;
  semantic_score?: number;
  skill_match_score?: number;
  overall_score?: number;
  skill_match_details?: {
    matched?: string[];
    missing?: string[];
    preferred?: string[];
  };
  ats_score?: number;
  ats_confidence?: string;
  ats_breakdown?: AtsExplanation;
  created_at?: string;
  updated_at?: string;
}

export interface AtsExplanation {
  ats_score: number;
  confidence: string;
  component_scores: {
    skill?: number | null;
    experience?: number | null;
    education?: number | null;
    project?: number | null;
    semantic?: number | null;
  };
  effective_weights: Record<string, number>;
  rationales: Record<string, string>;
  evidence: Record<string, string[]>;
  missing_information: Record<string, string>;
  disclaimer: string;
  limitations?: string[];
}

export interface AtsCandidateRanking {
  rank: number | null;
  candidate_id: number;
  candidate_name: string;
  candidate_email: string;
  application_id: number;
  application_status: ApplicationStatus;
  applied_at: string;
  resume_id: number;
  ats_score: number | null;
  confidence: string | null;
  skill_score: number | null;
  component_scores?: Record<string, number | null>;
  status: string;
}

// Technical Assessments
export type QuestionType = 'mcq' | 'coding';

export interface QuestionOption {
  key: string;
  text: string;
}

export interface CodingTestCase {
  input: any;
  expected: any;
  hidden?: boolean;
}

export interface AssessmentQuestion {
  id: number;
  question_type: QuestionType;
  prompt: string;
  options: QuestionOption[];
  points: number;
  skill_tag?: string;
  difficulty: string;
  order_index: number;
  language?: string;
  function_name?: string;
  starter_code?: string;
  sample_test_cases?: CodingTestCase[];
  test_cases?: CodingTestCase[];
  correct_answer?: string;
  explanation?: string;
}

export interface Assessment {
  id: number;
  job_id: number;
  created_by_id: number;
  title: string;
  description?: string;
  status: 'active' | 'archived';
  duration_minutes: number;
  passing_score: number;
  generation_model?: string;
  created_at: string;
  questions?: AssessmentQuestion[];
}

export interface AssessmentAttempt {
  id: number;
  assessment_id: number;
  candidate_id: number;
  status: 'in_progress' | 'submitted' | 'evaluated' | 'partially_evaluated';
  score?: number;
  mcq_score?: number;
  coding_score?: number;
  earned_points?: number;
  total_points?: number;
  started_at: string;
  submitted_at?: string;
  evaluated_at?: string;
  result_details?: any;
}

// Mock Interviews
export type InterviewStatus = 'in_progress' | 'completed';

export interface InterviewQuestion {
  id: number;
  session_id: number;
  order_index: number;
  is_follow_up: boolean;
  parent_question_id?: number | null;
  prompt: string;
  skill_tag?: string;
  difficulty: string;
  created_at: string;
}

export interface InterviewAnswer {
  id: number;
  session_id: number;
  question_id: number;
  answer_text: string;
  technical_correctness: number;
  relevance: number;
  clarity: number;
  reasoning: number;
  overall_score: number;
  feedback: string;
  evaluation_details?: any;
  evaluated_at: string;
  created_at: string;
}

export interface InterviewEvaluation {
  id: number;
  session_id: number;
  overall_score: number;
  technical_correctness: number;
  relevance: number;
  clarity: number;
  reasoning: number;
  overall_summary: string;
  strengths: string[];
  weaknesses: string[];
  improvement_suggestions: string[];
  recommended_topics: string[];
  disclaimer: string;
  rubric_version: string;
  generation_status: string;
  created_at: string;
}

export interface InterviewSession {
  id: number;
  job_id: number;
  candidate_id: number;
  resume_id?: number | null;
  status: InterviewStatus;
  title: string;
  description?: string;
  difficulty: string;
  focus_areas: string[];
  target_question_count: number;
  max_follow_ups: number;
  started_at: string;
  completed_at?: string;
  created_at: string;
  questions?: InterviewQuestion[];
  answers?: InterviewAnswer[];
  evaluation?: InterviewEvaluation | null;
  current_question?: InterviewQuestion | null;
}

// Reports
export interface ResumeDiagnosticReport {
  resume_id: number;
  candidate_id: number;
  candidate_name: string;
  filename: string;
  is_reviewed_by_candidate: boolean;
  extracted_skills: string[];
  education_records_count: number;
  has_experience_section: boolean;
  has_projects_section: boolean;
  word_count: number;
  completeness_score: number;
  formatting_recommendations: string[];
  generated_at: string;
}

export interface ComprehensiveReport {
  candidate_id: number;
  candidate_name: string;
  candidate_email: string;
  job_id: number;
  job_title: string;
  company_name: string;
  application_status?: string | null;
  applied_at?: string | null;
  resume_analysis: ResumeDiagnosticReport;
  matching?: {
    match_id?: number;
    tfidf_score?: number;
    semantic_score?: number;
    skill_score?: number;
    blended_score?: number;
    matched_skills: string[];
    missing_skills: string[];
    calculated_at?: string;
  } | null;
  ats?: {
    ats_score?: number;
    confidence?: string;
    component_scores: Record<string, number | null>;
    effective_weights: Record<string, number>;
    rationales: Record<string, string>;
    evidence: Record<string, string[]>;
    missing_information: Record<string, string>;
    disclaimer: string;
  } | null;
  assessment?: {
    has_assessment: boolean;
    score?: number;
    mcq_score?: number;
    coding_score?: number;
    passing_score?: number;
    passed?: boolean;
    attempted_at?: string;
  } | null;
  mock_interview?: {
    has_interview: boolean;
    overall_score?: number;
    technical_correctness?: number;
    relevance?: number;
    clarity?: number;
    reasoning?: number;
    strengths: string[];
    weaknesses: string[];
    interview_suggestions: string[];
    recommended_topics: string[];
    disclaimer: string;
  } | null;
  improvement_plan: {
    composite_readiness_score: number;
    readiness_level: string;
    priority_skill_gaps: string[];
    resume_action_items: string[];
    technical_focus_areas: string[];
    interview_coaching_points: string[];
    executive_summary: string;
  };
  generated_at: string;
}
