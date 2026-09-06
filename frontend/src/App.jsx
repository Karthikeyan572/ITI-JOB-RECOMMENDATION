import { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Award,
  BriefcaseBusiness,
  Check,
  CheckCircle2,
  Clock,
  ExternalLink,
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
  GraduationCap
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

function StepIndicator({ step }) {
  const steps = ['Resume & Validation', 'Top Job Matches', 'Skill Gap & Courses'];
  return (
    <div className="steps" aria-label="Application progress">
      {steps.map((label, index) => {
        const number = index + 1;
        return (
          <div className={`step ${step >= number ? 'step-active' : ''}`} key={label}>
            <span>{step > number ? <Check size={15} /> : number}</span>
            <small>{label}</small>
          </div>
        );
      })}
    </div>
  );
}

export default function App() {
  const [step, setStep] = useState(1);
  const [fileName, setFileName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [isMatching, setIsMatching] = useState(false);
  const [validationStatus, setValidationStatus] = useState(null);
  const [validationMessage, setValidationMessage] = useState('');
  const [documentType, setDocumentType] = useState('RESUME');
  const [rejectionReason, setRejectionReason] = useState(null);

  const [profile, setProfile] = useState({
    name: 'Candidate Profile',
    iti_trade: '',
    experience: 0.0,
    skills: [],
    certifications: [],
    qualification: [],
    is_resume: true,
  });

  const [verified, setVerified] = useState(false);
  const [skillInput, setSkillInput] = useState('');
  const [certInput, setCertInput] = useState('');
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [query, setQuery] = useState('');
  const [tradeFilter, setTradeFilter] = useState('All');
  const [samples, setSamples] = useState({});

  const fileInputRef = useRef(null);

  // Load samples and metadata on mount
  useEffect(() => {
    fetch('/api/samples')
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => setSamples(data))
      .catch(() => {});
  }, []);

  // Handle actual file upload to backend
  const handleFileUpload = async (file) => {
    if (!file) return;

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
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to analyze uploaded document.');
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
          name: file.name.replace(/\.[^/.]+$/, ''),
          iti_trade: isValidItiProfile ? data.profile.iti_trade || '' : '',
          experience: isValidItiProfile ? data.profile.experience || 0.0 : 0.0,
          skills: isValidItiProfile ? data.profile.skills || [] : [],
          certifications: isValidItiProfile ? data.profile.certifications || [] : [],
          qualification: isValidItiProfile ? data.profile.qualification || [] : [],
          is_resume: isValidItiProfile,
        });
      }
    } catch (err) {
      setValidationStatus('NOT_A_RESUME');
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
    const file = new File([blob], sample.filename, { type: 'text/plain' });
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
          min_threshold: 0.50,
          top_n: 6,
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to compute job match scores.');
      }

      const data = await res.json();
      const recs = data.top_recommendations || [];
      setJobs(recs);
      setStep(2);
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

  return (
    <div className="app-shell">
      {/* Top Navigation */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={19} />
          </div>
          <div>
            <strong>AI Skill Gap System</strong>
            <span>Employability Enhancement for ITI Graduates</span>
          </div>
        </div>
        <div className="user-chip">
          <span className="avatar">
            <UserRound size={15} />
          </span>{' '}
          ITI Candidate Portal
        </div>
      </header>

      {/* Main Container */}
      <main className="content">
        <div className="page-heading">
          <div>
            <p className="eyebrow">VOCATIONAL CAREER MATCHING</p>
            <h1>
              {step === 1
                ? 'Candidate Resume & Validation'
                : step === 2
                ? 'Recommended ITI Job Roles'
                : 'Job Match Details & Skill Gap Analysis'}
            </h1>
            <p className="subheading">
              {step === 1
                ? 'Upload a resume (PDF/DOCX) to extract technical skills, validate ITI credentials, and guard against non-resume documents.'
                : step === 2
                ? 'Review algorithmic recommendations ranked by our 4-factor scoring model.'
                : 'Inspect detailed score components, missing technical skills, and accredited learning resources.'}
            </p>
          </div>
          <StepIndicator step={step} />
        </div>

        {/* STEP 1: UPLOAD & VALIDATION */}
        {step === 1 && (
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
                      <h4>Document Rejected — Academic Survey / Non-Resume Document</h4>
                      <p>{rejectionReason || validationMessage}</p>
                      <p style={{ marginTop: '6px', fontSize: '13px', opacity: 0.9 }}>
                        The system detected academic publishing sections (e.g., Abstract, References, Literature Review, Citations) and strictly refused to extract vocational skills or recommend jobs for a research paper.
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
        {step === 2 && (
          <section>
            <div className="toolbar">
              <div className="search-box">
                <Search size={17} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search job title, company, or location..."
                />
              </div>
              <button
                type="button"
                className="button button-quiet"
                onClick={() => setStep(1)}
              >
                <ArrowLeft size={16} /> Back to Profile
              </button>
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
                <p className="eyebrow">RANKED VACANCIES</p>
                <h2>Top Recommended ITI Roles for {profile.iti_trade}</h2>
              </div>
              <span>{filteredJobs.length} opportunities matched</span>
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
        {step === 3 && selectedJob && (
          <section>
            <button
              type="button"
              className="back-link"
              onClick={() => setStep(2)}
            >
              <ArrowLeft size={16} /> Back to Recommendations
            </button>

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
                  <h2>Accredited Upskilling Courses</h2>
                </div>
                <p className="review-note">Targeted modules from courses.csv</p>
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
                        <h3>{course.course_name}</h3>
                        <p>
                          Target Skill: <strong>{course.skill}</strong> · Level:{' '}
                          {course.level} · Platform: <strong>{course.provider}</strong> · Duration:{' '}
                          {course.duration}
                        </p>
                      </div>
                      {course.resource_url && course.resource_url.startsWith('http') ? (
                        <a
                          href={course.resource_url}
                          target="_blank"
                          rel="noreferrer"
                          aria-label={`Open ${course.course_name}`}
                        >
                          <ExternalLink size={16} />
                        </a>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#9aa7a4' }}>
                          Standard Curriculum
                        </span>
                      )}
                    </article>
                  ))}
                </div>
              ) : (
                <p className="muted">
                  {selectedJob.missing_skills?.length === 0
                    ? 'Candidate possesses all technical skills for this role; no upskilling modules needed.'
                    : 'No direct learning resources found in the current courses dataset for these missing skills.'}
                </p>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
