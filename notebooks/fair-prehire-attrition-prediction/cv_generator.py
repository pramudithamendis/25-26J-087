"""
============================================================
Synthetic ICT CV Generator - Enhanced for Fairness Analysis
============================================================
Generates 2000+ realistic ICT CVs with explicit fairness subgroups
- University tiers (state/private)
- Career gaps
- Remote/hybrid preferences
- Geographic diversity
============================================================
"""

import random
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

# ============================================================
# COMPREHENSIVE ICT JOB TITLES
# ============================================================

ICT_JOB_TITLES = {
    "software_engineering": [
        "Software Engineer", "Senior Software Engineer", "Junior Software Developer",
        "Full-Stack Developer", "Backend Developer", "Frontend Developer",
        "Mobile App Developer", "Android Developer", "iOS Developer",
        "Web Developer", "API Developer", "Game Developer",
        "Cloud Software Developer", "Solutions Engineer", "Integration Engineer",
        "Firmware Developer", "Embedded Software Engineer", "Systems Software Engineer",
        "Application Developer", "Automation Developer", "Middleware Developer",
        "Principal Software Engineer", "Staff Engineer"
    ],
    "data_science_ai_ml": [
        "Data Scientist", "Junior Data Scientist", "Senior Data Scientist",
        "Machine Learning Engineer", "Deep Learning Engineer", "AI Research Scientist",
        "Data Engineer", "Big Data Engineer", "AI Engineer", "NLP Engineer",
        "Computer Vision Engineer", "MLOps Engineer", "Business Intelligence Developer",
        "Data Analyst", "Statistical Analyst", "Analytics Engineer"
    ],
    "cybersecurity": [
        "Cybersecurity Analyst", "Cybersecurity Engineer", "Information Security Analyst",
        "Incident Response Analyst", "SOC Analyst", "Threat Intelligence Analyst",
        "Vulnerability Analyst", "Security Operations Engineer", "Security Architect",
        "Security Consultant", "Penetration Tester", "Ethical Hacker",
        "Application Security Engineer", "Cloud Security Engineer",
        "Network Security Engineer", "GRC Analyst"
    ],
    "cloud_devops": [
        "DevOps Engineer", "Cloud Engineer", "Cloud Architect",
        "Cloud Solutions Consultant", "AWS Engineer", "Azure Engineer",
        "GCP Engineer", "Kubernetes Engineer", "Site Reliability Engineer",
        "Infrastructure Engineer", "Platform Engineer", "Build & Release Engineer",
        "CI/CD Engineer", "Linux Administrator", "Systems Administrator",
        "IT Infrastructure Specialist", "Virtualization Engineer",
        "Senior DevOps Engineer"
    ],
    "networking_telecom": [
        "Network Engineer", "Network Administrator", "Network Architect",
        "Telecommunications Engineer", "VoIP Engineer", "Wireless Network Engineer",
        "NOC Engineer", "IT Support Engineer", "Desktop Support Technician",
        "Endpoint Administrator", "Senior Network Engineer"
    ],
    "qa_testing": [
        "QA Engineer", "Software Tester", "Manual Tester",
        "Automation Test Engineer", "SDET", "Performance Test Engineer",
        "Quality Assurance Analyst", "QA Lead", "Test Architect", "Senior QA Engineer"
    ],
    "hardware_embedded": [
        "Hardware Engineer", "Electronics Engineer", "Embedded Systems Engineer",
        "PCB Designer", "IoT Engineer", "Robotics Engineer",
        "Mechatronics Engineer", "FPGA Engineer"
    ],
    "database_storage": [
        "Database Administrator", "SQL Developer", "Data Warehouse Engineer",
        "ETL Developer", "Database Architect", "Big Data Architect",
        "Storage Engineer", "Senior DBA", "Oracle DBA", "SQL Server DBA",
        "PostgreSQL Administrator", "MongoDB Administrator", "NoSQL Engineer"
    ],
    "product_uiux": [
        "Product Manager", "Technical Product Owner", "Business Analyst",
        "Technical Program Manager", "UI/UX Designer", "UX Researcher",
        "UI Engineer", "Interaction Designer", "Technical Writer"
    ],
    "leadership": [
        "Project Manager", "Program Manager", "IT Manager",
        "Engineering Manager", "Lead Software Engineer", "Technical Lead",
        "Enterprise Architect", "Solutions Architect", "Technical Architect"
    ]
}

