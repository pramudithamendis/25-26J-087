"""
============================================================
ICT Job Description Generator - Sri Lankan Context
ENHANCED VERSION with realistic, level-appropriate requirements
============================================================
"""

import random
import os
from pathlib import Path

random.seed(42)

# ============================================================
# Configuration
# ============================================================

SL_CITIES = {
    # Western Province - Higher concentration
    "Colombo": 25, "Dehiwala": 5, "Moratuwa": 5, "Maharagama": 4,
    "Kotte": 4, "Nugegoda": 3, "Gampaha": 4, "Negombo": 4,
    "Kalutara": 3, "Panadura": 2, "Homagama": 2, "Kaduwela": 2,
    "Kelaniya": 2, "Wattala": 2,
    
    # Other Provinces
    "Kandy": 8, "Matale": 2, "Peradeniya": 2,
    "Galle": 4, "Matara": 3, "Hikkaduwa": 1,
    "Jaffna": 3, "Vavuniya": 1,
    "Batticaloa": 2, "Trincomalee": 2,
    "Kurunegala": 3, "Puttalam": 1,
    "Anuradhapura": 2, "Badulla": 2,
    "Ratnapura": 2, "Kegalle": 1
}

# Job Templates with realistic requirements by level
JOB_TEMPLATES = {
    "Software Engineer": {
        "weight": 8,
        "levels": ["Intern", "Junior", "Associate", "Senior", "Lead"],
        "tech_stacks": [
            ["Java", "Spring Boot", "MySQL", "REST APIs", "Docker", "Git"],
            ["Python", "Django", "PostgreSQL", "Redis", "AWS", "CI/CD"],
            [".NET Core", "C#", "SQL Server", "Azure", "Entity Framework", "Microservices"],
            ["Node.js", "Express", "MongoDB", "React", "TypeScript", "Kubernetes"],
            ["PHP", "Laravel", "MySQL", "Vue.js", "Redis", "Docker"],
            ["Go", "PostgreSQL", "Docker", "Kubernetes", "gRPC", "Microservices"],
            ["Ruby", "Ruby on Rails", "PostgreSQL", "Sidekiq", "Heroku", "Git"]
        ],
        "experience": {"Intern": "0-1", "Junior": "1-2", "Associate": "2-4", "Senior": "4-7", "Lead": "7+"},
        "salary": {"Intern": "30,000-50,000", "Junior": "80,000-120,000", "Associate": "120,000-180,000", 
                   "Senior": "180,000-280,000", "Lead": "280,000-400,000"}
    },
    
    "Full Stack Developer": {
        "weight": 7,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["React", "Node.js", "MongoDB", "Express", "AWS", "Docker"],
            ["Angular", "Java", "Spring Boot", "PostgreSQL", "Docker", "Kubernetes"],
            ["Vue.js", "Python", "Django", "MySQL", "Redis", "Git"],
            ["Next.js", "TypeScript", "GraphQL", "PostgreSQL", "Vercel", "Prisma"],
            ["React", "NestJS", "TypeScript", "PostgreSQL", "Redis", "Docker"],
            ["Svelte", "FastAPI", "Python", "PostgreSQL", "Docker", "AWS"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "100,000-150,000", "Mid-level": "150,000-220,000", "Senior": "220,000-350,000"}
    },
    
    "Data Scientist": {
        "weight": 6,
        "levels": ["Junior", "Associate", "Senior", "Lead"],
        "tech_stacks": [
            ["Python", "scikit-learn", "pandas", "SQL", "Tableau", "Git"],
            ["Python", "TensorFlow", "PyTorch", "AWS", "MLflow", "Spark"],
            ["R", "Python", "Power BI", "SQL", "Azure ML", "Statistics"],
            ["Python", "Spark", "Databricks", "AWS", "Airflow", "MLflow"],
            ["Python", "Keras", "TensorFlow", "Docker", "Kubernetes", "MLflow"],
            ["Python", "XGBoost", "LightGBM", "SQL", "AWS", "scikit-learn"]
        ],
        "experience": {"Junior": "1-2", "Associate": "2-4", "Senior": "4-7", "Lead": "7+"},
        "salary": {"Junior": "100,000-150,000", "Associate": "150,000-220,000", 
                   "Senior": "220,000-320,000", "Lead": "320,000-450,000"}
    },
    
    "Data Engineer": {
        "weight": 6,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Python", "PySpark", "AWS", "Redshift", "Airflow", "SQL"],
            ["Python", "Databricks", "Azure", "SQL", "Data Factory", "Synapse"],
            ["Scala", "Spark", "Kafka", "Snowflake", "DBT", "Airflow"],
            ["Python", "ETL", "BigQuery", "GCP", "Dataflow", "Composer"],
            ["Python", "Kafka", "Flink", "AWS", "Lambda", "Glue"],
            ["SQL", "Python", "Airflow", "dbt", "Snowflake", "Fivetran"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "100,000-160,000", "Mid-level": "160,000-240,000", "Senior": "240,000-380,000"}
    },
    
    "QA Engineer": {
        "weight": 6,
        "levels": ["Junior", "Mid-level", "Senior", "Lead QA"],
        "tech_stacks": [
            ["Selenium", "Java", "TestNG", "Jira", "API Testing", "Git"],
            ["Cypress", "JavaScript", "Postman", "Git", "CI/CD", "Docker"],
            ["Playwright", "TypeScript", "Azure DevOps", "K6", "Docker", "Jenkins"],
            ["Manual Testing", "SQL", "Jira", "TestRail", "API Testing", "Postman"],
            ["Python", "Pytest", "Selenium", "REST Assured", "Jenkins", "Git"],
            ["Robot Framework", "Python", "Selenium", "API Testing", "Jenkins", "Git"]
        ],
        "experience": {"Junior": "1-2", "Mid-level": "2-4", "Senior": "4-7", "Lead QA": "7+"},
        "salary": {"Junior": "70,000-110,000", "Mid-level": "110,000-170,000", 
                   "Senior": "170,000-250,000", "Lead QA": "250,000-350,000"}
    },
    
    "DevOps Engineer": {
        "weight": 6,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Docker", "Kubernetes", "AWS", "Terraform", "Jenkins", "Python"],
            ["Azure DevOps", "Docker", "Kubernetes", "Python", "Ansible", "Terraform"],
            ["GitLab CI/CD", "Docker", "AWS", "Prometheus", "Grafana", "Python"],
            ["Docker", "GCP", "Kubernetes", "Terraform", "Python", "Helm"],
            ["Jenkins", "Docker", "AWS", "CloudFormation", "Python", "Bash"],
            ["Kubernetes", "Helm", "AWS", "ArgoCD", "Terraform", "Python"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "100,000-150,000", "Mid-level": "150,000-230,000", "Senior": "230,000-350,000"}
    },
    
    "Frontend Developer": {
        "weight": 6,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["React", "JavaScript", "HTML", "CSS", "Redux", "Git"],
            ["Vue.js", "TypeScript", "Tailwind CSS", "Vuex", "Git", "Webpack"],
            ["Angular", "TypeScript", "RxJS", "NgRx", "Material UI", "Git"],
            ["React", "Next.js", "TypeScript", "Styled Components", "GraphQL", "Git"],
            ["Svelte", "TypeScript", "Tailwind CSS", "Vite", "Git", "REST APIs"],
            ["React", "TypeScript", "Material UI", "Redux Toolkit", "Storybook", "Git"]
        ],
        "experience": {"Junior": "1-2", "Mid-level": "2-5", "Senior": "5+"},
        "salary": {"Junior": "80,000-120,000", "Mid-level": "120,000-190,000", "Senior": "190,000-300,000"}
    },
    
    "Backend Developer": {
        "weight": 6,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Node.js", "Express", "MongoDB", "REST APIs", "AWS", "Docker"],
            ["Java", "Spring Boot", "PostgreSQL", "Microservices", "Docker", "Kafka"],
            ["Python", "FastAPI", "PostgreSQL", "Redis", "Celery", "Docker"],
            [".NET", "C#", "SQL Server", "Entity Framework", "Azure", "RabbitMQ"],
            ["Go", "Gin", "PostgreSQL", "Redis", "Docker", "gRPC"],
            ["Python", "Django", "PostgreSQL", "Celery", "Redis", "Docker"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "90,000-130,000", "Mid-level": "130,000-200,000", "Senior": "200,000-320,000"}
    },
    
    "Mobile Developer": {
        "weight": 5,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Flutter", "Dart", "Firebase", "REST APIs", "Git", "Provider"],
            ["React Native", "JavaScript", "Redux", "Firebase", "AWS", "TypeScript"],
            ["Android", "Kotlin", "Java", "MVVM", "Room Database", "Retrofit"],
            ["iOS", "Swift", "SwiftUI", "Core Data", "Firebase", "Combine"],
            ["Flutter", "Dart", "Bloc", "Firebase", "REST APIs", "SQLite"],
            ["React Native", "TypeScript", "Redux", "GraphQL", "Apollo", "Firebase"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "90,000-140,000", "Mid-level": "140,000-210,000", "Senior": "210,000-330,000"}
    },
    
    "UI/UX Designer": {
        "weight": 4,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Figma", "Adobe XD", "Sketch", "User Research", "Prototyping", "Wireframing"],
            ["Figma", "Adobe Creative Suite", "Wireframing", "User Testing", "Design Systems"],
            ["Figma", "InVision", "Design Systems", "User Research", "HTML", "CSS"],
            ["Adobe XD", "Figma", "Prototyping", "User Testing", "Sketch", "Zeplin"],
            ["Figma", "Miro", "Prototyping", "User Research", "A/B Testing", "Analytics"]
        ],
        "experience": {"Junior": "1-2", "Mid-level": "2-5", "Senior": "5+"},
        "salary": {"Junior": "70,000-100,000", "Mid-level": "100,000-160,000", "Senior": "160,000-250,000"}
    },
    
    "Cloud Engineer": {
        "weight": 5,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["AWS", "EC2", "S3", "Lambda", "CloudFormation", "Python"],
            ["Azure", "VMs", "App Services", "Azure DevOps", "Terraform", "PowerShell"],
            ["GCP", "Compute Engine", "Cloud Storage", "Kubernetes", "Python", "Terraform"],
            ["AWS", "EKS", "RDS", "Terraform", "Python", "Docker"],
            ["Azure", "AKS", "Functions", "Terraform", "Python", "ARM Templates"],
            ["Multi-cloud", "Kubernetes", "Terraform", "Python", "Docker", "Ansible"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "100,000-150,000", "Mid-level": "150,000-240,000", "Senior": "240,000-380,000"}
    },
    
    "Database Administrator": {
        "weight": 4,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["MySQL", "PostgreSQL", "Performance Tuning", "Backup/Recovery", "Replication", "SQL"],
            ["SQL Server", "T-SQL", "SSIS", "Database Design", "Replication", "Performance Tuning"],
            ["Oracle", "PL/SQL", "RAC", "Database Security", "Monitoring", "Backup/Recovery"],
            ["PostgreSQL", "MongoDB", "Database Design", "Performance Tuning", "Backup", "Python"],
            ["MySQL", "Redis", "Performance Tuning", "Replication", "Monitoring", "Python"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "80,000-120,000", "Mid-level": "120,000-180,000", "Senior": "180,000-280,000"}
    },
    
    "Business Analyst": {
        "weight": 4,
        "levels": ["Trainee", "Junior", "Senior"],
        "tech_stacks": [
            ["SQL", "Excel", "Jira", "Agile", "Documentation", "Stakeholder Management"],
            ["Power BI", "SQL", "Tableau", "Business Process Modeling", "Agile", "JIRA"],
            ["SQL", "Python", "Data Analysis", "Stakeholder Management", "Excel", "Tableau"],
            ["SQL", "Power BI", "Excel", "Requirements Gathering", "Agile", "Confluence"],
            ["Tableau", "SQL", "Excel", "Stakeholder Management", "Agile", "User Stories"]
        ],
        "experience": {"Trainee": "0-1", "Junior": "1-3", "Senior": "3+"},
        "salary": {"Trainee": "50,000-70,000", "Junior": "80,000-130,000", "Senior": "130,000-220,000"}
    },
    
    "Machine Learning Engineer": {
        "weight": 4,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Python", "TensorFlow", "PyTorch", "MLOps", "Docker", "Kubernetes"],
            ["Python", "scikit-learn", "MLflow", "AWS SageMaker", "Docker", "CI/CD"],
            ["Python", "PyTorch", "FastAPI", "Docker", "Kubernetes", "MLflow"],
            ["Python", "TensorFlow", "Kubeflow", "GCP", "Docker", "ML Pipelines"],
            ["Python", "XGBoost", "Docker", "AWS", "MLflow", "FastAPI"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "120,000-180,000", "Mid-level": "180,000-280,000", "Senior": "280,000-420,000"}
    },
    
    "Security Engineer": {
        "weight": 3,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Security Tools", "Penetration Testing", "SIEM", "Python", "Linux", "Networking"],
            ["AWS Security", "IAM", "Security Auditing", "Python", "Terraform", "Compliance"],
            ["Application Security", "OWASP", "Burp Suite", "Python", "Security Testing", "Docker"],
            ["Network Security", "Firewalls", "IDS/IPS", "Python", "Linux", "Wireshark"],
            ["Cloud Security", "Azure Security", "Compliance", "Python", "Terraform", "Automation"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "100,000-160,000", "Mid-level": "160,000-250,000", "Senior": "250,000-400,000"}
    },
    
    "Product Manager": {
        "weight": 3,
        "levels": ["Associate", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Product Strategy", "Roadmapping", "Agile", "Jira", "Analytics", "Stakeholder Management"],
            ["User Research", "Product Analytics", "A/B Testing", "SQL", "Agile", "Figma"],
            ["Data Analysis", "SQL", "Product Strategy", "Roadmapping", "Jira", "Confluence"],
            ["Market Research", "Product Analytics", "Agile", "User Stories", "Prioritization", "SQL"],
            ["Product Vision", "Strategy", "OKRs", "Agile", "Analytics", "Stakeholder Management"]
        ],
        "experience": {"Associate": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Associate": "120,000-180,000", "Mid-level": "180,000-280,000", "Senior": "280,000-450,000"}
    },
    
    "System Administrator": {
        "weight": 4,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Linux", "Windows Server", "Bash", "PowerShell", "Networking", "VMware"],
            ["Linux", "Docker", "Ansible", "Monitoring", "Bash", "Python"],
            ["Windows Server", "Active Directory", "PowerShell", "Hyper-V", "Networking", "Azure"],
            ["Linux", "Kubernetes", "Docker", "Monitoring", "Bash", "Ansible"],
            ["VMware", "Linux", "Windows", "Networking", "Backup Solutions", "PowerShell"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "70,000-110,000", "Mid-level": "110,000-170,000", "Senior": "170,000-260,000"}
    },
    
    "Network Engineer": {
        "weight": 3,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Cisco", "Routing", "Switching", "Firewalls", "VPN", "Network Security"],
            ["Network Design", "TCP/IP", "BGP", "OSPF", "Firewalls", "Cisco"],
            ["SD-WAN", "Network Automation", "Python", "Cisco", "Juniper", "Security"],
            ["Wireless Networks", "Cisco", "Network Monitoring", "Troubleshooting", "VPN", "Firewalls"],
            ["Network Architecture", "Cisco", "Juniper", "Security", "Load Balancing", "Monitoring"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "80,000-120,000", "Mid-level": "120,000-190,000", "Senior": "190,000-300,000"}
    },
    
    "Technical Lead": {
        "weight": 3,
        "levels": ["Senior"],
        "tech_stacks": [
            ["Java", "Spring", "Microservices", "AWS", "Team Leadership", "Architecture"],
            [".NET", "Azure", "Architecture", "CI/CD", "Mentoring", "Code Review"],
            ["Python", "Django", "System Design", "PostgreSQL", "Agile", "Team Leadership"],
            ["Node.js", "React", "Architecture", "AWS", "Team Leadership", "Code Review"],
            ["Full Stack", "Architecture", "Cloud", "Mentoring", "Agile", "Technical Strategy"]
        ],
        "experience": {"Senior": "6+"},
        "salary": {"Senior": "300,000-500,000"}
    },
    
    "Solutions Architect": {
        "weight": 2,
        "levels": ["Senior"],
        "tech_stacks": [
            ["AWS", "Microservices", "System Design", "Docker", "Kubernetes", "Architecture"],
            ["Azure", "Enterprise Architecture", "Integration Patterns", "Security", "Cloud Strategy"],
            ["Cloud Architecture", "API Design", "Scalability", "DevOps", "System Design"],
            ["Multi-cloud", "Architecture Patterns", "Microservices", "Security", "Integration"],
            ["AWS", "Serverless", "Microservices", "Architecture", "Cost Optimization", "Security"]
        ],
        "experience": {"Senior": "7+"},
        "salary": {"Senior": "350,000-600,000"}
    },
    
    "Scrum Master": {
        "weight": 3,
        "levels": ["Junior", "Senior"],
        "tech_stacks": [
            ["Agile", "Scrum", "Jira", "Facilitation", "Coaching", "Conflict Resolution"],
            ["Agile Methodologies", "Scrum", "Kanban", "Jira", "Team Coaching", "Azure DevOps"],
            ["Scrum", "SAFe", "Jira", "Confluence", "Agile Coaching", "Metrics"],
            ["Agile", "Scrum", "Sprint Planning", "Retrospectives", "Jira", "Stakeholder Management"],
            ["Scrum", "Agile Transformation", "Team Coaching", "Jira", "Metrics", "Continuous Improvement"]
        ],
        "experience": {"Junior": "1-3", "Senior": "3+"},
        "salary": {"Junior": "80,000-130,000", "Senior": "130,000-220,000"}
    },
    
    "Data Analyst": {
        "weight": 5,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["SQL", "Excel", "Power BI", "Python", "Data Visualization", "Statistics"],
            ["SQL", "Tableau", "Python", "Excel", "Data Analysis", "Business Intelligence"],
            ["SQL", "Python", "Pandas", "Power BI", "Statistical Analysis", "Excel"],
            ["SQL", "Looker", "Python", "Data Visualization", "A/B Testing", "Google Analytics"],
            ["SQL", "Excel", "Tableau", "Data Modeling", "ETL", "Business Analysis"]
        ],
        "experience": {"Junior": "1-2", "Mid-level": "2-4", "Senior": "4+"},
        "salary": {"Junior": "70,000-110,000", "Mid-level": "110,000-170,000", "Senior": "170,000-260,000"}
    },
    
    "Site Reliability Engineer": {
        "weight": 3,
        "levels": ["Mid-level", "Senior"],
        "tech_stacks": [
            ["Kubernetes", "Docker", "Monitoring", "Python", "Linux", "CI/CD"],
            ["AWS", "Terraform", "Monitoring", "Python", "Incident Response", "Automation"],
            ["GCP", "Kubernetes", "Monitoring", "Go", "Linux", "SLI/SLO"],
            ["Azure", "Kubernetes", "Prometheus", "Grafana", "Python", "Automation"],
            ["Cloud Platform", "Monitoring", "Automation", "Python", "Linux", "Performance Tuning"]
        ],
        "experience": {"Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Mid-level": "180,000-280,000", "Senior": "280,000-420,000"}
    },
    
    "Game Developer": {
        "weight": 2,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Unity", "C#", "Game Design", "3D Modeling", "Physics", "Git"],
            ["Unreal Engine", "C++", "Blueprints", "3D Assets", "Game Mechanics", "Git"],
            ["Unity", "C#", "Mobile Games", "Monetization", "Analytics", "Git"],
            ["Godot", "GDScript", "2D Games", "Animation", "Game Design", "Git"],
            ["Unity", "C#", "VR/AR", "3D Graphics", "Optimization", "Git"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "80,000-130,000", "Mid-level": "130,000-200,000", "Senior": "200,000-320,000"}
    },
    
    "Blockchain Developer": {
        "weight": 2,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Solidity", "Ethereum", "Web3", "Smart Contracts", "JavaScript", "Truffle"],
            ["Solidity", "Ethereum", "React", "Web3.js", "Smart Contracts", "Hardhat"],
            ["Blockchain", "Smart Contracts", "Solidity", "Node.js", "Cryptography", "Git"],
            ["Hyperledger", "Blockchain", "Go", "Smart Contracts", "Docker", "Kubernetes"],
            ["Solidity", "DeFi", "Web3", "Smart Contracts", "React", "Testing"]
        ],
        "experience": {"Junior": "1-3", "Mid-level": "3-5", "Senior": "5+"},
        "salary": {"Junior": "100,000-160,000", "Mid-level": "160,000-260,000", "Senior": "260,000-400,000"}
    },
    
    "Technical Writer": {
        "weight": 2,
        "levels": ["Junior", "Mid-level", "Senior"],
        "tech_stacks": [
            ["Technical Writing", "Documentation", "Markdown", "Git", "API Documentation", "Confluence"],
            ["Technical Writing", "Docs as Code", "Markdown", "Git", "REST APIs", "Postman"],
            ["Documentation", "Markdown", "Git", "Content Management", "User Guides", "API Docs"],
            ["Technical Writing", "Documentation Tools", "Markdown", "Git", "Style Guides", "Editing"],
            ["Technical Communication", "Documentation", "Markdown", "Git", "Video Tutorials", "Confluence"]
        ],
        "experience": {"Junior": "1-2", "Mid-level": "2-4", "Senior": "4+"},
        "salary": {"Junior": "60,000-90,000", "Mid-level": "90,000-140,000", "Senior": "140,000-220,000"}
    }
}

