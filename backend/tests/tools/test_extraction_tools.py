"""
Unit tests for extraction tools.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.agents.tools.extraction_tools import (
    extract_cv_tool,
    extract_linkedin_tool,
    extract_jd_tool
)


class TestExtractionTools:
    """Test cases for extraction tools"""
    
    @patch('app.services.agents.tools.extraction_tools.preprocess_pdf')
    @patch('app.services.agents.tools.extraction_tools.extract_from_cv_openai')
    def test_extract_cv_tool_success(self, mock_extract, mock_preprocess):
        """Test successful CV extraction"""
        mock_preprocess.return_value = {"full_text": "CV text"}
        mock_extract.return_value = {
            "skills_raw": ["Java", "Python"],
            "experience": [],
            "education": [],
            "github_handle": ""
        }
        
        result = extract_cv_tool("/path/to/cv.pdf")
        assert result["status"] == "success"
        assert "data" in result
        assert len(result["data"]["skills_raw"]) == 2
    
    def test_extract_cv_tool_error(self):
        """Test CV extraction error handling"""
        result = extract_cv_tool("/nonexistent/path.pdf")
        assert result["status"] == "error"
        assert "error" in result
    
    @patch('app.services.agents.tools.extraction_tools.preprocess_pdf')
    @patch('app.services.agents.tools.extraction_tools.extract_from_linkedin_openai')
    def test_extract_linkedin_tool_success(self, mock_extract, mock_preprocess):
        """Test successful LinkedIn extraction"""
        mock_preprocess.return_value = {"full_text": "LinkedIn text"}
        mock_extract.return_value = {
            "skills_raw": ["Leadership"],
            "experience": [],
            "education": [],
            "certifications": []
        }
        
        result = extract_linkedin_tool("/path/to/linkedin.pdf")
        assert result["status"] == "success"
        assert "data" in result
    
    @patch('app.services.agents.tools.extraction_tools.extract_from_jd')
    def test_extract_jd_tool_success(self, mock_extract):
        """Test successful JD extraction"""
        mock_extract.return_value = {
            "title": "Software Engineer",
            "must_have": ["Java", "Python"],
            "nice_to_have": ["AWS"],
            "min_years": 3
        }
        
        result = extract_jd_tool("Job description text")
        assert result["status"] == "success"
        assert result["data"]["title"] == "Software Engineer"
        assert len(result["data"]["must_have"]) == 2