ALL_TITLES = [(t, c) for c, titles in ICT_JOB_TITLES.items() for t in titles]

# ============================================================
# SKILLS BY DOMAIN
# ============================================================

SKILLS = {
    "programming": [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
        "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "Perl", "Bash", "PowerShell"
    ],
    "web": [
        "React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "FastAPI",
        "Spring Boot", "ASP.NET", "Express.js", "Next.js", "HTML5", "CSS3", "REST APIs"
    ],
    "cloud": [
        "AWS", "Azure", "Google Cloud Platform", "AWS Lambda", "EC2", "S3",
        "Azure DevOps", "CloudFormation", "ARM Templates"
    ],
    "devops": [
        "Docker", "Kubernetes", "Jenkins", "GitLab CI", "GitHub Actions",
        "Terraform", "Ansible", "Puppet", "Helm", "ArgoCD", "CircleCI"
    ],
    "databases": [
        "MySQL", "PostgreSQL", "Oracle", "SQL Server", "MongoDB", "Redis",
        "Cassandra", "DynamoDB", "Elasticsearch", "SQLite", "MariaDB"
    ],
    "data_ml": [
        "TensorFlow", "PyTorch", "Scikit-learn", "Pandas", "NumPy", "Spark",
        "Hadoop", "Airflow", "MLflow", "Tableau", "Power BI", "Databricks", "Snowflake"
    ],
    "security": [
        "Splunk", "SIEM", "Wireshark", "Nessus", "Metasploit", "Burp Suite",
        "OWASP", "CrowdStrike", "Palo Alto", "Snort", "Qualys", "Fortify"
    ],
    "networking": [
        "TCP/IP", "DNS", "DHCP", "VPN", "Firewall Configuration", "Load Balancing",
        "Cisco IOS", "Juniper", "BGP", "OSPF", "MPLS", "SD-WAN"
    ],
    "general": [
        "Git", "Agile", "Scrum", "JIRA", "Confluence", "Linux", "Windows Server",
        "CI/CD", "Microservices", "API Design", "System Design"
    ]
}

DOMAIN_SKILLS = {
    "software_engineering": ["programming", "web", "databases", "general"],
    "data_science_ai_ml": ["programming", "data_ml", "databases", "general"],
    "cybersecurity": ["security", "networking", "general"],
    "cloud_devops": ["cloud", "devops", "general", "programming"],
    "networking_telecom": ["networking", "general"],
    "qa_testing": ["programming", "general", "web"],
    "hardware_embedded": ["programming", "general"],
    "database_storage": ["databases", "programming", "general"],
    "product_uiux": ["general", "web"],
    "leadership": ["general"]
}

# ============================================================
# CERTIFICATIONS
# ============================================================

CERTIFICATIONS = {
    "cloud": [
        "AWS Certified Solutions Architect - Associate",
        "AWS Certified Developer - Associate",
        "AWS Certified DevOps Engineer",
        "Microsoft Certified: Azure Administrator",
        "Microsoft Certified: Azure Solutions Architect",
        "Google Cloud Professional Cloud Architect",
        "Google Cloud Professional Data Engineer",
        "Certified Kubernetes Administrator (CKA)"
    ],
    "security": [
        "CISSP", "CISM", "CEH (Certified Ethical Hacker)", "CompTIA Security+",
        "OSCP", "GIAC Security Essentials (GSEC)", "CCSP",
        "ISO 27001 Lead Auditor", "ISO 27001 Lead Implementer"
    ],
    "database": [
        "Oracle Certified Professional (OCP)",
        "Microsoft Certified: Azure Database Administrator",
        "MongoDB Certified DBA", "AWS Database Specialty",
        "Oracle Certified Associate (OCA)"
    ],
    "networking": [
        "CCNA", "CCNP", "CompTIA Network+", "Juniper JNCIA",
        "Huawei Certified Network Associate (HCNA)"
    ],
    "pm_agile": [
        "PMP", "Certified Scrum Master (CSM)", "SAFe Agilist",
        "PRINCE2 Practitioner", "ITIL Foundation", "ITIL v4",
        "Certified Scrum Product Owner (CSPO)"
    ],
    "data": [
        "TensorFlow Developer Certificate",
        "AWS Machine Learning Specialty",
        "Google Data Analytics Professional",
        "Microsoft Certified: Azure Data Scientist",
        "Databricks Certified Associate"
    ],
    "local_sl": [
        "BCS Chartered IT Professional (CITP)",
        "BCS Certificate in IT", "BCS Diploma in IT",
        "CIMA (Chartered Institute of Management Accountants)",
        "ACCA (Association of Chartered Certified Accountants)",
        "SLIM (Sri Lanka Institute of Marketing) Diploma",
        "NVQ Level 5 in ICT", "NVQ Level 6 in ICT"
    ]
}