COMPANY_TYPES = [
    "Tech Startup", "BPO", "Product Company", "Software Consultancy",
    "International IT Office", "Conglomerate IT Division", "FinTech Company",
    "E-commerce Platform", "Digital Agency", "RegTech Company", "EdTech Company",
    "HealthTech Company", "Gaming Studio", "Digital Bank", "Insurance Tech"
]

# ============================================================
# REALISTIC REQUIREMENT GENERATORS
# ============================================================

def get_education_requirements(job_title, level):
    """Generate realistic education requirements based on role and level"""
    
    # Intern/Trainee requirements
    if level in ["Intern", "Trainee"]:
        return {
            "primary": "Currently pursuing or recently completed Bachelor's degree in Computer Science, Software Engineering, IT, or related field",
            "alternatives": "Final year undergraduate students are encouraged to apply",
            "preferred": None
        }
    
    # Technical roles
    technical_roles = ["Software Engineer", "Full Stack Developer", "Frontend Developer", 
                       "Backend Developer", "Mobile Developer", "DevOps Engineer", 
                       "QA Engineer", "Database Administrator", "System Administrator",
                       "Network Engineer", "Game Developer", "Blockchain Developer"]
    
    # Data/Analytics roles
    data_roles = ["Data Scientist", "Data Engineer", "Data Analyst", "Machine Learning Engineer"]
    
    # Specialized roles
    design_roles = ["UI/UX Designer"]
    management_roles = ["Product Manager", "Technical Lead", "Solutions Architect", "Scrum Master"]
    security_roles = ["Security Engineer"]
    
    if job_title in technical_roles:
        if level in ["Junior"]:
            return {
                "primary": "Bachelor's degree in Computer Science, Software Engineering, IT, or related field",
                "alternatives": "Equivalent diploma with demonstrable practical experience or relevant certifications",
                "preferred": "Completed coding bootcamp or relevant online certifications (Coursera, Udemy, etc.)"
            }
        elif level in ["Senior", "Lead", "Lead QA"]:
            return {
                "primary": "Bachelor's or Master's degree in Computer Science, Software Engineering, or related field",
                "alternatives": None,
                "preferred": "Master's degree, relevant professional certifications (AWS, Azure, Oracle, Google Cloud, etc.)"
            }
        else:  # Mid-level, Associate
            return {
                "primary": "Bachelor's degree in Computer Science, Software Engineering, IT, or related field",
                "alternatives": None,
                "preferred": "Relevant technical certifications or continued professional development"
            }
    
    elif job_title in data_roles:
        if level in ["Junior"]:
            return {
                "primary": "Bachelor's degree in Computer Science, Statistics, Mathematics, Data Science, or related quantitative field",
                "alternatives": "Engineering degree with strong analytical background",
                "preferred": "Completed specialized courses in Machine Learning, Data Science (Coursera, edX, DataCamp)"
            }
        elif level in ["Senior", "Lead"]:
            return {
                "primary": "Bachelor's or Master's degree in Computer Science, Statistics, Mathematics, Data Science, or related field",
                "alternatives": None,
                "preferred": "Master's or PhD in relevant quantitative field, certifications like AWS ML Specialty, TensorFlow Developer"
            }
        else:  # Associate, Mid-level
            return {
                "primary": "Bachelor's degree in Computer Science, Statistics, Mathematics, Data Science, or related field",
                "alternatives": None,
                "preferred": "Relevant certifications in Data Analytics, Machine Learning, or Cloud platforms"
            }
    
    elif job_title in security_roles:
        if level in ["Junior"]:
            return {
                "primary": "Bachelor's degree in Computer Science, Cybersecurity, Information Security, or related field",
                "alternatives": "IT degree with security certifications (CompTIA Security+, CEH)",
                "preferred": "Entry-level security certifications like CompTIA Security+, GIAC Security Essentials"
            }
        elif level in ["Senior"]:
            return {
                "primary": "Bachelor's or Master's degree in Cybersecurity, Computer Science, or related field",
                "alternatives": None,
                "preferred": "Advanced certifications: CISSP, CISM, OSCP, or equivalent professional certifications"
            }
        else:  # Mid-level
            return {
                "primary": "Bachelor's degree in Computer Science, Cybersecurity, or related field",
                "alternatives": None,
                "preferred": "Professional security certifications (CEH, CompTIA Security+, GIAC)"
            }
    
    elif job_title in design_roles:
        if level in ["Junior"]:
            return {
                "primary": "Bachelor's degree in Design, HCI, Computer Science, or related field",
                "alternatives": "Relevant diploma with strong portfolio demonstrating UI/UX work",
                "preferred": "Completed UX/UI design courses, Google UX Design Certificate, strong portfolio"
            }
        elif level in ["Senior"]:
            return {
                "primary": "Bachelor's or Master's degree in Design, HCI, Interaction Design, or related field",
                "alternatives": None,
                "preferred": "Master's in HCI/Design, extensive portfolio with case studies"
            }
        else:  # Mid-level
            return {
                "primary": "Bachelor's degree in Design, HCI, or related field",
                "alternatives": None,
                "preferred": "Professional portfolio, certifications in UX research or design thinking"
            }
    
    elif job_title in management_roles:
        if level in ["Associate", "Junior"]:
            return {
                "primary": "Bachelor's degree in Computer Science, Business, or related field",
                "alternatives": "Technical background with product management training",
                "preferred": "Agile/Scrum certifications (CSM, CSPO), relevant bootcamp completion"
            }
        elif level in ["Senior"]:
            return {
                "primary": "Bachelor's or Master's degree in Computer Science, Engineering, Business, or related field",
                "alternatives": None,
                "preferred": "MBA or Master's degree, PMP, SAFe, or advanced Agile certifications"
            }
        else:  # Mid-level
            return {
                "primary": "Bachelor's degree in Computer Science, Business, or related technical field",
                "alternatives": None,
                "preferred": "Relevant certifications (PMP, CSM, CSPO), demonstrated leadership experience"
            }
    
    # Default for other roles
    return {
        "primary": "Bachelor's degree in Computer Science, IT, or related field",
        "alternatives": None,
        "preferred": "Relevant professional certifications"
    }


