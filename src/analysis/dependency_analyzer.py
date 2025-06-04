import os
import yaml
import google.generativeai as genai
from typing import Dict, List, Any, Tuple
from dotenv import load_dotenv
import re
from src.analysis.cross_repo_analyzer import CrossRepoAnalyzer
import time

class DependencyAnalyzer:
    def __init__(self, github_client):
        self.github_client = github_client
        self.cross_repo_analyzer = CrossRepoAnalyzer(github_client)
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
    
    def find_potential_affected_files(self, repo_name: str, changed_file_path: str, dependencies: List[Dict]) -> List[Tuple[str, str]]:
        """Find files that potentially use the changed dependencies"""
        repo_files = self.get_repository_structure(repo_name)
        potentially_affected = []
        
        # Filter relevant files (exclude non-code files)
        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php']
        relevant_files = [f for f in repo_files if any(f.endswith(ext) for ext in code_extensions)]
        
        for file_path in relevant_files:
            if file_path == changed_file_path:
                continue
                
            file_content = self.get_file_content(repo_name, file_path)
            if file_content:
                # Check if this file might be affected by analyzing imports and usage
                for dependency in dependencies:
                    dep_name = dependency.get('name', '')
                    if self._check_file_uses_dependency(file_content, changed_file_path, dep_name):
                        potentially_affected.append((file_path, file_content))
                        break
        
        return potentially_affected
    
    def _check_file_uses_dependency(self, file_content: str, changed_file_path: str, dependency_name: str) -> bool:
        """Check if a file potentially uses a dependency from the changed file"""
        # Check for imports from the changed file
        module_name = changed_file_path.replace('/', '.').replace('.py', '').replace('.js', '').replace('.ts', '')
        
        import_patterns = [
            f"from {module_name} import",
            f"import {module_name}",
            f"from .{os.path.basename(changed_file_path).split('.')[0]} import",
            f"import .{os.path.basename(changed_file_path).split('.')[0]}",
            f"require('{module_name}')",
            f'require("{module_name}")',
        ]
        
        # Check for direct usage of dependency name
        usage_patterns = [
            f"{dependency_name}(",
            f"{dependency_name}.",
            f"= {dependency_name}",
            f"@{dependency_name}",
        ]
        
        for pattern in import_patterns + usage_patterns:
            if pattern in file_content:
                return True
        
        return False
    
    def analyze_dependencies(self, repo_name: str, yaml_file_path: str, 
                           cross_repo_targets: List[str] = None) -> Dict[str, Any]:
        """Analyze dependencies from YAML file containing patch data"""
        # Load YAML data
        with open(yaml_file_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        file_data = data['file_changed']
        file_path = file_data['file_path']
        changes = file_data['changes']
        
        # Get current file content
        current_content = self.get_file_content(repo_name, file_path)
        
        # Analyze each change
        analysis_results = {
            'file_path': file_path,
            'dependencies_found': [],
            'potential_impacts': [],
            'specific_changes_needed': [],
            'analysis_summary': ''
        }
        
        for change in changes:
            patch = change.get('patch', '')
            if patch:
                dependency_analysis = self._analyze_patch_with_gemini(
                    file_path, current_content, patch, change['status']
                )
                analysis_results['dependencies_found'].extend(dependency_analysis.get('dependencies', []))
                analysis_results['potential_impacts'].extend(dependency_analysis.get('impacts', []))
        
        # Find affected files and analyze specific changes needed
        if analysis_results['dependencies_found']:
            affected_files = self.find_potential_affected_files(
                repo_name, file_path, analysis_results['dependencies_found']
            )
            
            for affected_file_path, affected_file_content in affected_files:
                specific_changes = self._analyze_specific_changes_needed(
                    file_path, affected_file_path, affected_file_content, 
                    analysis_results['dependencies_found'], changes
                )
                analysis_results['specific_changes_needed'].extend(specific_changes)
            
            # Analyze cross-repository impacts comprehensively
            if cross_repo_targets:
                print(f"Starting comprehensive cross-repository analysis for {len(cross_repo_targets)} repositories...")
                print(f"Found {len(analysis_results['dependencies_found'])} dependencies to analyze")
                start_time = time.time()
                
                try:
                    cross_repo_analysis = self.cross_repo_analyzer.analyze_cross_repo_dependencies(
                        repo_name, analysis_results['dependencies_found'], file_path, cross_repo_targets
                    )
                    analysis_results['cross_repository_impacts'] = cross_repo_analysis
                    
                    elapsed_time = time.time() - start_time
                    impact_count = len(cross_repo_analysis.get('cross_repo_dependencies', []))
                    print(f"Comprehensive cross-repository analysis completed in {elapsed_time:.2f} seconds")
                    print(f"Found {impact_count} cross-repository impacts")
                    
                except Exception as e:
                    print(f"Cross-repository analysis failed: {e}")
                    analysis_results['cross_repository_impacts'] = {
                        'analyzed_repos': cross_repo_targets,
                        'cross_repo_dependencies': [],
                        'affected_repositories': [],
                        'summary': f'Cross-repository analysis failed: {str(e)}'
                    }
            else:
                analysis_results['cross_repository_impacts'] = {
                    'analyzed_repos': [],
                    'cross_repo_dependencies': [],
                    'affected_repositories': [],
                    'summary': 'No target repositories specified for cross-repository analysis.'
                }
        else:
            analysis_results['cross_repository_impacts'] = {
                'analyzed_repos': [],
                'cross_repo_dependencies': [],
                'affected_repositories': [],
                'summary': 'No dependencies found to analyze cross-repository impacts.'
            }
        
        # Generate overall summary
        analysis_results['analysis_summary'] = self._generate_summary(analysis_results)
        
        return analysis_results
    
    def _analyze_patch_with_gemini(self, file_path: str, file_content: str, 
                                  patch: str, status: str) -> Dict[str, Any]:
        """Use Gemini to analyze patch for dependencies"""
        
        prompt = f"""
        Analyze the following code patch to identify specific dependencies that changed:

        FILE PATH: {file_path}
        CHANGE STATUS: {status}
        
        CURRENT FILE CONTENT:
        ```
        {file_content[:2000]}
        ```
        
        PATCH CHANGES:
        ```
        {patch}
        ```
        
        Please identify EXACTLY what changed and provide:
        1. **Dependencies**: List specific functions, classes, variables, methods, or imports that were:
           - Added (new items)
           - Modified (signature changes, renamed, behavior changes)
           - Removed (deleted items)
        
        2. **Change Details**: For each dependency, specify:
           - Exact name and type
           - What specifically changed (parameters, return type, behavior)
           - Whether it's a breaking change
        
        Respond in JSON format:
        {{
            "dependencies": [
                {{
                    "name": "exact_function_or_class_name",
                    "type": "function|class|variable|method|import|decorator",
                    "action": "added|modified|removed",
                    "details": "specific details of what changed",
                    "breaking_change": true/false,
                    "old_signature": "previous signature if modified",
                    "new_signature": "new signature if modified"
                }}
            ],
            "impacts": [
                {{
                    "affected_component": "what might be affected",
                    "risk_level": "LOW|MEDIUM|HIGH",
                    "reason": "why this might be impacted"
                }}
            ]
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
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
            return {"dependencies": [], "impacts": []}
    
    def _analyze_specific_changes_needed(self, changed_file_path: str, affected_file_path: str, 
                                       affected_file_content: str, dependencies: List[Dict], 
                                       changes: List[Dict]) -> List[Dict]:
        """Analyze what specific changes are needed in affected files"""
        
        # Get the patches for context
        patches = [change.get('patch', '') for change in changes if change.get('patch')]
        combined_patches = '\n'.join(patches)
        
        prompt = f"""
        Analyze what specific code changes are needed in an affected file due to changes in another file:

        CHANGED FILE: {changed_file_path}
        AFFECTED FILE: {affected_file_path}
        
        CHANGES MADE (patches):
        ```
        {combined_patches[:2000]}
        ```
        
        DEPENDENCIES IDENTIFIED:
        {yaml.dump(dependencies, default_flow_style=False)}
        
        AFFECTED FILE CONTENT:
        ```
        {affected_file_content[:3000]}
        ```
        
        Please analyze and identify:
        1. **Specific Lines/Sections** in the affected file that need changes
        2. **Exact Changes Required** (what to modify, add, or remove)
        3. **Code Examples** of the required changes
        4. **Reason** why each change is necessary
        
        Focus on:
        - Import statements that need updating
        - Function/method calls that need parameter changes
        - Class instantiations that need modification
        - Variable assignments that need updates
        - Error handling that might be affected
        
        Respond in JSON format:
        {{
            "changes_needed": [
                {{
                    "line_numbers": "approximate line numbers or 'imports section'",
                    "current_code": "current code that needs changing",
                    "required_change": "what needs to be changed",
                    "new_code_example": "example of corrected code",
                    "reason": "why this change is necessary",
                    "change_type": "import|function_call|class_usage|variable|error_handling|other",
                    "priority": "HIGH|MEDIUM|LOW"
                }}
            ],
            "summary": "overall summary of changes needed in this file"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text
            
            import json
            analysis = json.loads(json_text)
            
            # Add file path to each change
            for change in analysis.get('changes_needed', []):
                change['affected_file'] = affected_file_path
            
            return analysis.get('changes_needed', [])
            
        except Exception as e:
            print(f"Error analyzing specific changes with Gemini: {e}")
            return []
    
    def _generate_summary(self, analysis_results: Dict[str, Any]) -> str:
        """Generate a summary of the analysis"""
        dependencies_count = len(analysis_results['dependencies_found'])
        impacts_count = len(analysis_results['potential_impacts'])
        changes_count = len(analysis_results['specific_changes_needed'])
        cross_repo_count = len(analysis_results.get('cross_repository_impacts', {}).get('cross_repo_dependencies', []))
        
        summary = f"Found {dependencies_count} dependencies, {impacts_count} potential impacts, and {changes_count} specific changes needed"
        
        if cross_repo_count > 0:
            summary += f", with {cross_repo_count} cross-repository impacts"
        
        summary += f" for {analysis_results['file_path']}"
        
        return summary
    
    def save_analysis(self, analysis_results: Dict[str, Any], output_path: str):
        """Save analysis results to YAML file"""
        with open(output_path, 'w', encoding='utf-8') as file:
            yaml.dump(analysis_results, file, default_flow_style=False, indent=2, allow_unicode=True)
        
        print(f"Dependency analysis saved to {output_path}")