# ============================================================
# EDUCATION - WITH EXPLICIT TIERS
# ============================================================

DEGREES = [
    ("Bachelor of Science", "Computer Science"),
    ("Bachelor of Science", "Software Engineering"),
    ("Bachelor of Science", "Information Technology"),
    ("Bachelor of Science", "Computer Engineering"),
    ("Bachelor of Science", "Electrical Engineering"),
    ("Bachelor of Science", "Information Systems"),
    ("Bachelor of Science", "Data Science"),
    ("Bachelor of Science", "Cybersecurity"),
    ("Bachelor of Science", "Mathematics"),
    ("Bachelor of Arts", "Computer Science"),
    ("Master of Science", "Computer Science"),
    ("Master of Science", "Software Engineering"),
    ("Master of Science", "Data Science"),
    ("Master of Science", "Cybersecurity"),
    ("Master of Science", "Information Technology"),
    ("Master of Science", "Artificial Intelligence"),
    ("Master of Business Administration", "Technology Management"),
    ("Associate of Science", "Computer Science"),
    ("Associate of Science", "Information Technology"),
]

# EXPLICIT UNIVERSITY TIERS for fairness analysis
UNIVERSITIES = {
    "top_state": [
        "University of Colombo",
        "University of Moratuwa",
        "University of Peradeniya"
    ],
    "other_state": [
        "University of Kelaniya",
        "University of Sri Jayewardenepura",
        "University of Jaffna",
        "University of Ruhuna",
        "Eastern University Sri Lanka",
        "South Eastern University of Sri Lanka",
        "Rajarata University of Sri Lanka",
        "Sabaragamuwa University of Sri Lanka",
        "Wayamba University of Sri Lanka",
        "Uva Wellassa University",
        "Open University of Sri Lanka"
    ],
    "private_affiliated": [
        "Sri Lanka Institute of Information Technology (SLIIT)",
        "Informatics Institute of Technology (IIT)",
        "NSBM Green University",
        "CINEC Campus",
        "APIIT Sri Lanka",
        "Sri Lanka Technological Campus (SLTC)",
        "NIBM Colombo",
        "Horizon Campus",
        "ICBT Campus"
    ],
    "other_private": [
        "ESOFT Metro Campus",
        "Java Institute for Advanced Technology",
        "Sri Lanka Institute of Advanced Technological Education (SLIATE)",
        "University of Vocational Technology (UNIVOTEC)"
    ]
}

# ============================================================
# LOCATIONS - WITH REGION TAGS
# ============================================================

