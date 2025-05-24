import logging
from typing import Dict, Any, List

class PRAnalysisUtility:
    """Central orchestrator for PR analysis workflow"""
    
    def __init__(self, repo_store, dependency_mapper, context_generator, llm_engine, github_bot):
        self.repo_store = repo_store
        self.dependency_mapper = dependency_mapper
        self.context_generator = context_generator
        self.llm_engine = llm_engine
        self.github_bot = github_bot
        self.logger = logging.getLogger(__name__)
    
    def process_pr(self, payload: Dict[str, Any]):
        """Process a GitHub PR webhook payload"""
        try:
            # Extract PR metadata
            pr_data = self._extract_pr_metadata(payload)
            
            # Get related repositories
            related_repos = self.repo_store.get_related_repos(pr_data["repository"])
            
            # Get PR diffs
            diffs = self._fetch_pr_diffs(pr_data)
            
            # Analyze dependencies
            impacted_components = self.dependency_mapper.analyze_impacts(diffs, pr_data["repository"], related_repos)
            
            # Generate context for LLM
            context = self.context_generator.build_context(pr_data, diffs, impacted_components)
            
            # Get LLM analysis
            analysis_results = self.llm_engine.analyze(context)
            
            # Post comment to GitHub
            self.github_bot.post_comment(pr_data, analysis_results)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error processing PR: {str(e)}")
            return False
    
    def _extract_pr_metadata(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant PR metadata from webhook payload"""
        pr = payload["pull_request"]
        
        return {
            "pr_number": pr["number"],
            "title": pr["title"],
            "author": pr["user"]["login"],
            "repository": payload["repository"]["full_name"],
            "base_branch": pr["base"]["ref"],
            "head_branch": pr["head"]["ref"],
            "pr_url": pr["html_url"],
            "diff_url": pr["diff_url"],
            "created_at": pr["created_at"],
            "updated_at": pr["updated_at"]
        }
    
    def _fetch_pr_diffs(self, pr_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch PR diffs from GitHub"""
        # This would typically use GitHub API to fetch actual diffs
        # For now, return placeholder data
        return [
            {
                "file_path": "src/main/java/com/example/service/UserService.java",
                "changes": "+10/-5",
                "content": "Sample diff content"
            }
        ]
