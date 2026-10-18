import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  BriefcaseBusiness,
  Building2,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
  BookOpen,
  FileText,
  Info,
  Loader2,
  MapPin,
  RotateCcw,
  Search,
  Sparkles,
  Upload,
  UserRound,
  X,
  ShieldAlert,
  GraduationCap,
  Bookmark,
  ClipboardCheck,
  LogIn,
  LogOut,
  HelpCircle,
  Menu,
  Home
} from 'lucide-react';

const KNOWN_TRADES = [
  'Electrician',
  'Fitter',
  'Welder',
  'Machinist',
  'Electronics Mechanic',
  'Mechanic Motor Vehicle',
  'COPA'
];

const readResumeMatch = () => {
  try {
    return JSON.parse(sessionStorage.getItem('iti-resume-match') || 'null');
  } catch {
    return null;
  }
};

const formatPostDate = (value) => {
  if (!value) return 'Recently posted';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Recently posted'
    : new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }).format(date);
};

function Brand({ compact = false }) {
  return (
    <div className={`brand ${compact ? 'brand-compact' : ''}`}>
      <div className="brand-mark"><Sparkles size={19} /></div>
      <div>
        <strong>AI Skill Gap System</strong>
        <span>ITI career workspace</span>
      </div>
    </div>
  );
}

function LoginPage({ authMode, setAuthMode, authRole, setAuthRole, authName, setAuthName, authEmail, setAuthEmail, authPassword, setAuthPassword, authMessage, isAuthBusy, submitAuth, onBack }) {
  const isRegistering = authMode === 'register';
  return (
    <div className="auth-shell">
      <header className="auth-header"><Brand /><button className="auth-back" type="button" onClick={onBack}><ArrowLeft size={16} /> Back to Resume Match</button></header>
      <main className="auth-layout">
        <section className="auth-intro">
          <p className="eyebrow">YOUR NEXT STEP STARTS HERE</p>
          <h1>Build a career that fits your skills.</h1>
          <p>Match your ITI training to relevant roles, understand your skill gaps, and keep your job search organized in one place.</p>
          <div className="auth-points">
            <span><CheckCircle2 size={18} /> Skills based job matches</span>
            <span><CheckCircle2 size={18} /> Clear, explainable recommendations</span>
            <span><CheckCircle2 size={18} /> Saved jobs and application tracking</span>
          </div>
        </section>
        <section className="auth-card" aria-labelledby="auth-title">
          <div className="auth-card-heading">
            <p className="eyebrow">{isRegistering ? 'CREATE YOUR PROFILE' : 'WELCOME BACK'}</p>
            <h2 id="auth-title">{isRegistering ? 'Create your account' : 'Sign in to AI Skill Gap System'}</h2>
            <p>{isRegistering ? 'Set up your account to save jobs and track applications.' : 'Continue your job search where you left off.'}</p>
          </div>
          <form onSubmit={(event) => { event.preventDefault(); submitAuth(); }} className="auth-form">
            {isRegistering && <label>Full name<input autoComplete="name" placeholder="Your full name" value={authName} onChange={(e) => setAuthName(e.target.value)} required /></label>}
            <label>Email address<input autoComplete="email" type="email" placeholder="name@example.com" value={authEmail} onChange={(e) => setAuthEmail(e.target.value)} required /></label>
            <label>Password<input autoComplete={isRegistering ? 'new-password' : 'current-password'} type="password" placeholder={isRegistering ? 'At least 10 characters' : 'Enter your password'} value={authPassword} onChange={(e) => setAuthPassword(e.target.value)} required /></label>
            {isRegistering && <label>Account type<select value={authRole} onChange={(e) => setAuthRole(e.target.value)}><option value="candidate">Candidate</option><option value="employer">Employer</option></select></label>}
            {authMessage && <p role="status" className="auth-message">{authMessage}</p>}
            <button type="submit" className="button button-primary auth-submit" disabled={isAuthBusy || !authEmail || !authPassword || (isRegistering && !authName)}>
              {isAuthBusy ? <><Loader2 size={17} className="animate-spin" /> Please wait…</> : <>{isRegistering ? 'Create account' : 'Sign in'} <ArrowRight size={17} /></>}
            </button>
          </form>
          <p className="auth-switch">{isRegistering ? 'Already have an account?' : 'New to AI Skill Gap System?'} <button type="button" onClick={() => { setAuthMode(isRegistering ? 'login' : 'register'); }}>{isRegistering ? 'Sign in' : 'Create an account'}</button></p>
          <p className="auth-security"><ShieldAlert size={14} /> Your account details are stored securely.</p>
        </section>
      </main>
      <footer className="auth-footer">AI Skill Gap System · Employability support for ITI graduates</footer>
    </div>
  );
}