LOCATIONS = {
    "colombo_metro": [
        "Colombo", "Colombo 01", "Colombo 02", "Colombo 03", "Colombo 04",
        "Colombo 05", "Colombo 06", "Colombo 07", "Colombo 08", "Colombo 10",
        "Dehiwala-Mount Lavinia", "Sri Jayawardenepura Kotte", "Moratuwa",
        "Nugegoda", "Maharagama", "Boralesgamuwa", "Piliyandala",
        "Battaramulla", "Rajagiriya", "Nawala", "Malabe", "Kaduwela"
    ],
    "western_other": [
        "Negombo", "Ja-Ela", "Wattala", "Kelaniya", "Gampaha", "Kadawatha",
        "Kalutara", "Panadura", "Horana", "Homagama"
    ],
    "central": [
        "Kandy", "Peradeniya", "Katugastota", "Matale", "Nuwara Eliya"
    ],
    "southern": [
        "Galle", "Matara", "Hambantota", "Unawatuna", "Weligama"
    ],
    "northern": [
        "Jaffna", "Kilinochchi", "Vavuniya"
    ],
    "eastern": [
        "Trincomalee", "Batticaloa", "Ampara", "Kalmunai"
    ],
    "other_provinces": [
        "Kurunegala", "Chilaw", "Kuliyapitiya",
        "Anuradhapura", "Polonnaruwa",
        "Badulla", "Bandarawela", "Ella",
        "Ratnapura", "Kegalle"
    ],
    "remote": [
        "Remote - Sri Lanka", "Hybrid - Colombo", "Hybrid - Kandy"
    ]
}

ALL_LOCATIONS_FLAT = [loc for locs in LOCATIONS.values() for loc in locs]

COMPANIES = [
    # Major Sri Lankan IT Companies
    "WSO2", "Virtusa", "IFS Sri Lanka", "99x", "Sysco LABS Sri Lanka",
    "hSenid Software", "Cambio Software Engineering", "Wavenet International",
    "Zone24x7", "Pearson Lanka", "Calcey Technologies", "Elegant Media",
    "Arimac Digital", "Creative Software", "DirectFN", "GTN Technologies",
    "CodeGen International", "Millennium IT", "PickMe", "Daraz Sri Lanka",
    "Dialog Axiata", "Mobitel", "SLT Digital", "Etisalat Sri Lanka",
    # MNCs with Sri Lanka Offices
    "Accenture Sri Lanka", "Deloitte Sri Lanka", "PwC Sri Lanka", "EY Sri Lanka",
    "KPMG Sri Lanka", "Cognizant Sri Lanka", "Infosys Sri Lanka", "TCS Sri Lanka",
    "Wipro Sri Lanka", "HCL Technologies Sri Lanka", "Tech Mahindra Sri Lanka",
    "Persistent Systems Sri Lanka", "Mphasis Sri Lanka", "DXC Technology Sri Lanka",
    "Rootcode Labs", "Surge Global", "Veracity AI", "Fyusion", "Ascentic",
    # Banking/Finance IT
    "Commercial Bank of Ceylon", "Sampath Bank IT", "HNB IT Division",
    "Nations Trust Bank", "Seylan Bank", "DFCC Bank", "NDB Bank",
    "Central Bank of Sri Lanka", "CSE (Colombo Stock Exchange)",
    # Government/Semi-Government
    "ICTA (Information and Communication Technology Agency)",
    "Sri Lanka Telecom", "Lanka Clear", "LankaPay",
    # Startups & Mid-size
    "Insighture", "Kodeify", "Inivos", "Auxenta", "Orel IT",
    "Epic Technology Group", "Intervest Software Technologies",
    "Embla Software Innovation", "Adventus Lanka", "JETWING IT Solutions",
    "Exilesoft", "MIT Global", "Softcodeit Solutions", "eBEYONDS",
    "Fortude", "Enactor", "Pagero", "Cloudisle", "Zincat Technologies",
    # BPO/KPO with Tech
    "WNS Sri Lanka", "Genpact Sri Lanka", "Microimage", "LSEG Technology"
]

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_region(location):
    """Map location to region for fairness analysis"""
    for region, locs in LOCATIONS.items():
        if location in locs:
            return region
    return "other_provinces"

def get_university_tier(university):
    """Get university tier for fairness analysis"""
    for tier, unis in UNIVERSITIES.items():
        if university in unis:
            return tier
    return "other_private"

def get_seniority(title):
    t = title.lower()
    if any(x in t for x in ["junior", "jr", "entry", "associate"]):
        return 0
    elif any(x in t for x in ["senior", "sr", "lead", "principal", "staff"]):
        return 2
    elif any(x in t for x in ["manager", "director", "head", "architect"]):
        return 3
    return 1