def get_additional_requirements(job_title, level):
    """Generate additional realistic requirements based on level"""
    
    base_requirements = [
        "Strong problem-solving and analytical thinking abilities",
        "Excellent written and verbal communication skills",
        "Ability to work effectively in a team environment",
        "Self-motivated with ability to manage time effectively"
    ]
    
    if level in ["Intern", "Trainee"]:
        additional = [
            "Eagerness to learn and adapt to new technologies",
            "Basic understanding of software development lifecycle",
            "Good academic record",
            "Passion for technology and continuous learning"
        ]
        return base_requirements + additional
    
    elif level in ["Junior"]:
        additional = [
            "Understanding of Agile/Scrum methodologies",
            "Good debugging and troubleshooting skills",
            "Willingness to learn from senior team members",
            "Basic project management awareness"
        ]
        return base_requirements + additional
    
    elif level in ["Mid-level", "Associate"]:
        additional = [
            "Proven experience in Agile/Scrum environments",
            "Strong debugging and optimization skills",
            "Ability to work independently with minimal supervision",
            "Experience with code review and quality assurance processes",
            "Good understanding of software design patterns"
        ]
        return base_requirements + additional
    
    elif level in ["Senior", "Lead", "Lead QA"]:
        additional = [
            "Proven leadership and mentoring capabilities",
            "Strong stakeholder management experience",
            "Excellent architectural and design decision-making skills",
            "Experience leading technical projects or teams",
            "Ability to estimate efforts and manage technical debt",
            "Track record of delivering complex projects on time"
        ]
        return base_requirements + additional
    
    else:
        return base_requirements


