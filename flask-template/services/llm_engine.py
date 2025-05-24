import os
import requests
import logging
from typing import Dict, Any

class LLMEngine:
    """Interface with LLM APIs for PR analysis"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("LLM_API_KEY")
        self.logger = logging.getLogger(__name__)
        self.api_url = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
        self.model = os.environ.get("LLM_MODEL", "gpt-4")
    
    def analyze(self, context: str) -> Dict[str, Any]:
        """Send context to LLM and get analysis results"""
        try:
            if not self.api_key:
                self.logger.warning("No LLM API key provided, using mock response")
                return self._mock_analysis(context)
            
            # Call LLM API
            response = self._call_llm_api(context)
            return self._process_llm_response(response)
        
        except Exception as e:
            self.logger.error(f"Error during LLM analysis: {str(e)}")
            return {
                "error": str(e),
                "summary": "LLM analysis failed. Please check the logs for more details."
            }
    
    def _call_llm_api(self, context: str) -> Dict[str, Any]:
        """Call the LLM API with the provided context"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a code review assistant that analyzes Pull Requests for Java Spring Boot microservices."},
                {"role": "user", "content": context}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        response = requests.post(self.api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()
    
    def _process_llm_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process the LLM API response"""
        content = response["choices"][0]["message"]["content"]
        
        return {
            "summary": self._extract_summary(content),
            "bugs": self._extract_section(content, "bugs", "issues"),
            "improvements": self._extract_section(content, "improvements"),
            "security": self._extract_section(content, "security"),
            "testing": self._extract_section(content, "testing"),
            "cross_repo": self._extract_section(content, "cross", "impact"),
            "full_analysis": content
        }
    
    def _extract_summary(self, content: str) -> str:
        """Extract summary from LLM response"""
        if "## Summary" in content:
            parts = content.split("## Summary")
            summary_section = parts[1].split("##")[0].strip()
            return summary_section
        return "No summary provided"
    
    def _extract_section(self, content: str, *section_keywords) -> str:
        """Extract a section from LLM response based on keywords"""
        lower_content = content.lower()
        
        for section in content.split("##"):
            section_title = section.split("\n")[0].lower()
            if any(keyword in section_title for keyword in section_keywords):
                return section.strip()
        
        return "No information provided"
    
    def _mock_analysis(self, context: str) -> Dict[str, Any]:
        """Generate a mock analysis when API key is not available"""
        return {
            "summary": "This Pull Request makes changes to the UserService class by adding a new method for user validation.",
            "bugs": "No obvious bugs identified, but consider adding null checks for the user parameter.",
            "improvements": "Consider using Optional<User> as the return type for better null handling.",
            "security": "Ensure proper input validation is performed to prevent injection attacks.",
            "testing": "Add unit tests for the new validation method with both valid and invalid inputs.",
            "cross_repo": "This change may impact the auth-service which depends on UserService.",
            "full_analysis": "Mock analysis - API key not provided"
        }