export default function App() {
  const [step, setStep] = useState(() => window.location.pathname === '/resume-match' ? 2 : 1);
  const [activeNav, setActiveNav] = useState(() => window.location.pathname === '/resume-match' ? 'resume' : 'home');
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [fileName, setFileName] = useState(() => readResumeMatch()?.fileName || '');
  const [isUploading, setIsUploading] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [validationStatus, setValidationStatus] = useState(() => readResumeMatch()?.validationStatus || null);
  const [validationMessage, setValidationMessage] = useState(() => readResumeMatch()?.validationMessage || '');
  const [documentType, setDocumentType] = useState('RESUME');
  const [rejectionReason, setRejectionReason] = useState(null);

  const [profile, setProfile] = useState(() => readResumeMatch()?.profile || ({
    name: 'Candidate Profile',
    iti_trade: '',
    experience: 0.0,
    skills: [],
    certifications: [],
    qualification: [],
    is_resume: true,
  }));

  const [verified, setVerified] = useState(() => Boolean(readResumeMatch()?.verified));
  const [skillInput, setSkillInput] = useState('');
  const [certInput, setCertInput] = useState('');
  const [jobs, setJobs] = useState(() => readResumeMatch()?.jobs || []);
  const [selectedJob, setSelectedJob] = useState(null);
  const [query, setQuery] = useState('');
  const [tradeFilter, setTradeFilter] = useState('All');
  const [samples, setSamples] = useState({});
  const [jobSources, setJobSources] = useState([]);
  const [learningSources, setLearningSources] = useState([]);
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('iti-auth-token') || '');
  const [authUser, setAuthUser] = useState(null);
  const [authMode, setAuthMode] = useState('login');
  const [authRole, setAuthRole] = useState('candidate');
  const [employerJobs, setEmployerJobs] = useState([]);
  const [adminJobs, setAdminJobs] = useState([]);
  const [adminUsers, setAdminUsers] = useState([]);
  const [employerApplications, setEmployerApplications] = useState([]);
  const [approvedEmployerJobs, setApprovedEmployerJobs] = useState([]);
  const [homeFeedLoading, setHomeFeedLoading] = useState(true);
  const [homeFeedError, setHomeFeedError] = useState('');
  const [homeLastUpdated, setHomeLastUpdated] = useState(null);
  const [postForm, setPostForm] = useState({ title: '', trade: 'Electrician', company: '', location: '', description: '', required_skills: '', experience_required: 0 });
  const [authName, setAuthName] = useState('');
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authMessage, setAuthMessage] = useState('');
  const [isAuthBusy, setIsAuthBusy] = useState(false);
  const [savedJobs, setSavedJobs] = useState(() => {
    try { return JSON.parse(localStorage.getItem('iti-saved-jobs') || '[]'); } catch { return []; }
  });
  const [applications, setApplications] = useState(() => {
    try { return JSON.parse(localStorage.getItem('iti-applications') || '[]'); } catch { return []; }
  });

  const fileInputRef = useRef(null);

  const navigateTo = (path) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  };

  const refreshApprovedEmployerJobs = async () => {
    setHomeFeedLoading(true);
    try {
      const response = await fetch('/api/jobs/approved');
      if (!response.ok) throw new Error('Company postings could not be refreshed.');
      const data = await response.json();
      setApprovedEmployerJobs(data.jobs || []);
      setHomeFeedError('');
      setHomeLastUpdated(new Date());
    } catch {
      setHomeFeedError('Company postings could not be refreshed. Showing the latest data we have.');
    } finally {
      setHomeFeedLoading(false);
    }
  };

  useEffect(() => {
    const handlePopState = () => setCurrentPath(window.location.pathname);
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    refreshApprovedEmployerJobs();
    const refreshTimer = window.setInterval(refreshApprovedEmployerJobs, 60_000);
    return () => window.clearInterval(refreshTimer);
  }, []);

  // Load samples and metadata on mount
  useEffect(() => {
    fetch('/api/samples')
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => setSamples(data))
      .catch(() => {});

    fetch('/api/job-sources')
      .then((res) => (res.ok ? res.json() : { sources: [] }))
      .then((data) => setJobSources(data.sources || []))
      .catch(() => {});

    fetch('/api/learning-sources')
      .then((res) => (res.ok ? res.json() : { sources: [] }))
      .then((data) => setLearningSources(data.sources || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!authToken) return;
    const headers = { Authorization: `Bearer ${authToken}` };
    Promise.all([
      fetch('/api/auth/me', { headers }),
      fetch('/api/account/saved-jobs', { headers }),
      fetch('/api/account/applications', { headers }),
    ]).then(async ([meRes, savedRes, appsRes]) => {
      if (!meRes.ok) throw new Error('Session expired');
      const me = await meRes.json();
      const saved = savedRes.ok ? await savedRes.json() : { jobs: [] };
      const apps = appsRes.ok ? await appsRes.json() : { applications: [] };
      setAuthUser(me.user);
      setSavedJobs(saved.jobs || []);
      setApplications(apps.applications || []);
      if (me.user.role === 'employer' || me.user.role === 'admin') setActiveNav(me.user.role);
      if (me.user.role === 'employer') {
        const jobsRes = await fetch('/api/employer/jobs', { headers });
        if (jobsRes.ok) setEmployerJobs((await jobsRes.json()).jobs || []);
        const appsRes = await fetch('/api/employer/applications', { headers });
        if (appsRes.ok) setEmployerApplications((await appsRes.json()).applications || []);
      }
      if (me.user.role === 'admin') {
        const [jobsRes, usersRes] = await Promise.all([
          fetch('/api/admin/jobs', { headers }), fetch('/api/admin/users', { headers })
        ]);
        if (jobsRes.ok) setAdminJobs((await jobsRes.json()).jobs || []);
        if (usersRes.ok) setAdminUsers((await usersRes.json()).users || []);
      }
      setAuthMessage('');
    }).catch(() => {
      setAuthToken('');
      setAuthUser(null);
      localStorage.removeItem('iti-auth-token');
      setAuthMessage('Your session expired. Sign in again to sync saved jobs and applications.');
    });
  }, [authToken]);

  const submitAuth = async () => {
    setIsAuthBusy(true);
    setAuthMessage('');
    try {
      const endpoint = authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
      const body = authMode === 'register'
        ? { full_name: authName, email: authEmail, password: authPassword, role: authRole }
        : { email: authEmail, password: authPassword };
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Authentication failed.');
      localStorage.setItem('iti-auth-token', data.access_token);
      setAuthUser(data.user);
      setAuthToken(data.access_token);
      setAuthPassword('');
      setAuthMessage(`Signed in as ${data.user.full_name}.`);
      setActiveNav(data.user.role === 'employer' ? 'employer' : data.user.role === 'admin' ? 'admin' : 'home');
      navigateTo('/');
    } catch (error) {
      setAuthMessage(error.message || 'Unable to sign in.');
    } finally {
      setIsAuthBusy(false);
    }
  };

  const signOut = async () => {
    if (authToken) {
      try { await fetch('/api/auth/logout', { method: 'POST', headers: { Authorization: `Bearer ${authToken}` } }); } catch {}
    }
    localStorage.removeItem('iti-auth-token');
    setAuthToken('');
    setAuthUser(null);
    setActiveNav('home');
    setAuthMessage('Signed out. Your browser-local records remain on this device.');
  };

  useEffect(() => {
    localStorage.setItem('iti-saved-jobs', JSON.stringify(savedJobs));
  }, [savedJobs]);

  useEffect(() => {
    localStorage.setItem('iti-applications', JSON.stringify(applications));
  }, [applications]);

  const isJobSaved = (jobId) => savedJobs.some((job) => String(job.job_id) === String(jobId));

  const toggleSavedJob = async (job) => {
    const exists = savedJobs.some((item) => String(item.job_id) === String(job.job_id));
    setSavedJobs((current) => exists
      ? current.filter((item) => String(item.job_id) !== String(job.job_id))
      : [...current, job]);
    if (authToken) {
      try {
        await fetch(exists
          ? `/api/account/saved-jobs/${encodeURIComponent(job.job_id)}`
          : '/api/account/saved-jobs', {
          method: exists ? 'DELETE' : 'POST',
          headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
          ...(exists ? {} : { body: JSON.stringify({ job }) }),
        });
      } catch { setAuthMessage('Could not sync saved job to your account.'); }
    }
  };

  const markApplied = async (job, employerJobPostId = null) => {
    if (applications.some((item) => String(item.job_id) === String(job.job_id))) return;
    const application = {
      ...job,
      job_id: job.job_id,
      applied_at: new Date().toISOString(),
      status: 'Applied',
      source_status: job.record_status || 'UNVERIFIED_SAMPLE',
    };
    setApplications((current) => [...current, application]);
    if (authToken) {
      try {
        const response = await fetch('/api/account/applications', {
          method: 'POST',
          headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ job, employer_job_post_id: employerJobPostId }),
        });
        if (!response.ok) throw new Error('sync failed');
      } catch { setAuthMessage('Could not sync application to your account.'); }
    }
  };

  // Handle actual file upload to backend
  const handleFileUpload = async (file) => {
    if (!file) return;

    sessionStorage.removeItem('iti-resume-match');
    setJobs([]);
    setStep(1);
    if (window.location.pathname !== '/') navigateTo('/');
    setFileName(file.name);
    setIsUploading(true);
    setValidationStatus(null);
    setValidationMessage('');
    setRejectionReason(null);
    setVerified(false);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/upload-resume', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const responseText = await res.text();
        let detail = responseText;
        try {
          const parsed = JSON.parse(responseText);
          detail = parsed.detail || parsed.message || responseText;
        } catch {
          // Keep the plain-text response; proxies and servers may not return JSON.
        }
        const snippet = String(detail || res.statusText || 'Unknown server error').slice(0, 700);
        throw new Error(`Upload failed (HTTP ${res.status}): ${snippet}`);
      }

      const data = await res.json();
      setValidationStatus(data.validation_status);
      setValidationMessage(data.message || '');
      setDocumentType(data.document_type || 'RESUME');

      if (data.validation_status === 'NOT_A_RESUME') {
        setRejectionReason(
          data.message ||
          'The uploaded document was identified as an academic survey or research paper, not a candidate resume/CV.'
        );
        setProfile({
          name: file.name.replace(/\.[^/.]+$/, ''),
          iti_trade: '',
          experience: 0.0,
          skills: [],
          certifications: [],
          qualification: [],
          is_resume: false,
        });
      } else {
        setRejectionReason(null);
        const isValidItiProfile = data.validation_status === 'VALID';
        setProfile({
          name: data.profile.name || file.name.replace(/\.[^/.]+$/, ''),
          iti_trade: isValidItiProfile ? data.profile.iti_trade || '' : '',
          experience: isValidItiProfile ? data.profile.experience || 0.0 : 0.0,
          skills: isValidItiProfile ? data.profile.skills || [] : [],
          certifications: isValidItiProfile ? data.profile.certifications || [] : [],
          qualification: isValidItiProfile ? data.profile.qualification || [] : [],
          is_resume: isValidItiProfile,
        });
      }
    } catch (err) {
      // A network/API failure is not proof that the uploaded document is invalid.
      setValidationStatus('API_ERROR');
      setRejectionReason(err.message || 'Error processing document.');
      setValidationMessage(err.message || 'Error processing document.');
      setProfile((prev) => ({ ...prev, is_resume: false, skills: [], iti_trade: '' }));
    } finally {
      setIsUploading(false);
    }
  };

  // Load a quick sample scenario
  const handleLoadSample = (sampleKey) => {
    const sample = samples[sampleKey];
    if (!sample) return;

    const blob = new Blob([sample.text], { type: 'text/plain' });
    // Demo samples contain plain text, even when their display filename uses
    // a PDF/DOCX extension. Send them as .txt so the backend uses text parsing.
    const sampleName = sample.filename || `${sampleKey}_sample`;
    const textFilename = `${sampleName.replace(/\.[^.]+$/, '')}.txt`;
    const file = new File([blob], textFilename, { type: 'text/plain' });
    handleFileUpload(file);
  };

  // Find job recommendations via real API
  const handleFindJobs = async () => {
    if (validationStatus !== 'VALID' || !profile.is_resume || !profile.iti_trade) {
      alert('Only a valid ITI resume can be edited or matched to jobs.');
      return;
    }

    setIsMatching(true);
    try {
      const res = await fetch('/api/match-jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: {
            iti_trade: profile.iti_trade || null,
            skills: profile.skills,
            experience: parseFloat(profile.experience) || 0.0,
            certifications: profile.certifications,
            qualification: profile.qualification,
            is_resume: true,
            validation_status: validationStatus,
          },
          min_threshold: 0.60,
          top_n: 3,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to compute job match scores.');
      }

      const data = await res.json();
      const recs = data.top_recommendations || [];
      setJobs(recs);
      setStep(2);
      setActiveNav('resume');
      sessionStorage.setItem('iti-resume-match', JSON.stringify({
        fileName,
        validationStatus,
        validationMessage,
        profile,
        verified,
        jobs: recs,
      }));
      navigateTo('/resume-match');
      if (recs.length > 0) {
        setSelectedJob(recs[0]);
      }
    } catch (err) {
      alert('Error fetching job recommendations: ' + err.message);
    } finally {
      setIsMatching(false);
    }
  };

  // Filter jobs by search query & trade
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const matchesSearch = `${job.job_title} ${job.company} ${job.location} ${job.iti_trade}`
        .toLowerCase()
        .includes(query.toLowerCase());
      const matchesTrade =
        tradeFilter === 'All' ||
        (tradeFilter === 'Exact' && job.trade_match_type === 'Exact Trade') ||
        (tradeFilter === 'Related' && job.trade_match_type === 'Related Trade');
      return matchesSearch && matchesTrade;
    });
  }, [jobs, query, tradeFilter]);

  const portalTradeActivity = useMemo(() => {
    const counts = approvedEmployerJobs.reduce((result, post) => {
      const trade = post.trade?.trim();
      if (trade) result[trade] = (result[trade] || 0) + 1;
      return result;
    }, {});
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [approvedEmployerJobs]);

  // Skill management helpers
  const handleAddSkill = (e) => {
    if (e.key === 'Enter' && skillInput.trim()) {
      e.preventDefault();
      const val = skillInput.trim();
      if (!profile.skills.some((s) => s.toLowerCase() === val.toLowerCase())) {
        setProfile({ ...profile, skills: [...profile.skills, val] });
      }
      setSkillInput('');
    }
  };

  const handleRemoveSkill = (skillToRemove) => {
    setProfile({
      ...profile,
      skills: profile.skills.filter((s) => s !== skillToRemove),
    });
  };

  const handleAddCert = (e) => {
    if (e.key === 'Enter' && certInput.trim()) {
      e.preventDefault();
      const val = certInput.trim();
      if (!profile.certifications.some((c) => c.toLowerCase() === val.toLowerCase())) {
        setProfile({ ...profile, certifications: [...profile.certifications, val] });
      }
      setCertInput('');
    }
  };

  const handleRemoveCert = (certToRemove) => {
    setProfile({
      ...profile,
      certifications: profile.certifications.filter((c) => c !== certToRemove),
    });
  };

  const applyToEmployerPost = async (job) => {
    if (!authUser || authUser.role !== 'candidate') {
      setAuthMessage('Sign in with a candidate account to apply to employer-posted jobs.');
      return;
    }
    const mappedJob = {
      job_id: `EMP-${job.id}`,
      job_title: job.title,
      company: job.company,
      location: job.location,
      iti_trade: job.trade,
      job_description: job.description,
      required_skills: job.required_skills || [],
      record_status: 'EMPLOYER_SUBMITTED_ADMIN_APPROVED',
      employer_job_post_id: job.id,
    };
    const response = await fetch('/api/account/applications', {
      method: 'POST',
      headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ job: mappedJob, employer_job_post_id: job.id }),
    });
    const data = await response.json();
    if (!response.ok) { setAuthMessage(data.detail || 'Application could not be submitted.'); return; }
    setApplications((current) => current.some((item) => item.job_id === mappedJob.job_id) ? current : [...current, { ...mappedJob, ...data.application }]);
    setAuthMessage(`Application submitted to ${job.company}.`);
  };

  const reviewEmployerApplication = async (application, status) => {
    const response = await fetch(`/api/employer/applications/${application.user_id}/${encodeURIComponent(application.job_id)}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ status, note: application.employer_note || '' }),
    });
    const data = await response.json();
    if (!response.ok) { setAuthMessage(data.detail || 'Could not update application.'); return; }
    setEmployerApplications((current) => current.map((item) =>
      item.user_id === application.user_id && item.job_id === application.job_id ? data.application : item));
    setAuthMessage(`Application status updated to ${status}.`);
  };

  const submitJobPost = async () => {
    if (!authToken) return;
    try {
      const response = await fetch('/api/employer/jobs', {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...postForm, required_skills: postForm.required_skills.split(',').map((s) => s.trim()).filter(Boolean), experience_required: Number(postForm.experience_required) || 0 }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not submit job.');
      setEmployerJobs((current) => [data.job, ...current]);
      setPostForm({ title: '', trade: 'Electrician', company: '', location: '', description: '', required_skills: '', experience_required: 0 });
      setAuthMessage('Job submitted. It will appear publicly after admin approval.');
    } catch (error) { setAuthMessage(error.message); }
  };

  const moderateJob = async (jobId, status) => {
    try {
      const response = await fetch(`/api/admin/jobs/${jobId}/moderate`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Moderation failed.');
      setAdminJobs((current) => current.map((job) => job.id === jobId ? data.job : job));
      setAuthMessage(`Job #${jobId} ${status}d.`);
    } catch (error) { setAuthMessage(error.message); }
  };

  if (currentPath === '/login') {
    return <LoginPage authMode={authMode} setAuthMode={setAuthMode} authRole={authRole} setAuthRole={setAuthRole} authName={authName} setAuthName={setAuthName} authEmail={authEmail} setAuthEmail={setAuthEmail} authPassword={authPassword} setAuthPassword={setAuthPassword} authMessage={authMessage} isAuthBusy={isAuthBusy} submitAuth={submitAuth} onBack={() => navigateTo('/')} />;
  }

  const navItems = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'resume', label: 'Resume Match', icon: FileText },
    { id: 'saved', label: 'Saved & Applied', icon: Bookmark },
    ...(authUser?.role === 'employer' ? [{ id: 'employer', label: 'Employer workspace', icon: Building2 }] : []),
    ...(authUser?.role === 'admin' ? [{ id: 'admin', label: 'Admin moderation', icon: ShieldAlert }] : []),
    ...(authUser?.role === 'candidate' && approvedEmployerJobs.length ? [{ id: 'vacancies', label: 'Employer vacancies', icon: BriefcaseBusiness }] : []),
    { id: 'help', label: 'Help', icon: HelpCircle },
  ];

  return (
    <div className="app-shell">
      <div className="workspace-layout">
        <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
          <div className="sidebar-brand"><Brand /></div>
          <div className="sidebar-label">WORKSPACE</div>
          <nav className="sidebar-nav" aria-label="Main navigation">
            {navItems.map(({ id, label, icon: Icon }) => (
              <button key={id} type="button" className={`nav-item ${activeNav === id ? 'nav-item-active' : ''}`} onClick={() => { setActiveNav(id); setMobileNavOpen(false); if (id === 'home' && currentPath !== '/') navigateTo('/'); if (id === 'resume') { setStep(1); if (currentPath !== '/') navigateTo('/'); } if (id === 'saved' && step === 3) setStep(jobs.length ? 2 : 1); }}>
                <Icon size={18} strokeWidth={1.9} /><span>{label}</span>{id === 'saved' && savedJobs.length > 0 && <small className="nav-count">{savedJobs.length}</small>}
              </button>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="sidebar-tip"><Sparkles size={16} /><p>Make your next move with confidence.</p></div>
            {authUser ? (
              <div className="sidebar-user">
                <span className="avatar">{authUser.full_name?.charAt(0)?.toUpperCase() || <UserRound size={15} />}</span>
                <span className="sidebar-user-name"><strong>{authUser.full_name}</strong><small>{authUser.role}</small></span>
                <button type="button" className="sidebar-signout" aria-label="Sign out" title="Sign out" onClick={signOut}><LogOut size={16} /></button>
              </div>
            ) : <button type="button" className="sidebar-login" onClick={() => navigateTo('/login')}><LogIn size={17} /> Sign in</button>}
          </div>
        </aside>
        <div className="workspace-main">
          <header className="topbar">
            <button type="button" className="mobile-menu" aria-label="Open navigation" onClick={() => setMobileNavOpen(!mobileNavOpen)}><Menu size={20} /></button>
            <div className="breadcrumb"><span>AI Skill Gap System</span><span className="breadcrumb-divider">/</span><strong>{navItems.find((item) => item.id === activeNav)?.label || 'Resume Match'}</strong></div>
            <button className="topbar-help" type="button" onClick={() => setActiveNav('help')}><HelpCircle size={17} /> Help</button>
          </header>
          <main className="content">
        {authMessage && <div className="status-banner" role="status"><Info size={17} /><span>{authMessage}</span><button type="button" aria-label="Dismiss message" onClick={() => setAuthMessage('')}><X size={16} /></button></div>}
        {activeNav === 'home' && (
          <section className="home-page">
            <div className="home-hero">
              <p className="home-kicker">ITI CAREER PULSE</p>
              <h1>Stay informed. Plan your next step.</h1>
              <p>Follow trade related hiring, apprenticeship openings, training notices, and the steps that move your ITI career forward.</p>
              <div className="home-live-note"><span className="live-indicator" /> Portal approved postings refresh every minute <span className="home-live-divider">·</span> Official notices open at their source</div>
            </div>

            <div className="home-feed-section">
              <div className="home-section-heading">
                <div><p className="eyebrow">CURRENT PORTAL SIGNALS</p><h2>What’s happening in this portal</h2><p>Approved company posts offer a snapshot of employer activity here, not the whole job market.</p></div>
                <div className="home-refresh-wrap">
                  <span>{homeLastUpdated ? `Updated ${homeLastUpdated.toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })}` : homeFeedLoading ? 'Checking updates…' : 'Waiting for first update'}</span>
                  <button type="button" className="home-refresh-button" onClick={refreshApprovedEmployerJobs} disabled={homeFeedLoading}><RotateCcw size={15} className={homeFeedLoading ? 'refresh-spinning' : ''} /> Refresh</button>
                </div>
              </div>

              {homeFeedError && <div className="home-feed-error" role="status"><Info size={16} /> {homeFeedError}</div>}

              {homeFeedLoading && approvedEmployerJobs.length === 0 ? (
                <div className="home-empty-state"><Loader2 size={22} className="refresh-spinning" /><p>Checking for new company postings…</p></div>
              ) : approvedEmployerJobs.length ? (
                <div className="company-post-grid">
                  {approvedEmployerJobs.slice(0, 3).map((post) => (
                    <article className="company-post-card" key={post.id}>
                      <div className="company-post-header">
                        <span className="company-post-mark">{post.company?.charAt(0)?.toUpperCase() || <Building2 size={18} />}</span>
                        <div className="company-post-source"><strong>{post.company}</strong><span><Clock size={13} /> Posted {formatPostDate(post.created_at)}</span></div>
                        <span className="approved-tag"><CheckCircle2 size={13} /> Approved</span>
                      </div>
                      <h3>{post.title}</h3>
                      <div className="company-post-meta"><span>{post.trade}</span><span><MapPin size={14} /> {post.location}</span><span>{post.experience_required || 0}+ years</span></div>
                      <p className="company-post-description">{post.description}</p>
                      {!!post.required_skills?.length && <div className="company-post-skills">{post.required_skills.slice(0, 4).map((skill) => <span key={skill}>{skill}</span>)}</div>}
                      <div className="company-post-footer"><small>Employer posting · approved by this portal</small></div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="home-empty-state"><BriefcaseBusiness size={25} /><h3>No approved company updates yet</h3><p>Use the official job and apprenticeship sources below to check current vacancies while this portal’s feed is quiet.</p></div>
              )}
              <div className="home-activity-strip">
                <div className="home-activity-summary"><strong>{approvedEmployerJobs.length}</strong><span>approved postings in this portal</span></div>
                <div className="home-activity-trades"><span className="home-activity-label">Trades represented here</span>{portalTradeActivity.length ? portalTradeActivity.slice(0, 6).map(([trade, count]) => <span className="home-trade-chip" key={trade}>{trade}<b>{count}</b></span>) : <span className="home-activity-empty">No trade activity to summarize yet</span>}</div>
              </div>
            </div>

            <div className="home-source-section">
              <div className="home-section-heading"><div><p className="eyebrow">OFFICIAL UPDATES</p><h2>Follow the sources that shape your career</h2><p>Check government notices and job boards for current openings, training changes, exams, and deadlines.</p></div></div>
              <div className="home-source-grid">
                {jobSources.filter((source) => /^https?:\/\//i.test(source.source_url || '')).map((source) => (
                  <a key={source.source_id} className="home-source-card" href={source.source_url} target="_blank" rel="noreferrer">
                    <span className="home-source-icon"><ExternalLink size={17} /></span>
                    <strong>{source.source_name}</strong>
                    <span>{source.category} · Checked {source.checked_on || 'at source'}</span>
                    <small>View latest at official source <ArrowRight size={13} /></small>
                  </a>
                ))}
              </div>
            </div>

            <section className="home-journey-section" aria-labelledby="career-journey-title">
              <div className="home-section-heading"><div><p className="eyebrow">YOUR ITI CAREER JOURNEY</p><h2 id="career-journey-title">From trade training to your next role</h2><p>Use these milestones to turn updates into practical next steps.</p></div></div>
              <div className="home-journey-grid">
                {[
                  ['01', 'Build trade skills', 'Keep practical skills, safety training, and certificates current for your trade.'],
                  ['02', 'Track openings', 'Check job and apprenticeship notices regularly, including eligibility and closing dates.'],
                  ['03', 'Prepare your application', 'Keep your resume and supporting documents accurate and ready to share.'],
                  ['04', 'Apply and follow up', 'Use the employer’s official process, record your applications, and continue learning.'],
                ].map(([number, title, description]) => <article className="home-journey-card" key={number}><span>{number}</span><h3>{title}</h3><p>{description}</p></article>)}
              </div>
            </section>
          </section>
        )}
        {authUser?.role === 'employer' && activeNav === 'employer' && (
          <section className="comparison-panel" style={{ marginBottom: '20px' }}>
            <div className="comparison-heading"><span><BriefcaseBusiness size={16} /></span><div><h3>Employer Job Management</h3><p>New listings are pending until an administrator approves them.</p></div></div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: '10px' }}>
              <input aria-label="Job title" placeholder="Job title" value={postForm.title} onChange={(e) => setPostForm({ ...postForm, title: e.target.value })} />
              <select aria-label="ITI trade" value={postForm.trade} onChange={(e) => setPostForm({ ...postForm, trade: e.target.value })}>{KNOWN_TRADES.map((trade) => <option key={trade}>{trade}</option>)}</select>
              <input aria-label="Company" placeholder="Company" value={postForm.company} onChange={(e) => setPostForm({ ...postForm, company: e.target.value })} />
              <input aria-label="Location" placeholder="Location" value={postForm.location} onChange={(e) => setPostForm({ ...postForm, location: e.target.value })} />
              <input aria-label="Required skills" placeholder="Required skills (comma separated)" value={postForm.required_skills} onChange={(e) => setPostForm({ ...postForm, required_skills: e.target.value })} />
              <input aria-label="Required experience" type="number" min="0" max="60" placeholder="Experience required (years)" value={postForm.experience_required} onChange={(e) => setPostForm({ ...postForm, experience_required: e.target.value })} />
            </div>
            <textarea aria-label="Job description" placeholder="Job description (at least 20 characters)" value={postForm.description} onChange={(e) => setPostForm({ ...postForm, description: e.target.value })} />
            <button type="button" className="button button-primary" onClick={submitJobPost} disabled={!postForm.title || !postForm.company || !postForm.location || postForm.description.length < 20}>Submit job for review</button>
            <h4>Your listings</h4>
            {employerJobs.map((job) => <p key={job.id}>#{job.id} · {job.title} — <strong>{job.status}</strong></p>)}
            <h4>Candidate applications</h4>
            {employerApplications.length === 0 ? <p className="muted">No candidate applications have been linked to your approved listings yet.</p> : employerApplications.map((application) => (
              <div key={`${application.user_id}-${application.job_id}`} style={{ padding: '12px 0', borderTop: '1px solid #e5e9e7' }}>
                <strong>{application.candidate_name}</strong> · {application.candidate_email}
                <p>{application.posted_title} — {application.status}</p>
                <textarea aria-label={`Employer note for ${application.candidate_name}`} placeholder="Private review note" value={application.employer_note || ''} onChange={(e) => setEmployerApplications((current) => current.map((item) => item.user_id === application.user_id && item.job_id === application.job_id ? { ...item, employer_note: e.target.value } : item))} />
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
                  {['Reviewing', 'Interview', 'Offer', 'Rejected'].map((status) => <button type="button" className="button button-quiet" key={status} onClick={() => reviewEmployerApplication(application, status)}>{status}</button>)}
                </div>
              </div>
            ))}
          </section>
        )}
        {authUser?.role === 'candidate' && activeNav === 'vacancies' && approvedEmployerJobs.length > 0 && (
          <section className="comparison-panel" style={{ marginBottom: '20px' }}>
            <div className="comparison-heading"><span><BriefcaseBusiness size={16} /></span><div><h3>Approved Employer Vacancies</h3><p>These listings were approved by an administrator. Confirm details with the employer before making decisions.</p></div></div>
            {approvedEmployerJobs.map((job) => <div key={job.id} style={{ padding: '12px 0', borderTop: '1px solid #e5e9e7' }}>
              <strong>{job.title}</strong> · {job.company}
              <p>{job.trade} · {job.location} · Experience: {job.experience_required} years</p>
              <p>{job.description}</p>
              <p>Skills: {(job.required_skills || []).join(', ') || 'Not specified'}</p>
              <button type="button" className="button button-primary" onClick={() => applyToEmployerPost(job)} disabled={applications.some((item) => item.job_id === `EMP-${job.id}`)}>Apply to this job</button>
            </div>)}
          </section>
        )}
        {authUser?.role === 'admin' && activeNav === 'admin' && (
          <section className="comparison-panel" style={{ marginBottom: '20px' }}>
            <div className="comparison-heading"><span><ShieldAlert size={16} /></span><div><h3>Administrator Moderation</h3><p>Review employer submissions and manage account roles.</p></div></div>
            <h4>Job submissions</h4>
            {adminJobs.map((job) => <div key={job.id} style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap', padding: '8px 0' }}>
              <span style={{ flex: 1 }}>#{job.id} · {job.title} ({job.company}) — {job.status}</span>
              {job.status === 'pending' && <><button type="button" className="button button-primary" onClick={() => moderateJob(job.id, 'approve')}>Approve</button><button type="button" className="button button-quiet" onClick={() => moderateJob(job.id, 'reject')}>Reject</button></>}
            </div>)}
            <h4>Registered users</h4>
            {adminUsers.map((item) => <p key={item.id}>{item.full_name} · {item.email} · {item.role}</p>)}
          </section>
        )}
        {activeNav === 'resume' && <div className="page-heading">
          <div>
            <p className="eyebrow">VOCATIONAL CAREER MATCHING</p>
            <h1>{step === 3 ? 'Match Details' : currentPath === '/resume-match' ? 'Job Matches & Recommendations' : 'Resume Match'}</h1>
            <p className="subheading">
              {step === 3
                ? 'Review why this role matches, what skills you bring, and what to learn next.'
                : currentPath === '/resume-match'
                  ? 'Explore roles ranked against your ITI trade and resume, with skill gaps and learning suggestions.'
                  : 'Upload your resume to see tailored job matches, skill gaps, and learning suggestions together.'}
            </p>
          </div>
          {authUser && <div className="welcome-chip"><span className="avatar">{authUser.full_name?.charAt(0)?.toUpperCase()}</span><span>Welcome back, <strong>{authUser.full_name.split(' ')[0]}</strong></span></div>}
        </div>}

        {/* STEP 1: UPLOAD & VALIDATION */}
        {activeNav === 'resume' && currentPath !== '/resume-match' && step !== 3 && (
          <section className="panel resume-panel">
            {/* Quick Demo Scenarios */}
            <div className="demo-bar">
              <div className="demo-bar-title">Quick Test Scenarios</div>
              <div className="demo-pills">
                <button
                  type="button"
                  className="demo-pill"
                  onClick={() => handleLoadSample('electrician')}
                >
                  ⚡ ITI Electrician (Valid)
                </button>
                <button
                  type="button"
                  className="demo-pill"
                  onClick={() => handleLoadSample('fitter')}
                >
                  🔧 ITI Fitter (Valid)
                </button>
                <button
                  type="button"
                  className="demo-pill"
                  onClick={() => handleLoadSample('unclear')}
                >
                  ⚠️ ITI Unclear Trade
                </button>
                <button
                  type="button"
                  className="demo-pill"
                  onClick={() => handleLoadSample('cse')}
                >
                  💻 CSE Graduate (Non-ITI)
                </button>
                <button
                  type="button"
                  className="demo-pill demo-pill-danger"
                  onClick={() => handleLoadSample('survey_paper')}
                >
                  📄 Academic Survey Paper (Test Rejection)
                </button>
              </div>
            </div>

            {/* Upload Area / Dropzone */}
            {!fileName && !isUploading && (
              <div
                className="dropzone"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const file = e.dataTransfer.files?.[0];
                  if (file) handleFileUpload(file);
                }}
              >
                <div className="upload-icon">
                  <Upload size={24} />
                </div>
                <h2>Upload Candidate Resume</h2>
                <p>Drag and drop a PDF, DOCX, or TXT file to validate credentials</p>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload size={16} /> Choose file
                </button>
                <input
                  ref={fileInputRef}
                  hidden
                  type="file"
                  accept=".pdf,.docx,.txt"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleFileUpload(file);
                  }}
                />
                <small>Accepted formats: PDF, DOCX, TXT · Maximum size: 10 MB</small>
              </div>
            )}

            {/* Uploading State */}
            {isUploading && (
              <div className="dropzone">
                <div className="upload-icon" style={{ animation: 'spin 1.5s linear infinite' }}>
                  <Loader2 size={28} />
                </div>
                <h2>Analyzing Document...</h2>
                <p>Inspecting structure, validating ITI credentials, and verifying resume format.</p>
              </div>
            )}

            {/* Extracted Details & Validation Banner */}
            {fileName && !isUploading && (
              <div className="form-wrap">
                {/* File Banner */}
                <div className="file-banner">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileText size={18} />
                    <strong>{fileName}</strong>
                  </div>
                  <button
                    type="button"
                    className="icon-button"
                    aria-label="Remove resume"
                    onClick={() => {
                      setFileName('');
                      setValidationStatus(null);
                      setRejectionReason(null);
                    }}
                  >
                    <X size={17} />
                  </button>
                </div>

                {/* Validation Status Banners */}
                {validationStatus === 'NOT_A_RESUME' && (
                  <div className="alert-box alert-rejected">
                    <div className="alert-box-icon">
                      <ShieldAlert size={24} />
                    </div>
                    <div>
                      <h4>Document Rejected — Not a Candidate Resume</h4>
                      <p>{rejectionReason || validationMessage || 'The uploaded document does not appear to be a candidate resume.'}</p>
                      <p style={{ marginTop: '6px', fontSize: '13px', opacity: 0.9 }}>
                        Please upload a resume or CV. Academic papers and unrelated documents cannot be used for ITI job matching.
                      </p>
                      <button
                        type="button"
                        className="button button-quiet"
                        style={{ marginTop: '12px', background: '#fff' }}
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <RotateCcw size={15} /> Upload a Valid Candidate Resume
                      </button>
                    </div>
                  </div>
                )}

                {validationStatus === 'API_ERROR' && (
                  <div className="alert-box alert-rejected" role="alert">
                    <div className="alert-box-icon">
                      <ShieldAlert size={24} />
                    </div>
                    <div>
                      <h4>We Couldn't Analyze This File</h4>
                      <p>{rejectionReason || validationMessage || 'The resume service could not process this upload.'}</p>
                      <p style={{ marginTop: '6px', fontSize: '13px', opacity: 0.9 }}>
                        This is a processing error, not a document rejection. Check that the backend is running, then try again.
                      </p>
                      <button
                        type="button"
                        className="button button-quiet"
                        style={{ marginTop: '12px', background: '#fff' }}
                        onClick={() => fileInputRef.current?.click()}
                      >
                        <RotateCcw size={15} /> Try Another File
                      </button>
                    </div>
                  </div>
                )}

                {validationStatus === 'VALID' && (
                  <div className="alert-box alert-valid">
                    <div className="alert-box-icon">
                      <CheckCircle2 size={24} />
                    </div>
                    <div>
                      <h4>Valid ITI Candidate Profile Detected</h4>
                      <p>{validationMessage}</p>
                    </div>
                  </div>
                )}

                {validationStatus === 'TRADE_UNCLEAR' && (
                  <div className="alert-box alert-warning">
                    <div className="alert-box-icon">
                      <AlertTriangle size={24} />
                    </div>
                    <div>
                      <h4>Trade Unclear — ITI Indicators Found</h4>
                      <p>{validationMessage}</p>
                    </div>
                  </div>
                )}

                {validationStatus === 'NOT_ITI' && (
                  <div className="alert-box alert-info">
                    <div className="alert-box-icon">
                      <Info size={24} />
                    </div>
                    <div>
                      <h4>Notice: Non-ITI Profile Detected</h4>
                      <p>{validationMessage}</p>
                    </div>
                  </div>
                )}

                {/* Profile editing is available only for a validated ITI resume. */}
                {validationStatus === 'VALID' && (
                  <>
                    <div className="section-title">
                      <div>
                        <p className="eyebrow">CANDIDATE INFORMATION</p>
                        <h2>Review &amp; Edit Profile Attributes</h2>
                      </div>
                      <span className="review-note">Verify extracted technical credentials</span>
                    </div>

                    <div className="form-grid">
                      <label>
                        Candidate Name / Title
                        <input
                          value={profile.name}
                          onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                        />
                      </label>

                      <label>
                        Primary ITI Trade
                        <select
                          value={profile.iti_trade}
                          onChange={(e) =>
                            setProfile({ ...profile, iti_trade: e.target.value })
                          }
                        >
                          <option value="">-- Select ITI Trade --</option>
                          {KNOWN_TRADES.map((t) => (
                            <option key={t} value={t}>
                              {t}
                            </option>
                          ))}
                        </select>
                      </label>

                      <label>
                        Experience (Years)
                        <input
                          type="number"
                          step="0.5"
                          min="0"
                          max="40"
                          value={profile.experience}
                          onChange={(e) =>
                            setProfile({ ...profile, experience: parseFloat(e.target.value) || 0 })
                          }
                        />
                      </label>
                    </div>

                    {/* Skills Input */}
                    <label className="skills-field">
                      Technical Skills ({profile.skills.length} detected)
                      <div className="tag-input">
                        {profile.skills.map((skill) => (
                          <span className="tag" key={skill}>
                            {skill}
                            <button
                              type="button"
                              aria-label={`Remove ${skill}`}
                              onClick={() => handleRemoveSkill(skill)}
                            >
                              <X size={13} />
                            </button>
                          </span>
                        ))}
                        <input
                          value={skillInput}
                          onChange={(e) => setSkillInput(e.target.value)}
                          onKeyDown={handleAddSkill}
                          placeholder="Type a skill and press Enter"
                        />
                      </div>
                      <small className="field-hint">
                        Normalized against ITI master skills taxonomy (skills.csv). Press Enter to add.
                      </small>
                    </label>

                    {/* Certifications Input */}
                    <label className="skills-field" style={{ marginTop: '16px' }}>
                      Recognized Certifications
                      <div className="tag-input">
                        {profile.certifications.map((cert) => (
                          <span className="tag" key={cert}>
                            {cert}
                            <button
                              type="button"
                              aria-label={`Remove ${cert}`}
                              onClick={() => handleRemoveCert(cert)}
                            >
                              <X size={13} />
                            </button>
                          </span>
                        ))}
                        <input
                          value={certInput}
                          onChange={(e) => setCertInput(e.target.value)}
                          onKeyDown={handleAddCert}
                          placeholder="Type certification (e.g. NCVT, Safety Certificate) and press Enter"
                        />
                      </div>
                    </label>

                    {/* Verification Checkbox */}
                    <label className="verify">
                      <input
                        type="checkbox"
                        checked={verified}
                        onChange={(e) => setVerified(e.target.checked)}
                      />
                      <span>
                        I verify that the extracted details above accurately reflect the candidate's qualifications.
                      </span>
                    </label>

                    {/* Action Button */}
                    <div className="form-actions">
                      <button
                        type="button"
                        className="button button-primary"
                        disabled={!verified || isMatching || !profile.iti_trade}
                        onClick={handleFindJobs}
                      >
                        {isMatching ? (
                          <>
                            <Loader2 size={16} className="animate-spin" /> Matching against 1,000 jobs...
                          </>
                        ) : (
                          <>
                            Find Matching ITI Jobs <ArrowRight size={16} />
                          </>
                        )}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}
          </section>
        )}

        {/* STEP 2: JOB RECOMMENDATIONS */}
        {activeNav === 'resume' && currentPath === '/resume-match' && step === 2 && (
          <section>
            <div className="match-page-toolbar">
              <button type="button" className="back-link" onClick={() => { setStep(1); navigateTo('/'); }}>
                <ArrowLeft size={16} /> Back to resume
              </button>
              <span>{profile.iti_trade} · Matched from {fileName || 'your resume'}</span>
            </div>
            <div className="toolbar">
              <div className="search-box">
                <Search size={17} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search job title, company, or location..."
                />
              </div>
            </div>

            <div className="filter-row">
              {['All', 'Exact', 'Related'].map((item) => (
                <button
                  type="button"
                  key={item}
                  className={`filter-pill ${tradeFilter === item ? 'filter-selected' : ''}`}
                  onClick={() => setTradeFilter(item)}
                >
                  {item === 'All' ? 'All Roles' : `${item} Trade`}
                </button>
              ))}
            </div>

            <div className="results-heading">
              <div>
                <p className="eyebrow">RANKED JOB EXAMPLES</p>
                <h2>Top Recommended ITI Roles for {profile.iti_trade}</h2>
              </div>
              <span>{filteredJobs.length} roles matched</span>
            </div>

            {filteredJobs.length === 0 ? (
              <div className="empty-state">
                <Search size={28} />
                <h3>No matching roles found</h3>
                <p>Try clearing filters or adjusting required skills.</p>
              </div>
            ) : (
              <div className="job-grid">
                {filteredJobs.map((job) => {
                  const scorePercent = Math.round((job.final_score || 0) * 100);
                  const isHigh = scorePercent >= 70;
                  const isMid = scorePercent >= 50;

                  return (
                    <button
                      type="button"
                      className="job-card"
                      key={job.job_id}
                      onClick={() => {
                        setSelectedJob(job);
                        setStep(3);
                      }}
                    >
                      <div className="job-card-top">
                        <span className="company-mark">{job.company.charAt(0)}</span>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <span className="employment-tag">
                            {job.trade_match_type || job.iti_trade}
                          </span>
                          <span
                            className={`score-badge ${
                              isHigh ? 'score-high' : isMid ? 'score-mid' : 'score-low'
                            }`}
                          >
                            {scorePercent}% Match
                          </span>
                        </div>
                      </div>

                      <h3>{job.job_title}</h3>
                      <p className="company-name">{job.company}</p>

                      <p className="job-meta">
                        <MapPin size={14} /> {job.location} · Required Exp: {job.experience}
                      </p>

                      <p className="job-description">
                        {job.job_description?.slice(0, 140)}...
                      </p>

                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
                        <small style={{ color: '#27704f', fontWeight: 600 }}>
                          ✓ {job.matched_skills?.length || 0} matched
                        </small>
                        <small style={{ color: '#8a9894' }}>·</small>
                        <small style={{ color: '#966b21', fontWeight: 600 }}>
                          ⚠ {job.missing_skills?.length || 0} skill gaps
                        </small>
                      </div>

                      <div className="job-footer">
                        <strong>Req: ITI {job.iti_trade}</strong>
                        <span>
                          View Skill Gap &amp; Courses <ArrowRight size={15} />
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </section>
        )}

        {/* STEP 3: JOB DETAILS & SKILL GAP ANALYSIS */}
        {activeNav === 'resume' && currentPath === '/resume-match' && step === 3 && selectedJob && (
          <section>
            <button
              type="button"
              className="back-link"
              onClick={() => setStep(2)}
            >
              <ArrowLeft size={16} /> Back to Recommendations
            </button>

            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', margin: '12px 0 18px' }}>
              <button type="button" className="button button-quiet" onClick={() => toggleSavedJob(selectedJob)}>
                <Bookmark size={16} /> {isJobSaved(selectedJob.job_id) ? 'Remove Saved Job' : 'Save Job'}
              </button>
              <button type="button" className="button button-primary" onClick={() => markApplied(selectedJob)} disabled={applications.some((item) => String(item.job_id) === String(selectedJob.job_id))}>
                <ClipboardCheck size={16} /> {applications.some((item) => String(item.job_id) === String(selectedJob.job_id)) ? 'Marked as Applied' : 'Mark as Applied'}
              </button>
              {selectedJob.application_url && /^https?:\/\//i.test(selectedJob.application_url) && (
                <a className="button button-quiet" href={selectedJob.application_url} target="_blank" rel="noreferrer">
                  Open Application Link <ExternalLink size={15} />
                </a>
              )}
            </div>

            <div className="detail-hero">
              <div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className="employment-tag">{selectedJob.iti_trade}</span>
                  <span className="score-badge score-high">
                    {Math.round((selectedJob.final_score || 0) * 100)}% Overall Match
                  </span>
                </div>
                <h2>{selectedJob.job_title}</h2>
                <p className="company-name">{selectedJob.company}</p>
                <p className="job-meta">
                  <MapPin size={14} /> {selectedJob.location} <span>·</span>
                  <Clock size={14} /> {selectedJob.experience} Exp <span>·</span>
                  <Award size={14} /> {selectedJob.qualification}
                </p>
              </div>
            </div>

            <div className="detail-description">
              <p>{selectedJob.job_description}</p>
              {/* 4-Factor Scoring Breakdown */}
              <div style={{ marginTop: '20px' }}>
                <p className="eyebrow">SCORING FORMULA BREAKDOWN</p>
                <div className="breakdown-grid">
                  <div className="breakdown-card">
                    <div className="breakdown-label">50% Skill Match</div>
                    <div className="breakdown-value">
                      {Math.round((selectedJob.skill_score || 0) * 100)}%
                    </div>
                    <div className="breakdown-sub">Weighted overlap + TF-IDF</div>
                  </div>
                  <div className="breakdown-card">
                    <div className="breakdown-label">25% Trade Match</div>
                    <div className="breakdown-value">
                      {Math.round((selectedJob.trade_score || 0) * 100)}%
                    </div>
                    <div className="breakdown-sub">{selectedJob.trade_match_type}</div>
                  </div>
                  <div className="breakdown-card">
                    <div className="breakdown-label">15% Experience</div>
                    <div className="breakdown-value">
                      {Math.round((selectedJob.experience_score || 0) * 100)}%
                    </div>
                    <div className="breakdown-sub">vs {selectedJob.experience}</div>
                  </div>
                  <div className="breakdown-card">
                    <div className="breakdown-label">10% Certification</div>
                    <div className="breakdown-value">
                      {Math.round((selectedJob.certification_score || 0) * 100)}%
                    </div>
                    <div className="breakdown-sub">{selectedJob.certifications || 'Not required'}</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Matched Skills vs Missing Skills */}
            <div className="comparison-grid">
              <div className="comparison-panel">
                <div className="comparison-heading matching">
                  <span>
                    <Check size={16} />
                  </span>
                  <div>
                    <h3>Matched Skills ({selectedJob.matched_skills?.length || 0})</h3>
                    <p>Proficiencies candidate already demonstrates</p>
                  </div>
                </div>
                <div className="skill-pills">
                  {selectedJob.matched_skills && selectedJob.matched_skills.length > 0 ? (
                    selectedJob.matched_skills.map((skill) => (
                      <span className="skill-pill skill-matching" key={skill}>
                        ✓ {skill}
                      </span>
                    ))
                  ) : (
                    <p className="muted">No direct skill overlaps detected for this role.</p>
                  )}
                </div>
              </div>

              <div className="comparison-panel">
                <div className="comparison-heading missing">
                  <span>
                    <ArrowRight size={16} />
                  </span>
                  <div>
                    <h3>Identified Skill Gaps ({selectedJob.missing_skills?.length || 0})</h3>
                    <p>Missing proficiencies required by this job</p>
                  </div>
                </div>
                <div className="skill-pills">
                  {selectedJob.missing_skills && selectedJob.missing_skills.length > 0 ? (
                    selectedJob.missing_skills.map((skill) => (
                      <span className="skill-pill skill-missing" key={skill}>
                        ⚠ {skill}
                      </span>
                    ))
                  ) : (
                    <p className="muted" style={{ color: '#27704f' }}>
                      Candidate meets 100% of the required technical skills!
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Curated Vocational Courses */}
            <div className="learning-section">
              <div className="section-title">
                <div>
                  <p className="eyebrow">VOCATIONAL LEARNING RECOMMENDATIONS</p>
                  <h2>Learning Resources to Explore</h2>
                </div>
              </div>

              {selectedJob.learning_recommendations &&
              selectedJob.learning_recommendations.length > 0 ? (
                <div className="course-grid">
                  {selectedJob.learning_recommendations.map((course, idx) => (
                    <article className="course-card" key={`${course.course_id || idx}`}>
                      <div className="course-icon">
                        <GraduationCap size={18} />
                      </div>
                      <div style={{ flex: 1 }}>
                        <h3>{course.skill} — learning topic</h3>
                        <p>
                          Target Skill: <strong>{course.skill}</strong> · Level: {course.level}
                        </p>
                      </div>
                      {course.resource_url && course.resource_url.startsWith('http') && (
                        <a
                          href={course.resource_url}
                          target="_blank"
                          rel="noreferrer"
                          aria-label={`Open ${course.course_name}`}
                        >
                          <ExternalLink size={16} />
                        </a>
                      )}
                    </article>
                  ))}
                </div>
              ) : (
                <p className="muted">
                  {selectedJob.missing_skills?.length === 0
                    ? 'Candidate possesses all technical skills for this role; no upskilling modules needed.'
                    : 'No topic suggestions found in the current dataset for these missing skills.'}
                </p>
              )}
              <section className="learning-portal-section" aria-labelledby="learning-portals-title">
                <div className="learning-portal-heading">
                  <div><p className="eyebrow">CONTINUE LEARNING</p><h3 id="learning-portals-title">Learning portals and resources</h3></div>
                  <p>Browse trusted starting points. Course availability varies by skill and provider.</p>
                </div>
                <div className="learning-portal-group">
                  <h4>Explore learning portals</h4>
                  <div className="learning-portal-grid">
                    {learningSources.filter((source) => !source.source_name.includes('Study Materials')).map((source) => (
                      <a key={source.source_id} className="learning-portal-card" href={source.source_url} target="_blank" rel="noreferrer">
                        <span className="learning-portal-card-icon"><GraduationCap size={18} /></span>
                        <span className="learning-portal-card-copy"><strong>{source.source_name}</strong><small>{source.category}</small></span>
                        <ExternalLink className="learning-portal-card-link" size={16} aria-hidden="true" />
                      </a>
                    ))}
                  </div>
                </div>
                <div className="learning-portal-group">
                  <h4>Study materials by ITI trade</h4>
                  <div className="learning-portal-grid">
                    {learningSources.filter((source) => source.source_name.includes('Study Materials')).map((source) => (
                      <a key={source.source_id} className="learning-portal-card" href={source.source_url} target="_blank" rel="noreferrer">
                        <span className="learning-portal-card-icon"><BookOpen size={18} /></span>
                        <span className="learning-portal-card-copy"><strong>{source.source_name.replace('Bharat Skills — ', '')}</strong><small>{source.applicable_trades}</small></span>
                        <ExternalLink className="learning-portal-card-link" size={16} aria-hidden="true" />
                      </a>
                    ))}
                  </div>
                </div>
              </section>
            </div>
          </section>
        )}

        {activeNav === 'saved' && (
          <section className="saved-page">
            <div className="page-heading"><div><p className="eyebrow">YOUR JOB SEARCH</p><h1>Saved &amp; Applied</h1><p className="subheading">Keep your shortlist and application progress easy to find.</p></div></div>
            <div className="activity-grid">
              <section className="activity-panel">
                <div className="activity-heading"><span className="activity-icon"><Bookmark size={18} /></span><div><h2>Saved jobs</h2><p>{savedJobs.length} roles in your shortlist</p></div></div>
                {savedJobs.length ? savedJobs.map((job) => <article className="activity-row" key={job.job_id}><div><strong>{job.job_title}</strong><p>{job.company} <span>·</span> {job.location}</p></div><button className="text-action" type="button" onClick={() => { setSelectedJob(job); setStep(3); setActiveNav('resume'); navigateTo('/resume-match'); }}>View match <ArrowRight size={15} /></button></article>) : <div className="activity-empty"><Bookmark size={20} /><p>Jobs you save from your match results will appear here.</p><button type="button" className="text-action" onClick={() => { setActiveNav('resume'); setStep(1); navigateTo('/'); }}>Explore matches <ArrowRight size={15} /></button></div>}
              </section>
              <section className="activity-panel">
                <div className="activity-heading"><span className="activity-icon activity-icon-applied"><ClipboardCheck size={18} /></span><div><h2>Applications</h2><p>{applications.length} roles marked as applied</p></div></div>
                {applications.length ? applications.map((job) => <article className="activity-row" key={job.job_id}><div><strong>{job.job_title}</strong><p>{job.company} <span>·</span> {job.status || 'Applied'}</p></div><span className="application-status">{job.status || 'Applied'}</span></article>) : <div className="activity-empty"><ClipboardCheck size={20} /><p>When you mark a matched role as applied, it will show up here.</p><button type="button" className="text-action" onClick={() => setActiveNav('resume')}>Explore matches <ArrowRight size={15} /></button></div>}
              </section>
            </div>
          </section>
        )}

        {activeNav === 'help' && (
          <section className="help-page">
            <div className="page-heading"><div><p className="eyebrow">SKILLPATH SUPPORT</p><h1>How it works</h1><p className="subheading">A simple guide to getting useful, transparent recommendations.</p></div></div>
            <div className="help-grid">
              <article className="help-card"><span>01</span><h2>Upload your resume</h2><p>Start with a PDF or DOCX resume. We extract trade, experience, qualifications, and skills for your review.</p></article>
              <article className="help-card"><span>02</span><h2>Review your profile</h2><p>Check the detected information, make corrections, and confirm your ITI trade before matching.</p></article>
              <article className="help-card"><span>03</span><h2>Explore matches</h2><p>Compare role fit, matching skills, experience, and certifications. Open a role to see its skill gaps.</p></article>
            </div>
            <button type="button" className="button button-primary" onClick={() => setActiveNav('resume')}>Go to Resume Match <ArrowRight size={16} /></button>
          </section>
        )}
      </main>
        </div>
      </div>
    </div>
  );
}