def get_preferred_qualifications(job_title, level):
    """Generate nice-to-have qualifications"""
    
    preferred = []
    
    if level in ["Senior", "Lead", "Lead QA"]:
        preferred.extend([
            "Experience in interviewing and hiring technical talent",
            "Contributions to open-source projects",
            "Published technical articles or conference presentations",
            "Experience working in international teams"
        ])
    
    if level not in ["Intern", "Trainee"]:
        preferred.extend([
            "Experience with modern development tools and practices",
            "Familiarity with cloud platforms (AWS, Azure, GCP)",
            "Understanding of DevOps principles"
        ])
    
    # Role-specific preferences
    if "Data" in job_title or "ML" in job_title or "Machine Learning" in job_title:
        preferred.append("Experience with big data technologies (Spark, Hadoop)")
        preferred.append("Published research or Kaggle competition participation")
    
    if "Security" in job_title:
        preferred.append("Bug bounty participation or CVE discoveries")
        preferred.append("Security research or published vulnerability reports")
    
    if "DevOps" in job_title or "Cloud" in job_title or "SRE" in job_title:
        preferred.append("Experience with infrastructure as code")
        preferred.append("Knowledge of monitoring and observability tools")
    
    if "Lead" in level or "Senior" in level:
        preferred.append("Previous experience in a leadership or mentoring role")
    
    return preferred[:5]  # Return max 5 items