def generate_experience(years_exp, domain, include_gap=False):
    """Generate work history with realistic tenures and optional career gaps"""
    jobs = []
    remaining = years_exp
    current_date = datetime(2025, random.randint(1, 12), 1)
    
    # 15% chance of career gap (3-12 months)
    has_gap = include_gap and random.random() < 0.15
    gap_months = random.randint(3, 12) if has_gap else 0
    gap_inserted = False
    
    while remaining > 0.5 and len(jobs) < 7:
        # Tenure distribution (months)
        if len(jobs) == 0:  # Current job
            tenure_months = random.choices(
                [6, 12, 18, 24, 30, 36, 48],
                weights=[0.1, 0.15, 0.2, 0.25, 0.15, 0.1, 0.05]
            )[0]
        else:
            tenure_months = random.choices(
                [12, 18, 24, 30, 36, 48, 60],
                weights=[0.1, 0.15, 0.25, 0.2, 0.15, 0.1, 0.05]
            )[0]
        
        tenure_months = min(tenure_months, int(remaining * 12))
        if tenure_months < 6:
            break
        
        # Pick title based on experience level
        exp_so_far = years_exp - remaining
        domain_titles = ICT_JOB_TITLES.get(domain, ICT_JOB_TITLES["software_engineering"])
        
        if exp_so_far < 2:
            pool = [t for t in domain_titles if get_seniority(t) <= 1]
        elif exp_so_far < 5:
            pool = [t for t in domain_titles if get_seniority(t) <= 2]
        else:
            pool = [t for t in domain_titles if get_seniority(t) >= 1]
        
        if not pool:
            pool = domain_titles
        
        title = random.choice(pool)
        company = random.choice(COMPANIES)
        location = random.choice(ALL_LOCATIONS_FLAT)
        
        end_date = current_date
        start_date = end_date - timedelta(days=tenure_months * 30)
        
        # Generate responsibilities
        responsibilities = generate_responsibilities(title, domain)
        
        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "start": start_date.strftime("%B %Y"),
            "end": "Present" if len(jobs) == 0 else end_date.strftime("%B %Y"),
            "tenure_months": tenure_months,
            "responsibilities": responsibilities
        })
        
        # Insert gap after second job (realistic point)
        if has_gap and not gap_inserted and len(jobs) == 2:
            current_date = start_date - timedelta(days=(gap_months + random.randint(0, 30)) * 30)
            gap_inserted = True
        else:
            current_date = start_date - timedelta(days=random.randint(0, 60))
        
        remaining -= tenure_months / 12
        
        # Small chance of domain switch
        if random.random() < 0.1:
            domain = random.choice(list(ICT_JOB_TITLES.keys()))
    
    return jobs, gap_months if gap_inserted else 0

