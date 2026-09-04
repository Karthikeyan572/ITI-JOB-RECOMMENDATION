import React, { useState, useEffect } from 'react';
import {
  Briefcase,
  GraduationCap,
  Award,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Upload,
  BookOpen,
  ArrowRight,
  RefreshCw,
  Search,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Sliders,
  FileText,
  UserCheck,
  Download,
  Database,
  Layers,
  Sparkles
} from 'lucide-react';

const API_BASE = '/api';

export default function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState('candidate'); // 'candidate' | 'jobs' | 'courses'

  // Application State
  const [meta, setMeta] = useState({ trades: [], skills: [] });
  const [samples, setSamples] = useState({});
  const [uploading, setUploading] = useState(false);
  const [matching, setMatching] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);

  // Resume & Candidate State
  const [rawText, setRawText] = useState('');
  const [fileName, setFileName] = useState('');
  const [validationStatus, setValidationStatus] = useState(null); // 'VALID' | 'TRADE_UNCLEAR' | 'NOT_ITI' | null
  const [profile, setProfile] = useState({
    iti_trade: '',
    skills: [],
    experience: 0,
    certifications: [],
    qualification: []
  });

  // Matching & Results State
  const [minThreshold, setMinThreshold] = useState(0.60);
  const [matchResults, setMatchResults] = useState(null);
  const [showDiagnostics, setShowDiagnostics] = useState(false);

  // Skill Search Filter
  const [skillSearch, setSkillSearch] = useState('');
  const [customSkill, setCustomSkill] = useState('');

  // Directory Exploration State
  const [directoryJobs, setDirectoryJobs] = useState([]);
  const [directoryCourses, setDirectoryCourses] = useState([]);
  const [dirTradeFilter, setDirTradeFilter] = useState('');
  const [dirSearchQuery, setDirSearchQuery] = useState('');
  const [dirLoading, setDirLoading] = useState(false);

  // Initial Load
  useEffect(() => {
    fetchMeta();
    fetchSamples();
  }, []);

  const fetchMeta = async () => {
    try {
      const res = await fetch(`${API_BASE}/meta`);
      if (res.ok) {
        const data = await res.json();
        setMeta(data);
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch (err) {
      setBackendOnline(false);
    }
  };

  const fetchSamples = async () => {
    try {
      const res = await fetch(`${API_BASE}/samples`);
      if (res.ok) {
        const data = await res.json();
        setSamples(data);
      }
    } catch (err) {
      console.error("Could not load samples:", err);
    }
  };

  // Fetch Directory Jobs
  const loadDirectoryJobs = async (trade = dirTradeFilter) => {
    setDirLoading(true);
    try {
      const url = trade ? `${API_BASE}/jobs?trade=${encodeURIComponent(trade)}&limit=100` : `${API_BASE}/jobs?limit=100`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setDirectoryJobs(data.jobs || []);
      }
    } catch (err) {
      console.error("Failed to load jobs directory:", err);
    } finally {
      setDirLoading(false);
    }
  };

  // Fetch Directory Courses
  const loadDirectoryCourses = async (trade = dirTradeFilter) => {
    setDirLoading(true);
    try {
      const url = trade ? `${API_BASE}/courses?trade=${encodeURIComponent(trade)}&limit=150` : `${API_BASE}/courses?limit=150`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setDirectoryCourses(data.courses || []);
      }
    } catch (err) {
      console.error("Failed to load courses directory:", err);
    } finally {
      setDirLoading(false);
    }
  };

  // Switch Tabs
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'jobs' && directoryJobs.length === 0) {
      loadDirectoryJobs(dirTradeFilter);
    } else if (tab === 'courses' && directoryCourses.length === 0) {
      loadDirectoryCourses(dirTradeFilter);
    }
  };

  // Handle Resume File Upload
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setFileName(file.name);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/upload-resume`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        alert(`Upload error: ${err.detail || 'Could not parse resume'}`);
        setUploading(false);
        return;
      }

      const data = await res.json();
      setRawText(data.raw_text);
      setValidationStatus(data.validation_status);
      setProfile({
        iti_trade: data.profile.iti_trade || '',
        skills: data.profile.skills || [],
        experience: data.profile.experience || 0,
        certifications: data.profile.certifications || [],
        qualification: data.profile.qualification || ['ITI'],
      });

      if (data.validation_status === 'VALID') {
        runJobMatching(data.profile);
      } else {
        setMatchResults(null);
      }
    } catch (err) {
      alert(`Network error uploading file: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  // Load a Pre-configured Demo Sample
  const loadSample = (sampleKey) => {
    const sample = samples[sampleKey];
    if (!sample) return;

    setFileName(sample.filename);
    setRawText(sample.text);

    const formData = new FormData();
    const blob = new Blob([sample.text], { type: 'text/plain' });
    formData.append('file', blob, sample.filename);

    setUploading(true);
    fetch(`${API_BASE}/upload-resume`, {
      method: 'POST',
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        setValidationStatus(data.validation_status);
        setProfile({
          iti_trade: data.profile.iti_trade || '',
          skills: data.profile.skills || [],
          experience: data.profile.experience || 0,
          certifications: data.profile.certifications || [],
          qualification: data.profile.qualification || ['ITI'],
        });

        if (data.validation_status === 'VALID') {
          runJobMatching(data.profile);
        } else {
          setMatchResults(null);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setUploading(false));
  };

  // Execute Job Matching
  const runJobMatching = async (candidateProfile = profile) => {
    if (!candidateProfile.iti_trade) {
      alert("Please select or specify an ITI Trade before running job matching.");
      return;
    }

    setMatching(true);
    try {
      const res = await fetch(`${API_BASE}/match-jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: candidateProfile,
          min_threshold: minThreshold,
          top_n: 3
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setMatchResults(data);
      } else {
        alert("Failed to perform matching. Check backend server.");
      }
    } catch (err) {
      alert(`Network error during matching: ${err.message}`);
    } finally {
      setMatching(false);
    }
  };

  // Export Skill Gap Report
  const exportReport = () => {
    if (!matchResults) return;

    let content = `AI-DRIVEN ITI EMPLOYABILITY & SKILL GAP REPORT\n`;
    content += `==============================================\n\n`;
    content += `Candidate Profile:\n`;
    content += `- ITI Trade      : ${profile.iti_trade || 'Not detected'}\n`;
    content += `- Experience     : ${profile.experience} years\n`;
    content += `- Skills         : ${profile.skills.join(', ') || 'None'}\n`;
    content += `- Certifications : ${profile.certifications.join(', ') || 'None'}\n`;
    content += `- Qualifications : ${profile.qualification.join(', ') || 'ITI'}\n\n`;
    content += `==============================================\n`;
    content += `TOP 3 JOB RECOMMENDATIONS & SKILL GAPS:\n\n`;

    matchResults.top_recommendations.forEach((job, idx) => {
      content += `[Job #${idx + 1}] ${job.job_title} at ${job.company} (${job.location})\n`;
      content += `  - Final Match Score  : ${job.match_percentage}%\n`;
      content += `  - Trade Compatibility: ${(job.trade_score * 100).toFixed(0)}%\n`;
      content += `  - Skill Match Score  : ${(job.skill_score * 100).toFixed(1)}%\n`;
      content += `  - Experience Match   : ${(job.experience_score * 100).toFixed(0)}%\n`;
      content += `  - Certification Match: ${(job.certification_score * 100).toFixed(0)}%\n`;
      content += `  - Matched Skills     : ${job.matched_skills.join(', ') || 'None'}\n`;
      content += `  - Missing Skills     : ${job.missing_skills.join(', ') || 'None'}\n`;

      if (job.learning_recommendations && job.learning_recommendations.length > 0) {
        content += `  - Targeted Learning Modules:\n`;
        job.learning_recommendations.forEach((course) => {
          content += `    * ${course.skill}: "${course.course_name}" (${course.provider}, ${course.duration}, ${course.level})\n`;
        });
      }
      content += `\n`;
    });

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ITI_Skill_Gap_Report_${profile.iti_trade || 'Candidate'}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Profile Modification Helpers
  const addSkill = (skill) => {
    if (!profile.skills.includes(skill)) {
      setProfile({ ...profile, skills: [...profile.skills, skill] });
    }
  };

  const removeSkill = (skill) => {
    setProfile({ ...profile, skills: profile.skills.filter(s => s !== skill) });
  };

  const handleAddCustomSkill = (e) => {
    e.preventDefault();
    if (customSkill.trim() && !profile.skills.includes(customSkill.trim())) {
      setProfile({ ...profile, skills: [...profile.skills, customSkill.trim()] });
      setCustomSkill('');
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pb-16">
      {/* ================= HEADER ================= */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-teal-700 to-teal-500 flex items-center justify-center text-white font-bold text-xl shadow-xs">
              🛠️
            </div>
            <div>
              <h1 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
                AI-Driven ITI Employability System
                <span className="hidden sm:inline-block text-[11px] font-semibold uppercase bg-teal-50 text-teal-700 px-2 py-0.5 rounded border border-teal-200">
                  v1.0
                </span>
              </h1>
              <p className="text-xs text-slate-500">
                Automated Resume Analysis, Trade Validation & Targeted Skill Gap Mapping
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 self-end sm:self-auto">
            <button
              onClick={fetchMeta}
              title="Refresh connection"
              className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                backendOnline ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200' : 'bg-rose-100 text-rose-800 hover:bg-rose-200'
              }`}
            >
              <span className={`w-2 h-2 mr-1.5 rounded-full ${backendOnline ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
              {backendOnline ? 'FastAPI Connected (Port 8000)' : 'Backend Offline - Click to Retry'}
            </button>
          </div>
        </div>

        {/* NAVIGATION TABS */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 border-t border-slate-100 flex gap-6 text-sm">
          <button
            onClick={() => handleTabChange('candidate')}
            className={`py-2.5 font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'candidate'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <UserCheck className="w-4 h-4" /> Candidate Analysis Portal
          </button>
          <button
            onClick={() => handleTabChange('jobs')}
            className={`py-2.5 font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'jobs'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Briefcase className="w-4 h-4" /> Job Vacancies Explorer (1,000)
          </button>
          <button
            onClick={() => handleTabChange('courses')}
            className={`py-2.5 font-medium border-b-2 transition-all flex items-center gap-2 ${
              activeTab === 'courses'
                ? 'border-teal-600 text-teal-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <BookOpen className="w-4 h-4" /> Upskilling Courses Catalog (112)
          </button>
        </div>
      </header>

      {/* ================= MAIN CONTENT ================= */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 space-y-6">

        {/* CONNECTION ALERT IF BACKEND OFFLINE */}
        {!backendOnline && (
          <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 text-amber-900 flex items-center justify-between shadow-xs">
            <div className="flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
              <div>
                <p className="font-semibold text-sm">FastAPI Backend Server is not detected at http://127.0.0.1:8000</p>
                <p className="text-xs text-amber-700 mt-0.5">Please ensure the backend is running with: <code className="bg-amber-100 px-1 py-0.5 rounded font-mono">uvicorn src.api:app --reload --port 8000</code></p>
              </div>
            </div>
            <button
              onClick={fetchMeta}
              className="px-3 py-1.5 text-xs font-semibold bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors shrink-0"
            >
              Reconnect
            </button>
          </div>
        )}

        {/* TAB 1: CANDIDATE PORTAL */}
        {activeTab === 'candidate' && (
          <div className="space-y-6">
            {/* STEP 1: DEMO PRESETS & RESUME UPLOAD */}
            <section className="bg-white rounded-xl border border-slate-200 shadow-xs p-6">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-100">
                <div>
                  <h2 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
                    <Upload className="w-5 h-5 text-teal-600" />
                    Step 1: Upload Candidate Resume
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                    Upload a candidate resume in PDF or DOCX format, or select a pre-configured scenario.
                  </p>
                </div>

                {/* Quick Demo Buttons */}
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mr-1">Demo Scenarios:</span>
                  <button
                    onClick={() => loadSample('electrician')}
                    className="px-3 py-1.5 text-xs font-semibold bg-emerald-50 text-emerald-800 rounded-lg hover:bg-emerald-100 border border-emerald-200 transition-colors flex items-center gap-1"
                  >
                    ⚡ Electrician (Valid)
                  </button>
                  <button
                    onClick={() => loadSample('fitter')}
                    className="px-3 py-1.5 text-xs font-semibold bg-blue-50 text-blue-800 rounded-lg hover:bg-blue-100 border border-blue-200 transition-colors flex items-center gap-1"
                  >
                    🔧 Fitter (Valid)
                  </button>
                  <button
                    onClick={() => loadSample('cse')}
                    className="px-3 py-1.5 text-xs font-semibold bg-rose-50 text-rose-800 rounded-lg hover:bg-rose-100 border border-rose-200 transition-colors flex items-center gap-1"
                  >
                    💻 CSE (Non-ITI)
                  </button>
                  <button
                    onClick={() => loadSample('unclear')}
                    className="px-3 py-1.5 text-xs font-semibold bg-purple-50 text-purple-800 rounded-lg hover:bg-purple-100 border border-purple-200 transition-colors flex items-center gap-1"
                  >
                    ❓ Unclear Trade
                  </button>
                </div>
              </div>

              {/* Upload Dropzone */}
              <div className="mt-5">
                <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-slate-300 rounded-xl cursor-pointer bg-slate-50/50 hover:bg-slate-50 hover:border-teal-500 transition-all">
                  <div className="flex flex-col items-center justify-center pt-4 pb-5">
                    <Upload className="w-7 h-7 mb-1.5 text-slate-400" />
                    <p className="text-sm text-slate-700">
                      <span className="font-semibold text-teal-600">Click to upload resume</span> or drag and drop
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">Supports PDF (PyMuPDF) and DOCX (python-docx)</p>
                    {fileName && (
                      <p className="mt-2 text-xs font-semibold text-emerald-600 flex items-center gap-1 bg-emerald-50 px-2.5 py-1 rounded-md border border-emerald-200">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Loaded: {fileName}
                      </p>
                    )}
                  </div>
                  <input
                    type="file"
                    className="hidden"
                    accept=".pdf,.docx"
                    onChange={handleFileUpload}
                    disabled={uploading}
                  />
                </label>
              </div>
            </section>

            {/* STEP 2: PROFILE VALIDATION BANNER */}
            {validationStatus && (
              <section>
                {validationStatus === 'VALID' && (
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3 shadow-xs">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <h3 className="text-sm font-bold text-emerald-900">
                        VALID ITI PROFILE DETECTED — Primary Trade: <span className="underline">{profile.iti_trade}</span>
                      </h3>
                      <p className="text-xs text-emerald-700 mt-0.5">
                        Specific ITI vocational trade detected from resume text. Recommended jobs and skill gaps are ready below.
                      </p>
                    </div>
                  </div>
                )}

                {validationStatus === 'TRADE_UNCLEAR' && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 shadow-xs">
                    <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <h3 className="text-sm font-bold text-amber-900">
                        TRADE UNCLEAR: ITI Training Evidence Detected
                      </h3>
                      <p className="text-xs text-amber-700 mt-0.5">
                        Vocational education / NCVT training markers were identified, but the exact trade was not explicitly stated.
                        Please select your trade in Step 2 below to proceed with job matching.
                      </p>
                    </div>
                  </div>
                )}

                {validationStatus === 'NOT_ITI' && (
                  <div className="bg-slate-100 border border-slate-300 rounded-xl p-4 flex items-start gap-3 shadow-xs">
                    <XCircle className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />
                    <div>
                      <h3 className="text-sm font-bold text-slate-800">
                        No specific ITI trade or sufficient ITI-related information was detected.
                      </h3>
                      <p className="text-xs text-slate-600 mt-0.5">
                        This system specializes in ITI vocational placement. No ITI jobs are recommended by default.
                        If you are an ITI candidate, select your trade below to unlock tailored recommendations.
                      </p>
                    </div>
                  </div>
                )}
              </section>
            )}

            {/* STEP 3: REVIEW & EDIT CANDIDATE PROFILE */}
            {(rawText || profile.skills.length > 0) && (
              <section className="bg-white rounded-xl border border-slate-200 shadow-xs p-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
                  <div>
                    <h2 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
                      <UserCheck className="w-5 h-5 text-teal-600" />
                      Step 2: Review & Edit Candidate Profile
                    </h2>
                    <p className="text-xs sm:text-sm text-slate-500">
                      Verify or edit extracted candidate details. Matching will evaluate this reviewed profile.
                    </p>
                  </div>

                  <button
                    onClick={() => runJobMatching()}
                    disabled={matching || !profile.iti_trade}
                    className={`px-5 py-2.5 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 shadow-xs transition-all ${
                      profile.iti_trade
                        ? 'bg-teal-600 hover:bg-teal-700 text-white cursor-pointer'
                        : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    {matching ? (
                      <>
                        <RefreshCw className="w-4 h-4 animate-spin" /> Matching...
                      </>
                    ) : (
                      <>
                        <Briefcase className="w-4 h-4" /> Run Job Matching & Gap Analysis
                      </>
                    )}
                  </button>
                </div>

                {/* Profile Grid Form */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mt-5">
                  {/* ITI Trade */}
                  <div>
                    <label className="block text-xs font-semibold uppercase text-slate-600 mb-1.5">
                      ITI Trade <span className="text-rose-500">*</span>
                    </label>
                    <select
                      value={profile.iti_trade || ''}
                      onChange={(e) => setProfile({ ...profile, iti_trade: e.target.value })}
                      className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                    >
                      <option value="">-- Select ITI Trade --</option>
                      {meta.trades.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>

                  {/* Experience */}
                  <div>
                    <label className="block text-xs font-semibold uppercase text-slate-600 mb-1.5 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> Total Experience (Years)
                    </label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      max="25"
                      value={profile.experience}
                      onChange={(e) => setProfile({ ...profile, experience: parseFloat(e.target.value) || 0 })}
                      className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                    />
                  </div>

                  {/* Certifications */}
                  <div>
                    <label className="block text-xs font-semibold uppercase text-slate-600 mb-1.5 flex items-center gap-1">
                      <Award className="w-3.5 h-3.5" /> Certifications (Comma-separated)
                    </label>
                    <input
                      type="text"
                      value={profile.certifications.join(', ')}
                      onChange={(e) => setProfile({
                        ...profile,
                        certifications: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                      })}
                      placeholder="e.g. NCVT, Trade Certificate, Safety"
                      className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-sm font-medium focus:ring-2 focus:ring-teal-500 focus:outline-none"
                    />
                  </div>
                </div>

                {/* Technical Skills Section */}
                <div className="mt-5 pt-5 border-t border-slate-100">
                  <label className="block text-xs font-semibold uppercase text-slate-600 mb-2">
                    Candidate Technical Skills ({profile.skills.length} Selected)
                  </label>

                  {/* Active Skill Tags */}
                  <div className="flex flex-wrap gap-1.5 mb-3 p-3 bg-slate-50 rounded-lg border border-slate-200 min-h-[44px]">
                    {profile.skills.length === 0 ? (
                      <span className="text-xs text-slate-400 italic">No skills selected yet. Select from taxonomy below or add custom skills.</span>
                    ) : (
                      profile.skills.map((skill) => (
                        <span
                          key={skill}
                          className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200"
                        >
                          {skill}
                          <button
                            onClick={() => removeSkill(skill)}
                            className="ml-1.5 text-indigo-400 hover:text-indigo-900 focus:outline-none"
                          >
                            ×
                          </button>
                        </span>
                      ))
                    )}
                  </div>

                  {/* Quick Skill Search & Add */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <div className="relative">
                        <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                        <input
                          type="text"
                          placeholder="Search master ITI skills to add..."
                          value={skillSearch}
                          onChange={(e) => setSkillSearch(e.target.value)}
                          className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-none"
                        />
                      </div>

                      {/* Filtered skill chips */}
                      {skillSearch && (
                        <div className="flex flex-wrap gap-1 mt-2 max-h-32 overflow-y-auto p-2 bg-slate-50 rounded-lg border border-slate-200">
                          {meta.skills
                            .filter(s => s.toLowerCase().includes(skillSearch.toLowerCase()) && !profile.skills.includes(s))
                            .slice(0, 15)
                            .map(s => (
                              <button
                                key={s}
                                onClick={() => addSkill(s)}
                                className="text-xs bg-white hover:bg-teal-50 text-slate-700 px-2 py-0.5 rounded border border-slate-300 hover:border-teal-400 transition-colors"
                              >
                                + {s}
                              </button>
                            ))}
                        </div>
                      )}
                    </div>

                    {/* Custom Skill Input Form */}
                    <form onSubmit={handleAddCustomSkill} className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Type custom skill..."
                        value={customSkill}
                        onChange={(e) => setCustomSkill(e.target.value)}
                        className="flex-1 px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-none"
                      />
                      <button
                        type="submit"
                        className="px-3 py-1.5 text-xs font-semibold bg-slate-800 text-white rounded-lg hover:bg-slate-900 transition-colors cursor-pointer"
                      >
                        Add
                      </button>
                    </form>
                  </div>
                </div>
              </section>
            )}

            {/* STEP 4: TOP 3 RECOMMENDED JOBS */}
            {matchResults && (
              <section className="space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
                  <div>
                    <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                      <Briefcase className="w-5 h-5 text-teal-600" />
                      Step 3: Top 3 Recommended ITI Jobs
                    </h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Target Trade: <b>{matchResults.candidate_trade}</b> | Evaluated: <b>{matchResults.total_matched_jobs}</b> jobs | Qualifying (&ge;60%): <b>{matchResults.meets_threshold_count}</b>
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={exportReport}
                      className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg flex items-center gap-1.5 shadow-xs transition-colors cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" /> Download Skill Gap Report
                    </button>
                    <button
                      onClick={() => setShowDiagnostics(!showDiagnostics)}
                      className="px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded-lg flex items-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <Sliders className="w-3.5 h-3.5" /> {showDiagnostics ? 'Hide Diagnostics' : 'Inspect All Scores'}
                    </button>
                  </div>
                </div>

                {/* Jobs Cards Grid */}
                <div className="grid grid-cols-1 gap-5">
                  {matchResults.top_recommendations.map((job, idx) => (
                    <div
                      key={job.job_id}
                      className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 hover:shadow-md transition-shadow"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                        <div>
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <span className="w-7 h-7 rounded-full bg-teal-100 text-teal-800 font-bold text-sm flex items-center justify-center">
                              #{idx + 1}
                            </span>
                            <h3 className="text-base sm:text-lg font-bold text-slate-900">{job.job_title}</h3>
                            <span className="px-2 py-0.5 text-xs font-semibold bg-slate-100 text-slate-700 rounded-full border border-slate-200">
                              {job.iti_trade}
                            </span>
                          </div>
                          <p className="text-xs sm:text-sm text-slate-500 mt-1">
                            🏢 <b>{job.company}</b> &nbsp;•&nbsp; 📍 {job.location} &nbsp;•&nbsp; ⏳ Exp Required: <b>{job.experience_required}</b>
                          </p>
                        </div>

                        {/* Match Percentage */}
                        <div className="text-right shrink-0">
                          <div className={`text-2xl font-black ${
                            job.match_percentage >= 80 ? 'text-emerald-600' : 'text-teal-600'
                          }`}>
                            {job.match_percentage}%
                          </div>
                          <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                            Final Match Score
                          </span>
                        </div>
                      </div>

                      {/* 4-Factor Breakdown Badges */}
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mt-4 pt-4 border-t border-slate-100 bg-slate-50/50 p-3 rounded-lg">
                        <div className="text-center">
                          <span className="text-[10px] uppercase font-bold text-slate-400 block">Skill Match (50%)</span>
                          <span className="text-sm font-bold text-slate-800">{(job.skill_score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] uppercase font-bold text-slate-400 block">Trade Match (25%)</span>
                          <span className="text-sm font-bold text-slate-800">{(job.trade_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] uppercase font-bold text-slate-400 block">Experience (15%)</span>
                          <span className="text-sm font-bold text-slate-800">{(job.experience_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="text-center">
                          <span className="text-[10px] uppercase font-bold text-slate-400 block">Certification (10%)</span>
                          <span className="text-sm font-bold text-slate-800">{(job.certification_score * 100).toFixed(0)}%</span>
                        </div>
                        <div className="text-center col-span-2 sm:col-span-1">
                          <span className="text-[10px] uppercase font-bold text-slate-400 block">TF-IDF Text Sim</span>
                          <span className="text-sm font-bold text-indigo-600">{job.tfidf_similarity.toFixed(3)}</span>
                        </div>
                      </div>

                      {/* Matched vs Missing Skills */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
                        {/* Matched Skills */}
                        <div>
                          <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-800 mb-2 flex items-center gap-1.5">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Matched Skills ({job.matched_skills.length})
                          </h4>
                          <div className="flex flex-wrap gap-1.5">
                            {job.matched_skills.length > 0 ? (
                              job.matched_skills.map((s) => (
                                <span key={s} className="px-2 py-0.5 text-xs font-medium bg-emerald-50 text-emerald-800 rounded border border-emerald-200">
                                  ✓ {s}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-slate-400 italic">No matching skills</span>
                            )}
                          </div>
                        </div>

                        {/* Missing Skills */}
                        <div>
                          <h4 className="text-xs font-bold uppercase tracking-wider text-rose-800 mb-2 flex items-center gap-1.5">
                            <XCircle className="w-4 h-4 text-rose-600" /> Missing Skills (Skill Gap: {job.missing_skills.length})
                          </h4>
                          <div className="flex flex-wrap gap-1.5">
                            {job.missing_skills.length > 0 ? (
                              job.missing_skills.map((s) => (
                                <span key={s} className="px-2 py-0.5 text-xs font-medium bg-rose-50 text-rose-800 rounded border border-rose-200">
                                  ✗ {s}
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-emerald-600 font-semibold">
                                Full match! Zero skill gap for this position.
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Learning Recommendations for Missing Skills */}
                      {job.learning_recommendations && job.learning_recommendations.length > 0 && (
                        <div className="mt-5 pt-4 border-t border-slate-100">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center gap-1.5">
                            <BookOpen className="w-4 h-4 text-teal-600" /> Recommended Learning Modules for Gap Skills
                          </h4>
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {job.learning_recommendations.map((course, cIdx) => (
                              <div key={cIdx} className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs">
                                <span className="inline-block px-1.5 py-0.5 font-bold uppercase text-[9px] bg-indigo-100 text-indigo-800 rounded mb-1">
                                  Skill: {course.skill}
                                </span>
                                <h5 className="font-semibold text-slate-900 mt-0.5">{course.course_name}</h5>
                                <div className="text-slate-500 mt-1 flex justify-between">
                                  <span>Provider: <b>{course.provider}</b></span>
                                  <span>Duration: <b>{course.duration}</b></span>
                                </div>
                                <div className="text-[10px] text-slate-400 mt-1 flex justify-between">
                                  <span>Level: {course.level}</span>
                                  <span className="italic">{course.resource_url}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* DIAGNOSTICS TABLE */}
                {showDiagnostics && (
                  <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 mt-6">
                    <h3 className="text-base font-bold text-slate-900 mb-3 flex items-center gap-2">
                      <Sliders className="w-4 h-4 text-teal-600" /> Comprehensive Evaluation Table (Top 25 Evaluated Vacancies)
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-slate-200 bg-slate-50 text-slate-600 uppercase font-semibold">
                            <th className="p-2">Job ID</th>
                            <th className="p-2">Job Title</th>
                            <th className="p-2">Company</th>
                            <th className="p-2">Final %</th>
                            <th className="p-2">Skill (50%)</th>
                            <th className="p-2">Trade (25%)</th>
                            <th className="p-2">Exp (15%)</th>
                            <th className="p-2">Cert (10%)</th>
                            <th className="p-2">TF-IDF</th>
                            <th className="p-2">Qualifies</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {matchResults.diagnostics.map((j) => (
                            <tr key={j.job_id} className="hover:bg-slate-50">
                              <td className="p-2 font-mono text-slate-500">{j.job_id}</td>
                              <td className="p-2 font-semibold text-slate-900">{j.job_title}</td>
                              <td className="p-2 text-slate-600">{j.company}</td>
                              <td className="p-2 font-bold text-teal-700">{j.match_percentage}%</td>
                              <td className="p-2">{(j.skill_score * 100).toFixed(1)}%</td>
                              <td className="p-2">{(j.trade_score * 100).toFixed(0)}%</td>
                              <td className="p-2">{(j.experience_score * 100).toFixed(0)}%</td>
                              <td className="p-2">{(j.certification_score * 100).toFixed(0)}%</td>
                              <td className="p-2 font-mono text-indigo-600">{j.tfidf_similarity.toFixed(3)}</td>
                              <td className="p-2">
                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  j.meets_threshold ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                                }`}>
                                  {j.meets_threshold ? 'YES' : 'NO'}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </section>
            )}
          </div>
        )}

        {/* TAB 2: JOB VACANCIES EXPLORER */}
        {activeTab === 'jobs' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-teal-600" /> ITI Jobs Vacancy Directory
                </h2>
                <p className="text-xs text-slate-500">
                  Search across 1,000 industrial vacancies in the dataset.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={dirTradeFilter}
                  onChange={(e) => {
                    setDirTradeFilter(e.target.value);
                    loadDirectoryJobs(e.target.value);
                  }}
                  className="bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 text-xs font-semibold focus:ring-2 focus:ring-teal-500 focus:outline-none"
                >
                  <option value="">All Trades ({meta.trades.length})</option>
                  {meta.trades.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>

                <button
                  onClick={() => loadDirectoryJobs(dirTradeFilter)}
                  className="px-3 py-1.5 text-xs font-semibold bg-slate-800 text-white rounded-lg hover:bg-slate-900 transition-colors"
                >
                  Refresh
                </button>
              </div>
            </div>

            {dirLoading ? (
              <div className="p-8 text-center text-slate-400">Loading vacancies...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {directoryJobs.map((j) => (
                  <div key={j.job_id} className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs hover:border-teal-300 transition-all">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-[10px] font-mono text-slate-400">{j.job_id}</span>
                        <h4 className="text-sm font-bold text-slate-900">{j.job_title}</h4>
                        <p className="text-xs text-slate-500">{j.company} • {j.location}</p>
                      </div>
                      <span className="px-2 py-0.5 text-[11px] font-bold bg-teal-50 text-teal-800 rounded border border-teal-200">
                        {j.iti_trade}
                      </span>
                    </div>

                    <div className="mt-3 pt-3 border-t border-slate-100 text-xs">
                      <p className="text-slate-600 line-clamp-2">{j.job_description}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {String(j.required_skills).split(';').map((s) => (
                          <span key={s} className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px]">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: UPSKILLING COURSES CATALOG */}
        {activeTab === 'courses' && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-teal-600" /> Accredited ITI Upskilling Courses Directory
                </h2>
                <p className="text-xs text-slate-500">
                  Curated modules from NPTEL, Skill India Digital, SWAYAM, Coursera, and Udemy.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={dirTradeFilter}
                  onChange={(e) => {
                    setDirTradeFilter(e.target.value);
                    loadDirectoryCourses(e.target.value);
                  }}
                  className="bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 text-xs font-semibold focus:ring-2 focus:ring-teal-500 focus:outline-none"
                >
                  <option value="">All Trades ({meta.trades.length})</option>
                  {meta.trades.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>

                <button
                  onClick={() => loadDirectoryCourses(dirTradeFilter)}
                  className="px-3 py-1.5 text-xs font-semibold bg-slate-800 text-white rounded-lg hover:bg-slate-900 transition-colors"
                >
                  Refresh
                </button>
              </div>
            </div>

            {dirLoading ? (
              <div className="p-8 text-center text-slate-400">Loading courses...</div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {directoryCourses.map((c) => (
                  <div key={c.course_id} className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-center mb-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                          {c.trade}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">{c.course_id}</span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-900">{c.course_name}</h4>
                      <p className="text-xs text-indigo-700 font-semibold mt-1">Skill: {c.skill}</p>
                    </div>

                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                      <span>Provider: <b>{c.provider}</b></span>
                      <span>Duration: <b>{c.duration}</b></span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
}
