export interface CVListItem {
  cv_id: string;
  name: string | null;
  uploaded_at: string;
  emails: string[];
}

export interface CVListResponse {
  cvs: CVListItem[];
  count: number;
}

//----------------------
// ==========================================================
// BASICS (Header Section)
// ==========================================================

export interface Basics {
  name?: string;
  email?: string;        // EmailStr -> string
  phone?: string;
  linkedin?: string;
  github?: string;
  website?: string;
  summary?: string;
  address?: string;
}

// ==========================================================
// EDUCATION
// ==========================================================

export interface Education {
  institution?: string;
  area?: string;         // Major / Field
  studyType?: string;    // BSc, MSc, etc.
  startDate?: string;    // ISO date string recommended
  endDate?: string;
  gpa?: string;
  courses: string[];     // default_factory=list
}

// ==========================================================
// WORK EXPERIENCE
// ==========================================================

export interface Work {
  name?: string;         // Company name
  position?: string;
  startDate?: string;
  endDate?: string;
  summary?: string;
  highlights: string[];
}

// ==========================================================
// SKILLS
// ==========================================================

export interface Skill {
  name?: string;
  level?: string;
  keywords: string[];
}

// ==========================================================
// PROJECTS
// ==========================================================

export interface Project {
  name?: string;
  description?: string;
  highlights: string[];
  url?: string;
}

// ==========================================================
// CERTIFICATES
// ==========================================================

export interface Certificate {
  name?: string;
  issuer?: string;
  date?: string;         // ISO date string recommended
}

// ==========================================================
// MAIN CV MODEL
// ==========================================================

export interface CVParsed {
  cv_id: string;

  basics?: Basics;
  education: Education[];
  work: Work[];
  skills: Skill[];
  projects: Project[];
  certificates: Certificate[];

  raw_text?: string;
  uploaded_at?: string;   // datetime -> ISO string
  user_email?: string;    // EmailStr -> string
}

// ==========================================================
// RESPONSE MODEL
// ==========================================================

export interface CVSubmitResponse {
  success: boolean;
  message: string;
  data: CVParsed;
}
