"""
Convenience script to generate the complete dataset.

This script orchestrates the entire dataset generation process:
1. Analyze real resumes
2. Generate synthetic candidates
3. Generate job descriptions
4. Create ground truth labels
5. Build and organize dataset
6. Validate dataset
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from app.services.dataset import (
    ResumeAnalyzer,
    CandidateGenerator,
    JobGenerator,
    GroundTruthLabeler,
    DatasetBuilder,
    DatasetValidator
)
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function to generate complete dataset."""
    logger.info("Starting dataset generation process...")
    
    # Configuration
    resume_folder = "resume"  # Relative to project root
    output_dir = settings.DATASET_OUTPUT_DIR
    candidate_count = settings.SYNTHETIC_CANDIDATE_COUNT
    job_count = settings.SYNTHETIC_JOB_COUNT
    label_method = settings.GROUND_TRUTH_METHOD
    
    # Check if resume folder exists
    resume_path = Path(resume_folder)
    if not resume_path.exists():
        logger.warning(f"Resume folder not found: {resume_folder}")
        logger.info("Continuing with default templates...")
        analysis_results = None
    else:
        # Phase 1: Analyze real resumes
        logger.info("Phase 1: Analyzing real resumes...")
        analyzer = ResumeAnalyzer(resume_folder=resume_folder)
        try:
            analysis_results = analyzer.analyze_all_resumes()
            analysis_output = Path(output_dir) / "analysis_results.json"
            analyzer.save_analysis(str(analysis_output))
            logger.info(f"✓ Resume analysis complete. Results saved to {analysis_output}")
        except Exception as e:
            logger.error(f"Resume analysis failed: {str(e)}")
            logger.info("Continuing with default templates...")
            analysis_results = None
    
    # Phase 2: Generate synthetic candidates
    logger.info(f"Phase 2: Generating {candidate_count} synthetic candidates...")
    candidate_gen = CandidateGenerator(analysis_results=analysis_results)
    try:
        synthetic_candidates = candidate_gen.generate_candidates(count=candidate_count)
        logger.info(f"✓ Generated {len(synthetic_candidates)} synthetic candidates")
    except Exception as e:
        logger.error(f"Candidate generation failed: {str(e)}")
        raise
    
    # Phase 3: Generate job descriptions
    logger.info(f"Phase 3: Generating {job_count} job descriptions...")
    job_gen = JobGenerator(analysis_results=analysis_results)
    try:
        jobs = job_gen.generate_jobs(count=job_count)
        logger.info(f"✓ Generated {len(jobs)} job descriptions")
    except Exception as e:
        logger.error(f"Job generation failed: {str(e)}")
        raise
    
    # Phase 4: Create ground truth labels
    logger.info(f"Phase 4: Creating ground truth labels using {label_method} method...")
    labeler = GroundTruthLabeler()
    try:
        evaluation_pairs = labeler.create_labels(
            synthetic_candidates,
            jobs,
            method=label_method if label_method != "manual" else "llm_based"
        )
        logger.info(f"✓ Created {len(evaluation_pairs)} evaluation pairs with labels")
    except Exception as e:
        logger.error(f"Label creation failed: {str(e)}")
        raise
    
    # Phase 5: Build complete dataset
    logger.info("Phase 5: Building and organizing dataset...")
    builder = DatasetBuilder(output_dir=output_dir)
    try:
        dataset_info = builder.build_dataset(
            synthetic_candidates=synthetic_candidates,
            jobs=jobs,
            evaluation_pairs=evaluation_pairs,
            real_candidates=None,  # Can be added if real candidates are processed
            analysis_results=analysis_results
        )
        logger.info(f"✓ Dataset built successfully in {dataset_info['output_dir']}")
    except Exception as e:
        logger.error(f"Dataset building failed: {str(e)}")
        raise
    
    # Phase 6: Validate dataset
    logger.info("Phase 6: Validating dataset...")
    validator = DatasetValidator(dataset_dir=output_dir)
    try:
        validation_results = validator.validate_dataset()
        validation_report_path = validator.save_validation_report()
        logger.info(f"✓ Validation complete. Report saved to {validation_report_path}")
        
        # Print validation summary
        overall_status = validation_results.get("overall_status", "unknown")
        logger.info(f"Overall validation status: {overall_status}")
        
        if overall_status == "failed":
            logger.warning("Dataset validation found issues. Check validation_report.json for details.")
    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        # Don't raise - validation failure doesn't prevent dataset usage
    
    logger.info("=" * 60)
    logger.info("Dataset generation complete!")
    logger.info(f"Dataset location: {output_dir}")
    logger.info(f"Total candidates: {len(synthetic_candidates)}")
    logger.info(f"Total jobs: {len(jobs)}")
    logger.info(f"Total evaluation pairs: {len(evaluation_pairs)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

