from typing import Dict, Any, List

class ContextGenerator:
    """Builds structured prompts for LLM analysis"""
    
    def __init__(self):
        pass
    
    def build_context(self, pr_data: Dict[str, Any], diffs: List[Dict[str, Any]], impacts: Dict[str, Any]) -> str:
        """Build a structured prompt context for LLM analysis"""
        context = self._build_intro_context(pr_data)
        context += self._build_changes_context(diffs)
        context += self._build_impacts_context(impacts)
        context += self._build_analysis_request()
        
        return context
    
    def _build_intro_context(self, pr_data: Dict[str, Any]) -> str:
        """Build introduction context with PR metadata"""
        return f"""
# Pull Request Analysis
- Repository: {pr_data['repository']}
- PR Number: {pr_data['pr_number']}
- Title: {pr_data['title']}
- Author: {pr_data['author']}
- Base Branch: {pr_data['base_branch']}
- Head Branch: {pr_data['head_branch']}

## Overview
This Pull Request contains changes that need to be analyzed for potential impacts.

"""
    
    def _build_changes_context(self, diffs: List[Dict[str, Any]]) -> str:
        """Build context describing the code changes"""
        context = "## Code Changes\n\n"
        
        for diff in diffs:
            context += f"### File: {diff['file_path']}\n"
            context += f"Changes: {diff['changes']}\n\n"
            context += "```java\n"
            context += diff['content'] + "\n"
            context += "```\n\n"
        
        return context
    
    def _build_impacts_context(self, impacts: Dict[str, Any]) -> str:
        """Build context describing potential impacts"""
        context = "## Potential Impacts\n\n"
        
        # Add impacted modules
        context += "### Impacted Modules\n"
        for module in impacts['impacted_modules']:
            context += f"- {module['class_name']} ({module['package']})\n"
        
        context += "\n"
        
        # Add impacted tests
        context += "### Tests to Run\n"
        if impacts['impacted_tests']:
            for test in impacts['impacted_tests']:
                context += f"- {test['test_name']} (tests {test['related_module']})\n"
        else:
            context += "- No specific tests identified\n"
        
        context += "\n"
        
        # Add cross-repo impacts
        context += "### Cross-Repository Impacts\n"
        if impacts['cross_repo_impacts']:
            for impact in impacts['cross_repo_impacts']:
                context += f"- {impact['repository']}: {impact['potential_impact']}\n"
        else:
            context += "- No cross-repository impacts identified\n"
        
        context += "\n"
        
        return context
    
    def _build_analysis_request(self) -> str:
        """Build the analysis request for the LLM"""
        return """
## Analysis Request
Please analyze the changes in this Pull Request and provide:

1. A concise summary of the changes
2. Potential bugs or issues in the implementation
3. Suggestions for code improvements
4. Any security concerns
5. Recommendations for testing
6. Cross-repository impact assessment

Format your response so it can be directly posted as a GitHub PR comment.
"""
