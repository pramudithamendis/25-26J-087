export interface CVParsed {
  cv_id: string;
  name: string | null;
  emails: string[];
  phones: string[];
  links: {
    linkedin: string[];
    github: string[];
    portfolio: string[];
  };
  sections: {
    education?: string;
    experience?: string;
    skills?: string;
    projects?: string;
    certifications?: string;
    summary?: string;
  };
  raw_text: string;
  uploaded_at: string;
  user_email: string;
}

export interface CVSubmitResponse {
  status: string;
  message: string;
  cv_id: string;
  parsed_data: CVParsed;
}

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