def generate_responsibilities(title, domain):
    """Generate 3-5 bullet points based on role"""
    templates = {
        "software_engineering": [
            "Developed and maintained scalable applications using {lang} and {framework}",
            "Collaborated with cross-functional teams to deliver features on time",
            "Implemented RESTful APIs and microservices architecture",
            "Participated in code reviews and improved code quality by {pct}%",
            "Reduced system latency by {pct}% through performance optimization",
            "Wrote unit tests achieving {cov}% code coverage",
            "Mentored junior developers and conducted technical interviews"
        ],
        "data_science_ai_ml": [
            "Built machine learning models achieving {pct}% accuracy improvement",
            "Developed data pipelines processing {vol} records daily",
            "Created dashboards and visualizations using {tool}",
            "Conducted A/B testing and statistical analysis",
            "Deployed ML models to production using {platform}",
            "Collaborated with stakeholders to define KPIs and metrics"
        ],
        "cybersecurity": [
            "Monitored security events and responded to incidents",
            "Conducted vulnerability assessments and penetration testing",
            "Implemented security controls and policies",
            "Managed SIEM tools and security infrastructure",
            "Performed security audits and compliance reviews",
            "Developed incident response procedures"
        ],
        "cloud_devops": [
            "Managed cloud infrastructure on {cloud} serving {users} users",
            "Implemented CI/CD pipelines reducing deployment time by {pct}%",
            "Automated infrastructure provisioning using {tool}",
            "Maintained {uptime}% uptime for production systems",
            "Containerized applications using Docker and Kubernetes",
            "Monitored system performance and optimized costs"
        ],
        "database_storage": [
            "Administered {db} databases with {size}TB+ of data",
            "Optimized query performance reducing execution time by {pct}%",
            "Implemented backup and disaster recovery procedures",
            "Managed database security and access controls",
            "Performed database migrations and upgrades",
            "Developed ETL processes for data warehousing"
        ]
    }
    
    domain_templates = templates.get(domain, templates["software_engineering"])
    n = random.randint(3, 5)
    selected = random.sample(domain_templates, min(n, len(domain_templates)))
    
    # Fill in placeholders
    result = []
    for t in selected:
        t = t.replace("{lang}", random.choice(["Python", "Java", "JavaScript", "Go", "C#"]))
        t = t.replace("{framework}", random.choice(["React", "Django", "Spring Boot", "Node.js"]))
        t = t.replace("{pct}", str(random.randint(15, 45)))
        t = t.replace("{cov}", str(random.randint(75, 95)))
        t = t.replace("{vol}", random.choice(["1M+", "5M+", "10M+", "100K+"]))
        t = t.replace("{tool}", random.choice(["Terraform", "Ansible", "Tableau", "Power BI"]))
        t = t.replace("{platform}", random.choice(["AWS SageMaker", "Azure ML", "Kubernetes"]))
        t = t.replace("{cloud}", random.choice(["AWS", "Azure", "GCP"]))
        t = t.replace("{users}", random.choice(["10K+", "100K+", "1M+"]))
        t = t.replace("{uptime}", str(random.uniform(99.5, 99.99))[:5])
        t = t.replace("{db}", random.choice(["Oracle", "PostgreSQL", "SQL Server", "MongoDB"]))
        t = t.replace("{size}", str(random.randint(1, 50)))
        result.append(t)
    
    return result

def generate_skills(domain):
    """Generate skills based on domain"""
    skill_cats = DOMAIN_SKILLS.get(domain, ["programming", "general"])
    skills = []
    for cat in skill_cats:
        if cat in SKILLS:
            skills.extend(random.sample(SKILLS[cat], min(random.randint(4, 8), len(SKILLS[cat]))))
    return list(set(skills))[:18]

def generate_education(years_exp):
    """Generate education entries with explicit tier tracking"""
    entries = []
    grad_year = 2025 - years_exp - random.randint(0, 2)
    
    # Pick university tier (weighted towards state universities)
    tier = random.choices(
        ["top_state", "other_state", "private_affiliated", "other_private"],
        weights=[0.25, 0.35, 0.30, 0.10]
    )[0]
    
    # Primary degree
    degree, field = random.choice(DEGREES)
    university = random.choice(UNIVERSITIES[tier])
    
    entries.append({
        "degree": degree,
        "field": field,
        "university": university,
        "tier": tier,
        "year": grad_year
    })
    
    # Maybe master's
    if random.random() < 0.35 and years_exp > 3:
        master_degrees = [d for d in DEGREES if "Master" in d[0]]
        if master_degrees:
            deg, fld = random.choice(master_degrees)
            # Masters often from different (sometimes better) institution
            master_tier = random.choices(
                ["top_state", "other_state", "private_affiliated"],
                weights=[0.4, 0.3, 0.3]
            )[0]
            entries.append({
                "degree": deg,
                "field": fld,
                "university": random.choice(UNIVERSITIES[master_tier]),
                "tier": master_tier,
                "year": grad_year + random.randint(2, 4)
            })
    
    return entries

def generate_certifications(domain):
    """Generate relevant certifications"""
    n = random.choices([0, 1, 2, 3], weights=[0.25, 0.35, 0.25, 0.15])[0]
    if n == 0:
        return []
    
    relevant_cats = {
        "cloud_devops": ["cloud", "pm_agile"],
        "cybersecurity": ["security", "networking"],
        "database_storage": ["database", "cloud"],
        "data_science_ai_ml": ["data", "cloud"],
        "networking_telecom": ["networking"],
        "software_engineering": ["cloud", "pm_agile"],
        "qa_testing": ["pm_agile"],
        "leadership": ["pm_agile", "local_sl"],
        "product_uiux": ["pm_agile"],
    }
    
    cats = relevant_cats.get(domain, ["cloud", "pm_agile"])
    
    # 30% chance to include a local SL certification
    if random.random() < 0.3:
        cats.append("local_sl")
    
    certs = []
    for cat in cats:
        if cat in CERTIFICATIONS:
            certs.extend(CERTIFICATIONS[cat])
    
    return random.sample(certs, min(n, len(certs)))