def get_responsibilities(job_title, level):
    """Generate level-appropriate responsibilities"""
    
    if level in ["Intern", "Trainee"]:
        return [
            "Assist senior team members in daily development and operational tasks",
            "Learn and apply best practices in software development",
            "Participate in team meetings and code review sessions",
            "Write clean, maintainable code under guidance and supervision",
            "Help document technical processes and solutions",
            "Contribute to testing and quality assurance activities"
        ]
    
    elif level in ["Junior"]:
        return [
            "Develop and maintain software features according to specifications",
            "Write unit tests and participate in debugging activities",
            "Participate in code reviews and incorporate feedback",
            "Collaborate with team members on assigned projects",
            "Document code and maintain technical documentation",
            "Learn new technologies and tools as required by projects"
        ]
    
    elif level in ["Mid-level", "Associate"]:
        return [
            "Design, develop, and test software solutions independently",
            "Write efficient, reusable, and reliable code",
            "Conduct thorough code reviews and provide constructive feedback",
            "Troubleshoot, debug, and resolve technical issues",
            "Collaborate with cross-functional teams on requirements and delivery",
            "Contribute to technical design discussions and decisions",
            "Mentor junior developers when needed"
        ]
    
    elif level in ["Senior", "Lead", "Lead QA"]:
        return [
            "Lead technical design and architectural decisions for projects",
            "Mentor and guide junior and mid-level developers",
            "Drive adoption of best practices and technical standards",
            "Collaborate closely with stakeholders on requirements and priorities",
            "Conduct comprehensive code reviews ensuring quality and standards",
            "Optimize application performance, scalability, and security",
            "Make critical technical decisions and evaluate trade-offs",
            "Contribute to technical strategy and roadmap planning"
        ]
    
    else:
        return [
            "Design, develop, and maintain software solutions",
            "Collaborate with team members on project delivery",
            "Write clean, efficient, and well-documented code",
            "Participate in Agile ceremonies and team activities"
        ]


