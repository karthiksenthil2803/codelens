import os
import requests
import logging
from typing import Dict, Any

class GitHubCommentBot:
    """Posts analysis results to GitHub PR comments"""
    
    def __init__(self, api_token=None):
        self.api_token = api_token or os.environ.get("GITHUB_TOKEN")
        self.logger = logging.getLogger(__name__)
    
    def post_comment(self, pr_data: Dict[str, Any], analysis_results: Dict[str, Any]) -> bool:
        """Post analysis results as a comment on the PR"""
        try:
            if not self.api_token:
                self.logger.warning("No GitHub API token provided, skipping comment posting")
                return False
            
            # Format the comment
            comment_body = self._format_comment(analysis_results)
            
            # Post to GitHub
            repo_full_name = pr_data["repository"]
            pr_number = pr_data["pr_number"]
            
            return self._post_github_comment(repo_full_name, pr_number, comment_body)
        
        except Exception as e:
            self.logger.error(f"Error posting GitHub comment: {str(e)}")
            return False
    
    def _format_comment(self, analysis_results: Dict[str, Any]) -> str:
        """Format analysis results as a GitHub comment"""
        if "full_analysis" in analysis_results:
            # If LLM already formatted the response for GitHub
            return analysis_results["full_analysis"]
        
        # Otherwise, format it ourselves
        comment = "# PR Analysis Results\n\n"
        
        # Add summary
        comment += f"## Summary\n{analysis_results['summary']}\n\n"
        
        # Add potential bugs
        comment += f"## Potential Issues\n{analysis_results['bugs']}\n\n"
        
        # Add improvement suggestions
        comment += f"## Suggested Improvements\n{analysis_results['improvements']}\n\n"
        
        # Add security concerns
        comment += f"## Security Considerations\n{analysis_results['security']}\n\n"
        
        # Add testing recommendations
        comment += f"## Testing Recommendations\n{analysis_results['testing']}\n\n"
        
        # Add cross-repo impacts
        comment += f"## Cross-Repository Impacts\n{analysis_results['cross_repo']}\n\n"
        
        comment += "\n\n_This analysis was generated automatically by the PR Analysis Bot._"
        
        return comment
    
    def _post_github_comment(self, repo_full_name: str, pr_number: int, comment_body: str) -> bool:
        """Post a comment to the GitHub PR using the GitHub API"""
        url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
        
        headers = {
            "Authorization": f"token {self.api_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "body": comment_body
        }

        # Test comment
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 201:
            self.logger.info(f"Successfully posted comment to PR #{pr_number}")
            return True
        else:
            self.logger.error(f"Failed to post comment: {response.status_code} {response.text}")
            return False