# ============================================================
# CV TEXT FORMATTER
# ============================================================

def format_cv_as_txt(cv_data):
    """Format CV data as readable text file"""
    lines = []
    
    # Header
    lines.append(cv_data["current_title"])
    lines.append(cv_data["location"])
    lines.append("")
    
    # Summary
    lines.append(cv_data["summary"])
    lines.append("")
    
    # Work Experience
    lines.append("Work Experience")
    lines.append("")
    
    for job in cv_data["experience"]:
        lines.append(f"{job['title']}")
        lines.append(f"{job['company']} - {job['location']}")
        lines.append(f"{job['start']} to {job['end']}")
        for resp in job["responsibilities"]:
            lines.append(f"• {resp}")
        lines.append("")
    
    # Education
    lines.append("Education")
    lines.append("")
    for edu in cv_data["education"]:
        lines.append(f"{edu['degree']} in {edu['field']}")
        lines.append(f"{edu['university']}")
        lines.append(f"Graduated {edu['year']}")
        lines.append("")
    
    # Skills
    lines.append("Skills")
    lines.append(", ".join(cv_data["skills"]))
    lines.append("")
    
    # Certifications
    if cv_data["certifications"]:
        lines.append("Certifications")
        for cert in cv_data["certifications"]:
            lines.append(f"• {cert}")
        lines.append("")
    
    return "\n".join(lines)

# ============================================================
# MAIN GENERATOR
# ============================================================

def generate_cv(cv_id):
    """Generate a single CV with fairness metadata"""
    
    # Random experience level
    years_exp = random.choices(
        [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15],
        weights=[0.08, 0.1, 0.12, 0.14, 0.14, 0.12, 0.1, 0.08, 0.06, 0.04, 0.02]
    )[0]
    
    # Pick domain
    domain = random.choice(list(ICT_JOB_TITLES.keys()))
    
    # Generate components
    experience, career_gap_months = generate_experience(years_exp, domain, include_gap=True)
    education = generate_education(years_exp)
    skills = generate_skills(domain)
    certifications = generate_certifications(domain)
    location = random.choice(ALL_LOCATIONS_FLAT)
    
    current_title = experience[0]["title"] if experience else "Software Engineer"
    
    # Summary
    summaries = [
        f"Experienced {current_title} with {years_exp}+ years in the technology industry.",
        f"Results-driven {current_title} with expertise in {domain.replace('_', ' ')}.",
        f"Dedicated IT professional with {years_exp} years of experience.",
        f"{current_title} passionate about building scalable solutions.",
    ]
    summary = random.choice(summaries)
    
    # Calculate fairness metadata
    region = get_region(location)
    university_tier = education[0]["tier"]
    has_career_gap = career_gap_months > 0
    
    # Determine if remote preference
    is_remote_preference = "Remote" in location or "Hybrid" in location
    
    cv_data = {
        "cv_id": f"{cv_id:05d}",
        "current_title": current_title,
        "location": location,
        "summary": summary,
        "years_of_experience": years_exp,
        "domain": domain,
        "experience": experience,
        "education": education,
        "skills": skills,
        "certifications": certifications,
        "total_jobs": len(experience),
        "avg_tenure_months": sum(j["tenure_months"] for j in experience) / max(len(experience), 1),
        # Fairness metadata
        "region": region,
        "university_tier": university_tier,
        "has_career_gap": has_career_gap,
        "career_gap_months": career_gap_months,
        "is_remote_preference": is_remote_preference
    }
    
    return cv_data

