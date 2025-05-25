import os
import yaml
import google.generativeai as genai
from typing import Dict, List, Any
from dotenv import load_dotenv

class DependencyAnalyzer:
    def __init__(self, github_client):
        self.github_client = github_client
        load_dotenv()
        
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def get_file_content(self, repo_name: str, file_path: str, ref: str = None) -> str:
        """Get the current content of a file from GitHub repository"""
        try:
            repo = self.github_client.get_repo(repo_name)
            if ref:
                file_content = repo.get_contents(file_path, ref=ref)
            else:
                file_content = repo.get_contents(file_path)
            
            return file_content.decoded_content.decode('utf-8')
        except Exception as e:
            print(f"Error fetching file content for {file_path}: {e}")
            return ""
    
    def get_repository_structure(self, repo_name: str) -> List[str]:
        """Get a list of all files in the repository"""
        try:
            repo = self.github_client.get_repo(repo_name)
            contents = repo.get_contents("")
            files = []
            
            def traverse_contents(contents_list):
                for content in contents_list:
                    if content.type == "file":
                        files.append(content.path)
                    elif content.type == "dir":
                        traverse_contents(repo.get_contents(content.path))
            
            traverse_contents(contents)
            return files
        except Exception as e:
            print(f"Error fetching repository structure: {e}")
            return []
    
    def analyze_dependencies(self, repo_name: str, yaml_file_path: str) -> Dict[str, Any]:
        """Analyze dependencies from YAML file containing patch data"""
        # Load YAML data
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        file_data = data['file_changed']
        file_path = file_data['file_path']
        changes = file_data['changes']
        
        # Get current file content
        current_content = self.get_file_content(repo_name, file_path)
        
        # Get repository structure
        repo_files = self.get_repository_structure(repo_name)
        
        # Analyze each change
        analysis_results = {
            'file_path': file_path,
            'dependencies_found': [],
            'potential_impacts': [],
            'analysis_summary': ''
        }
        
        for change in changes:
            patch = change.get('patch', '')
            if patch:
                dependency_analysis = self._analyze_patch_with_gemini(
                    file_path, current_content, patch, repo_files, change['status']
                )
                analysis_results['dependencies_found'].extend(dependency_analysis.get('dependencies', []))
                analysis_results['potential_impacts'].extend(dependency_analysis.get('impacts', []))
        
        # Generate overall summary
        analysis_results['analysis_summary'] = self._generate_summary(analysis_results)
        
        return analysis_results
    
    def _analyze_patch_with_gemini(self, file_path: str, file_content: str, 
                                  patch: str, repo_files: List[str], status: str) -> Dict[str, Any]:
        """Use Gemini to analyze patch for dependencies"""
        
        prompt = f"""
        Analyze the following code patch for a file in a software repository to identify dependencies and potential impacts:

        FILE PATH: {file_path}
        CHANGE STATUS: {status}
        
        CURRENT FILE CONTENT:
        ```
        {file_content[:3000]}  # Truncate for token limits
        ```
        
        PATCH CHANGES:
        ```
        {patch}
        ```
        
        REPOSITORY FILES (sample):
        {repo_files[:50]}  # Show first 50 files for context
        
        Please analyze and provide:
        1. **Dependencies**: List any classes, functions, variables, decorators, imports, or modules that are:
           - Added, modified, or removed in this patch
           - Might be used by other files in the repository
           - Could affect the API or interface of this file
        
        2. **Potential Impacts**: Identify files or components that might be affected by these changes:
           - Files that might import from this file
           - Files that might call functions/classes modified here
           - Test files that might need updates
           - Configuration files that might reference these changes
        
        3. **Risk Level**: Assess the risk level (LOW, MEDIUM, HIGH) based on:
           - How widely used the changed components might be
           - Whether the changes are breaking or backwards compatible
           - The type of changes (additions vs modifications vs deletions)
        
        Respond in JSON format:
        {{
            "dependencies": [
                {{
                    "name": "function/class/variable name",
                    "type": "function|class|variable|decorator|import|module",
                    "action": "added|modified|removed",
                    "description": "brief description of the dependency"
                }}
            ],
            "impacts": [
                {{
                    "affected_component": "description of what might be affected",
                    "risk_level": "LOW|MEDIUM|HIGH",
                    "reason": "explanation of why this might be impacted"
                }}
            ],
            "overall_risk": "LOW|MEDIUM|HIGH",
            "summary": "brief summary of the analysis"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text
            
            import json
            return json.loads(json_text)
            
        except Exception as e:
            print(f"Error analyzing with Gemini: {e}")
            return {
                "dependencies": [],
                "impacts": [],
                "overall_risk": "UNKNOWN",
                "summary": f"Analysis failed: {str(e)}"
            }
    
    def _generate_summary(self, analysis_results: Dict[str, Any]) -> str:
        """Generate a summary of the analysis"""
        dependencies_count = len(analysis_results['dependencies_found'])
        impacts_count = len(analysis_results['potential_impacts'])
        
        return f"Found {dependencies_count} dependencies and {impacts_count} potential impacts for {analysis_results['file_path']}"
    
    def save_analysis(self, analysis_results: Dict[str, Any], output_path: str):
        """Save analysis results to YAML file"""
        with open(output_path, 'w', encoding='utf-8') as file:
            yaml.dump(analysis_results, file, default_flow_style=False, indent=2, allow_unicode=True)
        
        print(f"Dependency analysis saved to {output_path}")
