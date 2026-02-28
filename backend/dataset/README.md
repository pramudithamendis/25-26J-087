# Agentic AI Evaluation Dataset

This dataset is designed for evaluating and benchmarking the agentic AI candidate evaluation system (`/api/evaluate`).

## Dataset Overview

The dataset contains:
- **Real Candidates**: 58 real resume profiles (from `resume/` folder)
- **Synthetic Candidates**: 100-200 synthetically generated candidate profiles
- **Job Descriptions**: 20-30 synthetic job descriptions
- **Ground Truth Labels**: Expected evaluation scores and decisions for candidate-job pairs

## Dataset Structure

```
dataset/
├── candidates/
│   ├── real/
│   │   └── metadata.json          # Real candidate profiles
│   └── synthetic/
│       └── metadata.json           # Synthetic candidate profiles
├── jobs/
│   └── synthetic/
│       └── jobs.json              # Synthetic job descriptions
├── evaluations/
│   └── ground_truth.json          # Candidate-job pairs with labels
├── dataset_metadata.json          # Dataset statistics and metadata
├── candidates.csv                 # Candidates in CSV format
├── jobs.csv                       # Jobs in CSV format
└── evaluations.csv                # Evaluation pairs in CSV format
```

## Dataset Generation

### Prerequisites

1. **Real Resumes**: Place 58 PDF resumes in the `resume/` folder (relative to project root)
2. **OpenAI API Key**: Set `OPENAI_API_KEY` in `.env` for LLM-based generation
3. **Python Dependencies**: All required packages from `requirements.txt`

### Generation Process

The dataset is generated in phases:

1. **Phase 1: Resume Analysis**
   - Analyzes 58 real resumes to extract patterns
   - Identifies skill distributions, role categories, experience levels
   - Creates template profiles

2. **Phase 2: Synthetic Candidate Generation**
   - Generates 100-200 synthetic candidates using LLM or rule-based approach
   - Matches real resume patterns and distributions
   - Creates realistic profiles with skills, experience, education

3. **Phase 3: Job Description Generation**
   - Generates 20-30 diverse job descriptions
   - Matches job types to candidate profiles
   - Includes must-have and nice-to-have skills

4. **Phase 4: Ground Truth Labeling**
   - Creates evaluation pairs (candidate-job combinations)
   - Generates expected scores (0-100) and decisions
   - Uses LLM-based or rule-based labeling

5. **Phase 5: Dataset Organization**
   - Organizes all components into structured format
   - Generates metadata and statistics
   - Exports in JSON and CSV formats

6. **Phase 6: Validation**
   - Validates dataset structure and data quality
   - Checks ground truth labels for consistency
   - Generates validation report

### Running Dataset Generation

Use the provided script:

```python
from app.services.dataset import (
    ResumeAnalyzer,
    CandidateGenerator,
    JobGenerator,
    GroundTruthLabeler,
    DatasetBuilder,
    DatasetValidator
)

# 1. Analyze real resumes
analyzer = ResumeAnalyzer(resume_folder="resume")
analysis_results = analyzer.analyze_all_resumes()
analyzer.save_analysis("dataset/analysis_results.json")

# 2. Generate synthetic candidates
candidate_gen = CandidateGenerator(analysis_results)
synthetic_candidates = candidate_gen.generate_candidates(count=150)
candidate_gen.save_candidates(synthetic_candidates, "dataset/candidates_synthetic.json")

# 3. Generate jobs
job_gen = JobGenerator(analysis_results)
jobs = job_gen.generate_jobs(count=25)
job_gen.save_jobs(jobs, "dataset/jobs.json")

# 4. Create ground truth labels
labeler = GroundTruthLabeler()
evaluation_pairs = labeler.create_labels(
    synthetic_candidates,
    jobs,
    method="llm_based"  # or "rule_based"
)
labeler.save_labels(evaluation_pairs, "dataset/ground_truth.json")

# 5. Build complete dataset
builder = DatasetBuilder(output_dir="dataset")
dataset_info = builder.build_dataset(
    real_candidates=None,  # Can include real candidates if available
    synthetic_candidates=synthetic_candidates,
    jobs=jobs,
    evaluation_pairs=evaluation_pairs,
    analysis_results=analysis_results
)

# 6. Validate dataset
validator = DatasetValidator(dataset_dir="dataset")
validation_results = validator.validate_dataset()
validator.save_validation_report("dataset/validation_report.json")
```