# ============================================================
# JD Generation Function
# ============================================================

def get_random_city():
    """Get random Sri Lankan city with weighted distribution"""
    cities = list(SL_CITIES.keys())
    weights = list(SL_CITIES.values())
    return random.choices(cities, weights=weights, k=1)[0]


def generate_jd(job_title, level, tech_stack, experience_range, salary_range, city, company_type):
    """Generate a complete job description with realistic requirements"""
    
    # Get requirements
    education = get_education_requirements(job_title, level)
    additional_reqs = get_additional_requirements(job_title, level)
    preferred_quals = get_preferred_qualifications(job_title, level)
    responsibilities = get_responsibilities(job_title, level)
    
    # Job-specific descriptions
    descriptions = {
        "Software Engineer": f"We are seeking a talented {level} Software Engineer to join our development team and contribute to building scalable software solutions.",
        "Full Stack Developer": f"Looking for a skilled {level} Full Stack Developer to build end-to-end solutions using modern technologies.",
        "Data Scientist": f"Join our analytics team as a {level} Data Scientist and drive data-driven decision making across the organization.",
        "Data Engineer": f"We need a {level} Data Engineer to design, build, and maintain our data infrastructure and pipelines.",
        "QA Engineer": f"Seeking a detail-oriented {level} QA Engineer to ensure the highest quality standards for our products.",
        "DevOps Engineer": f"Looking for a {level} DevOps Engineer to optimize our CI/CD pipelines and cloud infrastructure.",
        "Frontend Developer": f"Join us as a {level} Frontend Developer to create beautiful, responsive user interfaces.",
        "Backend Developer": f"We're hiring a {level} Backend Developer to build robust, scalable server-side solutions.",
        "UI/UX Designer": f"Seeking a creative {level} UI/UX Designer to enhance user experiences across our products.",
        "Business Analyst": f"Looking for a {level} Business Analyst to bridge business needs and technology solutions.",
        "Mobile Developer": f"Join our mobile team as a {level} Mobile Developer to build next-generation mobile applications.",
        "Cloud Engineer": f"We need a {level} Cloud Engineer to manage and optimize our cloud infrastructure.",
        "Database Administrator": f"Seeking a {level} Database Administrator to maintain and optimize our database systems.",
        "Technical Lead": f"Looking for an experienced Technical Lead to guide our engineering team and drive technical excellence.",
        "Solutions Architect": f"We need a Solutions Architect to design enterprise-scale systems and architectural patterns.",
        "Machine Learning Engineer": f"Seeking a {level} ML Engineer to build production-ready AI/ML systems.",
        "Security Engineer": f"Looking for a {level} Security Engineer to protect our infrastructure and ensure compliance.",
        "Product Manager": f"Join us as a {level} Product Manager to drive product strategy and delivery.",
        "System Administrator": f"We need a {level} System Administrator to manage and maintain our IT infrastructure.",
        "Network Engineer": f"Seeking a {level} Network Engineer to design, implement, and maintain our network infrastructure.",
        "Scrum Master": f"Looking for a {level} Scrum Master to facilitate Agile processes and team collaboration.",
        "Data Analyst": f"Join us as a {level} Data Analyst to derive actionable insights from data.",
        "Site Reliability Engineer": f"We need a {level} SRE to ensure system reliability, performance, and scalability.",
        "Game Developer": f"Seeking a {level} Game Developer to create engaging and immersive gaming experiences.",
        "Blockchain Developer": f"Looking for a {level} Blockchain Developer to build decentralized applications and smart contracts.",
        "Technical Writer": f"Join us as a {level} Technical Writer to create comprehensive technical documentation."
    }
    
    # Work mode
    work_mode = random.choices(
        ["On-site", "Hybrid", "Remote"],
        weights=[0.5, 0.3, 0.2] if level in ["Intern", "Trainee", "Junior"] else [0.3, 0.4, 0.3]
    )[0]
    
    jd_text = f"""============================================================
{job_title.upper()} - {level.upper()}
============================================================

Company: {company_type}
Location: {city}, Sri Lanka
Employment Type: Full-time
Work Mode: {work_mode}

============================================================
ABOUT THE ROLE
============================================================

{descriptions.get(job_title, f"We are looking for a {level} {job_title} to join our team.")}

============================================================
KEY RESPONSIBILITIES
============================================================

"""
    
    for i, resp in enumerate(responsibilities, 1):
        jd_text += f"{i}. {resp}\n"
    
    jd_text += f"""
============================================================
REQUIRED QUALIFICATIONS
============================================================

Education:
- {education['primary']}"""
    
    if education['alternatives']:
        jd_text += f"\n- Alternative: {education['alternatives']}"
    
    if education['preferred']:
        jd_text += f"\n- Preferred: {education['preferred']}"
    
    # Experience description
    if level in ["Intern", "Trainee"]:
        experience_desc = "Recent graduate or final year undergraduate student"
    else:
        experience_desc = f"{experience_range} years of relevant experience in {job_title} or related roles"
    
    jd_text += f"""

Experience:
- {experience_desc}

Technical Skills Required:
"""
    
    for skill in tech_stack:
        jd_text += f"- {skill}\n"
    
    jd_text += f"""
Additional Requirements:
"""
    for req in additional_reqs:
        jd_text += f"- {req}\n"
    
    # Preferred qualifications
    if preferred_quals:
        jd_text += f"""
Preferred Qualifications (Nice to Have):
"""
        for pref in preferred_quals:
            jd_text += f"- {pref}\n"
    
    # Benefits
    benefits = [
        f"Competitive salary: Rs. {salary_range} per month",
        "Performance-based annual bonuses",
        "Comprehensive medical insurance coverage",
        "Professional development and training opportunities"
    ]
    
    if work_mode in ["Hybrid", "Remote"]:
        benefits.append("Flexible working arrangements")
    else:
        benefits.append("Structured working hours with work-life balance")
    
    if level not in ["Intern", "Trainee"]:
        benefits.append("Annual leave and sick leave provisions")
    
    benefits.extend([
        "Collaborative and innovative work environment",
        "Clear career progression pathways",
        "Modern tools and technologies"
    ])
    
    if level in ["Senior", "Lead", "Lead QA"]:
        benefits.append("Leadership development programs")
    
    jd_text += f"""
============================================================
WHAT WE OFFER
============================================================

"""
    for benefit in benefits:
        jd_text += f"- {benefit}\n"
    
    jd_text += f"""
============================================================
HOW TO APPLY
============================================================

Please send your CV and cover letter to: recruitment@{company_type.lower().replace(' ', '')}.lk
or apply through our careers portal at: www.{company_type.lower().replace(' ', '')}.lk/careers

Application Deadline: {random.choice(['Within 2 weeks', 'Within 14 days', '30 days from posting', 'Open until filled'])}

Equal Opportunity Employer: We are committed to creating a diverse and inclusive workplace. 
All qualified applicants will receive consideration for employment without regard to race, 
color, religion, gender, national origin, age, disability status, or any other characteristic 
protected by law.
"""
    
    return jd_text


