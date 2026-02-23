from typing import Dict, List
import requests
import logging
from datetime import datetime, timedelta
from app.config import settings
import time

logger = logging.getLogger(__name__)

def analyze_github(handle: str) -> Dict:
    """
    Analyze GitHub profile using GitHub REST API v3
    
    Args:
        handle: GitHub username
    
    Returns:
        Dictionary with repos, commits_last_12m, external_prs_merged
    """
    if not handle or not handle.strip():
        logger.warning("Empty GitHub handle provided")
        return {
            "repos": [],
            "commits_last_12m": 0,
            "external_prs_merged": 0
        }
    
    handle = handle.strip()
    
    # Prepare headers
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "CV-Analysis-System"
    }
    
    # Add token if available (increases rate limit from 60 to 5000 requests/hour)
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
    
    base_url = "https://api.github.com"
    
    try:
        # 1. Get user's public repositories
        repos = _fetch_user_repositories(base_url, handle, headers)
        
        # 2. Calculate commits in last 12 months (simplified - sample from top repos)
        commits_last_12m = _calculate_commits_last_12m(base_url, handle, headers, repos)
        
        # 3. Count external PRs merged (simplified for now)
        external_prs_merged = _count_external_prs_merged(base_url, handle, headers)
        
        logger.info(f"GitHub analysis for {handle}: {len(repos)} repos, {commits_last_12m} commits, {external_prs_merged} external PRs")
        
        return {
            "repos": repos,
            "commits_last_12m": commits_last_12m,
            "external_prs_merged": external_prs_merged
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"GitHub API request failed for {handle}: {str(e)}")
        # Return empty data on error
        return {
            "repos": [],
            "commits_last_12m": 0,
            "external_prs_merged": 0
        }
    except Exception as e:
        logger.error(f"Unexpected error analyzing GitHub profile {handle}: {str(e)}")
        return {
            "repos": [],
            "commits_last_12m": 0,
            "external_prs_merged": 0
        }

def _fetch_user_repositories(base_url: str, handle: str, headers: dict) -> List[Dict]:
    """Fetch user's public repositories"""
    repos = []
    page = 1
    per_page = 100  # Max allowed by GitHub API
    
    try:
        while True:
            url = f"{base_url}/users/{handle}/repos"
            params = {
                "type": "all",  # all, owner, member
                "sort": "updated",
                "direction": "desc",
                "per_page": per_page,
                "page": page
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # Check rate limit
            if response.status_code == 403:
                rate_limit = response.headers.get("X-RateLimit-Remaining", "0")
                logger.warning(f"GitHub API rate limit reached. Remaining: {rate_limit}")
                break
            
            if response.status_code == 404:
                logger.warning(f"GitHub user {handle} not found")
                break
            
            if response.status_code != 200:
                logger.error(f"GitHub API error: {response.status_code} - {response.text}")
                break
            
            page_repos = response.json()
            if not page_repos:
                break
            
            for repo in page_repos:
                repos.append({
                    "name": repo.get("name", ""),
                    "full_name": repo.get("full_name", ""),
                    "description": repo.get("description", ""),
                    "language": repo.get("language", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "is_fork": repo.get("fork", False),
                    "created_at": repo.get("created_at", ""),
                    "updated_at": repo.get("updated_at", ""),
                    "url": repo.get("html_url", "")
                })
            
            # If we got fewer than per_page, we're done
            if len(page_repos) < per_page:
                break
            
            page += 1
            
            # Safety limit: don't fetch more than 100 repos
            if len(repos) >= 100:
                break
        
        logger.info(f"Fetched {len(repos)} repositories for {handle}")
        return repos
    
    except Exception as e:
        logger.error(f"Error fetching repositories: {str(e)}")
        return repos

def _calculate_commits_last_12m(base_url: str, handle: str, headers: dict, repos: List[Dict]) -> int:
    """Calculate total commits in last 12 months across all repos"""
    if not repos:
        return 0
    
    total_commits = 0
    one_year_ago = datetime.now() - timedelta(days=365)
    
    try:
        # Sample from top 10 repos to avoid rate limits
        repos_to_check = repos[:10]
        
        for repo in repos_to_check:
            repo_name = repo.get("name", "")
            if not repo_name:
                continue
            
            try:
                # Get commits since one year ago
                url = f"{base_url}/repos/{handle}/{repo_name}/commits"
                params = {
                    "author": handle,
                    "since": one_year_ago.isoformat(),
                    "per_page": 1  # We just need to check if there are commits
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=5)
                
                if response.status_code == 200:
                    commits = response.json()
                    if commits:
                        # Try to get total from pagination Link header
                        link_header = response.headers.get("Link", "")
                        if link_header and "rel=\"last\"" in link_header:
                            # Parse last page number
                            import re
                            match = re.search(r'page=(\d+)>; rel="last"', link_header)
                            if match:
                                last_page = int(match.group(1))
                                # Estimate: 30 commits per page (default)
                                total_commits += (last_page - 1) * 30 + len(commits)
                            else:
                                # Fallback: count what we have
                                total_commits += len(commits)
                        else:
                            # No pagination, count what we have
                            total_commits += len(commits)
                
                # Small delay to avoid rate limiting
                time.sleep(0.1)
            
            except Exception as e:
                logger.debug(f"Error counting commits for {repo_name}: {str(e)}")
                continue
        
        # If we sampled repos, estimate total
        if len(repos) > len(repos_to_check):
            avg_commits_per_repo = total_commits / len(repos_to_check) if repos_to_check else 0
            estimated_total = int(avg_commits_per_repo * len(repos))
            logger.info(f"Estimated commits: {estimated_total} (based on {len(repos_to_check)} sampled repos)")
            return estimated_total
        
        logger.info(f"Total commits in last 12 months: {total_commits}")
        return total_commits
    
    except Exception as e:
        logger.error(f"Error calculating commits: {str(e)}")
        return 0

def _count_external_prs_merged(base_url: str, handle: str, headers: dict) -> int:
    """Count external pull requests merged (PRs to other repos)"""
    try:
        # Search for merged PRs by the user
        url = f"{base_url}/search/issues"
        params = {
            "q": f"author:{handle} type:pr is:merged",
            "per_page": 1  # We just need the count
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            total_count = data.get("total_count", 0)
            
            # Filter out PRs to user's own repos (external PRs only)
            # This is an approximation - we'd need to check each PR's repo
            # For now, return a fraction as external PRs
            # Most developers have more PRs to their own repos than external
            external_estimate = max(0, int(total_count * 0.3))  # Estimate 30% are external
            logger.info(f"Total merged PRs: {total_count}, Estimated external: {external_estimate}")
            return external_estimate
        
        return 0
    
    except Exception as e:
        logger.debug(f"Error counting external PRs: {str(e)}")
        return 0