Or use the convenience script (see `generate_dataset.py`):

```bash
python backend/scripts/generate_dataset.py
```

## Dataset Statistics

After generation, check `dataset_metadata.json` for:
- Total number of candidates (real + synthetic)
- Total number of jobs
- Total evaluation pairs
- Score distribution
- Decision distribution
- Skill frequency
- Role distribution

## Usage in Research

### Performance Benchmarking

Use the dataset to measure evaluation system performance:

```python
# Load ground truth
with open("dataset/evaluations/ground_truth.json", 'r') as f:
    evaluation_pairs = json.load(f)

# Run evaluation system on each pair
for pair in evaluation_pairs:
    candidate = pair["candidate"]
    job = pair["job"]
    ground_truth = pair["ground_truth"]
    
    # Call /api/evaluate endpoint
    result = evaluate_candidate(candidate, job)
    
    # Compare with ground truth
    accuracy = compare_results(result, ground_truth)
```

### Metrics

- **Accuracy**: Percentage of decisions matching ground truth
- **Score Correlation**: Correlation between predicted and ground truth scores
- **Precision/Recall**: For each decision category (Selected/Review/Not Selected)
- **Mean Absolute Error**: Average difference between predicted and ground truth scores

### Ablation Studies

Test different configurations:
- Agentic vs. traditional pipeline
- Different agent configurations
- Different LLM models
- Different temperature settings

## Data Format

### Candidate Format

```json
{
  "id": "synthetic_1",
  "type": "synthetic",
  "profile": {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "github_handle": "johndoe",
    "skills_raw": ["Python", "JavaScript", "React"],
    "experience": [
      {
        "title": "Software Engineer",
        "company": "TechCorp",
        "start": "2020-01",
        "end": "2022-06",
        "highlights": ["Developed web applications", "Led team of 3"]
      }
    ],
    "education": [
      {
        "institution": "State University",
        "degree": "BSc Computer Science",
        "start": "2016-09",
        "end": "2020-05"
      }
    ]
  }
}
```

### Job Format

```json
{
  "id": "job_1",
  "type": "synthetic",
  "job": {
    "title": "Mid-Level Software Engineer",
    "jd_text": "Full job description...",
    "must_have": ["Python", "JavaScript", "SQL"],
    "nice_to_have": ["Docker", "AWS"],
    "min_years": 3,
    "location": "Remote"
  }
}
```

### Ground Truth Format

```json
{
  "candidate": { /* candidate profile */ },
  "job": { /* job description */ },
  "ground_truth": {
    "total_score": 75,
    "decision": "Selected",
    "reasoning": "Candidate has all required skills and sufficient experience.",
    "role_predictions": [
      {"role": "Software Engineer", "similarity": 0.85}
    ],
    "breakdown": {
      "skill_match": 25,
      "experience_match": 25,
      "overall_fit": 25
    }
  }
}
```

## Configuration

Set in `backend/app/config.py` or `.env`:

- `DATASET_OUTPUT_DIR`: Output directory (default: "dataset")
- `SYNTHETIC_CANDIDATE_COUNT`: Number of synthetic candidates (default: 150)
- `SYNTHETIC_JOB_COUNT`: Number of synthetic jobs (default: 25)
- `USE_LLM_FOR_SYNTHESIS`: Use OpenAI for generation (default: True)
- `GROUND_TRUTH_METHOD`: "manual" or "llm_based" (default: "llm_based")

## Research Benefits

This dataset enables:

1. **Performance Benchmarking**: Measure system accuracy against ground truth
2. **Ablation Studies**: Test different agent configurations
3. **Error Analysis**: Identify failure cases and edge cases
4. **Statistical Validation**: Prove system effectiveness with quantitative data
5. **Reproducible Research**: Same dataset = same results
6. **Comparison Studies**: Agentic vs. traditional pipeline performance

## Validation

After generation, the dataset is automatically validated:

- Structure validation (required files and directories)
- Data quality checks (required fields, data types)
- Ground truth validation (score ranges, decision consistency)
- Statistics generation

Check `validation_report.json` for detailed validation results.

## License

[Add your license information here]

## Citation

If you use this dataset in your research, please cite:

```
[Your citation format here]
```

## Contact

[Your contact information]