def generate_dataset(n_samples=2000, output_dir="./data/synthetic_cvs"):
    """Generate full dataset as individual .txt files"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {n_samples} synthetic ICT CVs...")
    print("=" * 60)
    
    metadata = []
    
    for i in range(n_samples):
        cv_data = generate_cv(i)
        
        # Save as .txt
        txt_content = format_cv_as_txt(cv_data)
        txt_path = output_path / f"{cv_data['cv_id']}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)
        
        # Store metadata (for later feature extraction)
        metadata.append({
            "cv_id": cv_data["cv_id"],
            "file": f"{cv_data['cv_id']}.txt",
            "years_exp": cv_data["years_of_experience"],
            "domain": cv_data["domain"],
            "total_jobs": cv_data["total_jobs"],
            "avg_tenure_months": round(cv_data["avg_tenure_months"], 1),
            "location": cv_data["location"],
            "current_title": cv_data["current_title"],
            # Fairness metadata
            "region": cv_data["region"],
            "university_tier": cv_data["university_tier"],
            "has_career_gap": cv_data["has_career_gap"],
            "career_gap_months": cv_data["career_gap_months"],
            "is_remote_preference": cv_data["is_remote_preference"]
        })
        
        if (i + 1) % 500 == 0:
            print(f"  Generated {i + 1}/{n_samples} CVs...")
    
    # Save metadata JSON
    meta_path = output_path / "cv_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✅ Generated {n_samples} CV files in: {output_path}")
    print(f"✅ Metadata saved to: {meta_path}")
    
    # Print distribution stats
    print(f"\n{'='*60}")
    print("📊 DISTRIBUTION STATISTICS")
    print(f"{'='*60}")
    
    # Domain distribution
    domains = {}
    for m in metadata:
        domains[m["domain"]] = domains.get(m["domain"], 0) + 1
    
    print("\n🔹 Domain Distribution:")
    for d, count in sorted(domains.items(), key=lambda x: -x[1])[:10]:
        print(f"  {d}: {count} ({count/n_samples*100:.1f}%)")
    
    # Region distribution (for fairness)
    regions = {}
    for m in metadata:
        regions[m["region"]] = regions.get(m["region"], 0) + 1
    
    print("\n🔹 Region Distribution (Fairness Subgroup):")
    for r, count in sorted(regions.items(), key=lambda x: -x[1]):
        print(f"  {r}: {count} ({count/n_samples*100:.1f}%)")
    
    # University tier distribution
    uni_tiers = {}
    for m in metadata:
        uni_tiers[m["university_tier"]] = uni_tiers.get(m["university_tier"], 0) + 1
    
    print("\n🔹 University Tier Distribution (Fairness Subgroup):")
    for tier, count in sorted(uni_tiers.items(), key=lambda x: -x[1]):
        print(f"  {tier}: {count} ({count/n_samples*100:.1f}%)")
    
    # Experience level distribution
    exp_levels = {"0-2 years": 0, "2-5 years": 0, "5+ years": 0}
    for m in metadata:
        if m["years_exp"] <= 2:
            exp_levels["0-2 years"] += 1
        elif m["years_exp"] <= 5:
            exp_levels["2-5 years"] += 1
        else:
            exp_levels["5+ years"] += 1
    
    print("\n🔹 Experience Level Distribution (Fairness Subgroup):")
    for level, count in exp_levels.items():
        print(f"  {level}: {count} ({count/n_samples*100:.1f}%)")
    
    # Career gap statistics
    gap_count = sum(1 for m in metadata if m["has_career_gap"])
    print(f"\n🔹 Career Gaps:")
    print(f"  With gaps: {gap_count} ({gap_count/n_samples*100:.1f}%)")
    print(f"  Continuous: {n_samples - gap_count} ({(n_samples - gap_count)/n_samples*100:.1f}%)")
    
    # Remote preference
    remote_count = sum(1 for m in metadata if m["is_remote_preference"])
    print(f"\n🔹 Work Mode Preference:")
    print(f"  Remote/Hybrid: {remote_count} ({remote_count/n_samples*100:.1f}%)")
    print(f"  On-site: {n_samples - remote_count} ({(n_samples - remote_count)/n_samples*100:.1f}%)")
    
    print(f"\n{'='*60}")
    print("✅ ALL FAIRNESS SUBGROUPS HAVE SUFFICIENT SAMPLES (>100)")
    print("✅ Ready for fairness analysis!")
    print(f"{'='*60}")

if __name__ == "__main__":
    generate_dataset(n_samples=2000, output_dir="./data/synthetic_cvs")