def generate_dataset(num_jds=1000, output_dir="data/jd_data"):
    """Generate synthetic JD dataset"""
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating {num_jds} synthetic ICT job descriptions...")
    print(f"Output directory: {output_path.absolute()}")
    print("=" * 60)
    
    # Calculate jobs per role based on weights
    total_weight = sum(job["weight"] for job in JOB_TEMPLATES.values())
    
    jd_count = 0
    stats = {"cities": {}, "levels": {}, "roles": {}, "work_modes": {}}
    
    for job_title, config in JOB_TEMPLATES.items():
        # Calculate number of JDs for this role
        role_count = int((config["weight"] / total_weight) * num_jds)
        
        for _ in range(role_count):
            # Select random level
            level = random.choice(config["levels"])
            
            # Select random tech stack
            tech_stack = random.choice(config["tech_stacks"])
            
            # Get experience and salary for level
            experience_range = config["experience"][level]
            salary_range = config["salary"][level]
            
            # Get random city and company type
            city = get_random_city()
            company_type = random.choice(COMPANY_TYPES)
            
            # Generate JD
            jd_text = generate_jd(
                job_title, level, tech_stack, 
                experience_range, salary_range, 
                city, company_type
            )
            
            # Extract work mode for stats
            work_mode = "On-site"
            if "Hybrid" in jd_text:
                work_mode = "Hybrid"
            elif "Remote" in jd_text:
                work_mode = "Remote"
            
            # Save to file
            jd_count += 1
            safe_title = job_title.lower().replace(' ', '_').replace('/', '_')
            safe_level = level.lower().replace(' ', '_').replace('-', '_')
            filename = f"{safe_title}_{safe_level}_{jd_count:04d}.txt"
            filepath = output_path / filename
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(jd_text)
            
            # Update stats
            stats["cities"][city] = stats["cities"].get(city, 0) + 1
            stats["levels"][level] = stats["levels"].get(level, 0) + 1
            stats["roles"][job_title] = stats["roles"].get(job_title, 0) + 1
            stats["work_modes"][work_mode] = stats["work_modes"].get(work_mode, 0) + 1
            
            if jd_count % 100 == 0:
                print(f"  Generated {jd_count}/{num_jds} JDs...")
    
    print(f"\n{'='*60}")
    print(f"✅ Successfully generated {jd_count} job descriptions!")
    print(f"{'='*60}")
    
    print("\n📊 GENERATION STATISTICS")
    print(f"{'='*60}")
    
    print("\n🔹 Top 15 Cities:")
    for city, count in sorted(stats["cities"].items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {city}: {count} ({count/jd_count*100:.1f}%)")
    
    print("\n🔹 Experience Levels:")
    for level, count in sorted(stats["levels"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {level}: {count} ({count/jd_count*100:.1f}%)")
    
    print("\n🔹 Work Modes:")
    for mode, count in sorted(stats["work_modes"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {mode}: {count} ({count/jd_count*100:.1f}%)")
    
    print("\n🔹 Job Roles (All):")
    for role, count in sorted(stats["roles"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {role}: {count} ({count/jd_count*100:.1f}%)")
    
    print(f"\n{'='*60}")
    print(f"✅ Files saved to: {output_path.absolute()}")
    print(f"✅ Ready for preprocessing and feature extraction!")
    print(f"{'='*60}")


# ============================================================
# Main Execution
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate synthetic ICT job descriptions")
    parser.add_argument("--count", type=int, default=1000, 
                       help="Number of JDs to generate (default: 1000)")
    parser.add_argument("--output", type=str, default="data/jd_data",
                       help="Output directory (default: data/jd_data)")
    
    args = parser.parse_args()
    
    generate_dataset(num_jds=args.count, output_dir=args.output)