import os
import yaml
import google.generativeai as genai
from typing import Dict, List, Any, Tuple
from dotenv import load_dotenv
import requests
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time

class CrossRepoAnalyzer:
    def __init__(self, github_client):
        self.github_client = github_client
        load_dotenv()
        
        # Configure Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Performance optimization settings - no file limits to avoid missing files
        self.max_file_size = 500000  # Increased to 500KB to avoid skipping important files
        self.file_cache = {}  # Cache file contents
        self.max_workers = 4  # Increased concurrent operations
        self.batch_size = 20  # Process files in batches
    
    def get_user_repositories(self, username: str) -> List[str]:
        """Get all repositories for a user"""
        try:
            user = self.github_client.get_user(username)
            repos = user.get_repos()
            return [repo.full_name for repo in repos if not repo.fork]
        except Exception as e:
            print(f"Error fetching repositories for {username}: {e}")
            return []
    
    def search_code_across_repos(self, query: str, username: str) -> List[Dict]:
        """Search for code patterns across repositories"""
        try:
            # Use GitHub's code search API
            search_results = self.github_client.search_code(
                f"{query} user:{username}",
                sort='indexed',
                order='desc'
            )
            
            results = []
            for item in search_results[:10]:  # Limit to first 10 results
                results.append({
                    'repo_name': item.repository.full_name,
                    'file_path': item.path,
                    'sha': item.sha,
                    'url': item.html_url,
                    'score': item.score
                })
            
            return results
        except Exception as e:
            print(f"Error searching code: {e}")
            return []
    
    def get_repository_files_optimized(self, repo_name: str) -> List[str]:
        """Get relevant files in a repository with optimizations"""
        try:
            repo = self.github_client.get_repo(repo_name)
            
            # Use search API to find specific file types instead of traversing all
            relevant_files = []
            
            # Search for specific file extensions to reduce API calls
            search_queries = [
                f"repo:{repo_name} extension:py",
                f"repo:{repo_name} extension:js",
                f"repo:{repo_name} extension:ts",
                f"repo:{repo_name} extension:java",
            ]
            
            for query in search_queries:
                try:
                    search_results = self.github_client.search_code(query)
                    for item in search_results[:self.max_files_per_repo // len(search_queries)]:
                        if item.path not in relevant_files:
                            relevant_files.append(item.path)
                except Exception as e:
                    print(f"Search query failed: {query}, error: {e}")
                    continue
            
            # Fallback to directory traversal if search fails (limited)
            if not relevant_files:
                relevant_files = self._get_files_by_traversal(repo, limit=self.max_files_per_repo)
            
            return relevant_files[:self.max_files_per_repo]
            
        except Exception as e:
            print(f"Error fetching repository structure for {repo_name}: {e}")
            return []
    
    def _get_files_by_traversal(self, repo, limit: int = 50) -> List[str]:
        """Fallback method to get files by directory traversal with limits"""
        files = []
        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php']
        
        try:
            contents = repo.get_contents("")
            
            def traverse_contents(contents_list, current_count=0):
                if current_count >= limit:
                    return current_count
                
                for content in contents_list:
                    if current_count >= limit:
                        break
                        
                    if content.type == "file":
                        if any(content.path.endswith(ext) for ext in code_extensions):
                            files.append(content.path)
                            current_count += 1
                    elif content.type == "dir" and current_count < limit:
                        try:
                            # Only traverse first level subdirectories to limit API calls
                            if content.path.count('/') < 2:
                                current_count = traverse_contents(repo.get_contents(content.path), current_count)
                        except Exception:
                            continue
                
                return current_count
            
            traverse_contents(contents)
        except Exception as e:
            print(f"Error in directory traversal: {e}")
        
        return files
    
    def get_file_content_from_repo_cached(self, repo_name: str, file_path: str) -> str:
        """Get file content with caching and size limits"""
        cache_key = f"{repo_name}/{file_path}"
        
        if cache_key in self.file_cache:
            return self.file_cache[cache_key]
        
        try:
            repo = self.github_client.get_repo(repo_name)
            file_content_obj = repo.get_contents(file_path)
            
            # Only skip extremely large files (>500KB) to avoid memory issues
            if file_content_obj.size > self.max_file_size:
                print(f"Large file detected: {file_path} ({file_content_obj.size} bytes) - processing anyway")
                # Still process but with truncation for analysis
                content = file_content_obj.decoded_content.decode('utf-8')[:self.max_file_size]
            else:
                content = file_content_obj.decoded_content.decode('utf-8')
            
            self.file_cache[cache_key] = content
            return content
            
        except Exception as e:
            print(f"Error fetching file content from {repo_name}/{file_path}: {e}")
            return ""
    
    def get_repository_files_smart(self, repo_name: str) -> Tuple[List[str], List[str]]:
        """Get all repository files with smart categorization (priority vs regular)"""
        try:
            repo = self.github_client.get_repo(repo_name)
            
            # Try search API first for efficiency, but get ALL files
            priority_files = []
            regular_files = []
            
            # Search for all code files by extension
            code_extensions = ['py', 'js', 'ts', 'java', 'cpp', 'c', 'h', 'go', 'rs', 'rb', 'php']
            
            for ext in code_extensions:
                try:
                    query = f"repo:{repo_name} extension:{ext}"
                    search_results = self.github_client.search_code(query)
                    
                    for item in search_results:
                        file_path = item.path
                        # Categorize files by importance for processing order
                        if self._is_priority_file(file_path):
                            if file_path not in priority_files:
                                priority_files.append(file_path)
                        else:
                            if file_path not in regular_files:
                                regular_files.append(file_path)
                                
                except Exception as e:
                    print(f"Search failed for extension {ext}: {e}")
                    continue
            
            # Fallback to directory traversal if search API fails or returns incomplete results
            if not priority_files and not regular_files:
                all_files = self._get_all_files_by_traversal(repo)
                for file_path in all_files:
                    if self._is_priority_file(file_path):
                        priority_files.append(file_path)
                    else:
                        regular_files.append(file_path)
            
            return priority_files, regular_files
            
        except Exception as e:
            print(f"Error fetching repository structure for {repo_name}: {e}")
            return [], []

    def _is_priority_file(self, file_path: str) -> bool:
        """Determine if a file should be processed with priority"""
        priority_patterns = [
            'index', 'main', 'app', 'server', 'client', 'api', 'service', 'controller',
            'config', 'setup', 'init', 'routes', 'middleware', 'auth', 'utils'
        ]
        
        file_name = os.path.basename(file_path).lower()
        return any(pattern in file_name for pattern in priority_patterns)

    def _get_all_files_by_traversal(self, repo) -> List[str]:
        """Get ALL code files by directory traversal - no limits"""
        files = []
        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php']
        
        try:
            contents = repo.get_contents("")
            
            def traverse_contents(contents_list):
                for content in contents_list:
                    try:
                        if content.type == "file":
                            if any(content.path.endswith(ext) for ext in code_extensions):
                                files.append(content.path)
                        elif content.type == "dir":
                            # Traverse all directories - no depth limit
                            traverse_contents(repo.get_contents(content.path))
                    except Exception as e:
                        print(f"Error accessing {content.path}: {e}")
                        continue
            
            traverse_contents(contents)
        except Exception as e:
            print(f"Error in directory traversal: {e}")
        
        return files
    
    def analyze_cross_repo_dependencies(self, source_repo_name: str, dependencies: List[Dict], 
                                      source_file_path: str, target_repo_names: List[str] = None) -> Dict[str, Any]:
        """Analyze dependencies across specific repositories with optimizations"""
        if not target_repo_names:
            target_repo_names = []
        
        cross_repo_impacts = {
            'analyzed_repos': target_repo_names,
            'cross_repo_dependencies': [],
            'affected_repositories': [],
            'summary': ''
        }
        
        # Add batch_size if not already defined
        if not hasattr(self, 'batch_size'):
            self.batch_size = 20
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all repository analysis tasks
            future_to_repo = {
                executor.submit(self._analyze_single_repo_comprehensive, source_repo_name, source_file_path, 
                              dependencies, target_repo): target_repo
                for target_repo in target_repo_names
                if target_repo != source_repo_name
            }
            
            # Collect results with longer timeout for comprehensive analysis
            for future in future_to_repo:
                try:
                    repo_impacts = future.result(timeout=120)  # Increased timeout to 2 minutes
                    if repo_impacts:
                        cross_repo_impacts['cross_repo_dependencies'].extend(repo_impacts)
                except Exception as e:
                    repo_name = future_to_repo[future]
                    print(f"Error analyzing repository {repo_name}: {e}")
        
        # Group by affected repositories
        affected_repos = {}
        for impact in cross_repo_impacts['cross_repo_dependencies']:
            repo = impact['affected_repo']
            if repo not in affected_repos:
                affected_repos[repo] = []
            affected_repos[repo].append(impact)
        
        cross_repo_impacts['affected_repositories'] = [
            {
                'repo_name': repo,
                'impact_count': len(impacts),
                'impacts': impacts
            }
            for repo, impacts in affected_repos.items()
        ]
        
        cross_repo_impacts['summary'] = self._generate_cross_repo_summary(cross_repo_impacts)
        
        return cross_repo_impacts
    
    def _analyze_single_repo_comprehensive(self, source_repo_name: str, source_file_path: str, 
                                         dependencies: List[Dict], target_repo_name: str) -> List[Dict]:
        """Comprehensively analyze a single repository without skipping files"""
        print(f"Comprehensive analysis of: {target_repo_name}")
        start_time = time.time()
        
        repo_impacts = []
        
        try:
            # Get ALL repository files categorized by priority
            priority_files, regular_files = self.get_repository_files_smart(target_repo_name)
            all_files = priority_files + regular_files
            
            print(f"Analyzing {len(all_files)} files in {target_repo_name} ({len(priority_files)} priority, {len(regular_files)} regular)")
            
            # Create dependency search patterns for efficient matching
            dependency_patterns = self._create_search_patterns(dependencies, source_repo_name, source_file_path)
            
            # Process files in batches for memory efficiency
            for i in range(0, len(all_files), self.batch_size):
                batch_files = all_files[i:i + self.batch_size]
                batch_impacts = self._process_file_batch(
                    target_repo_name, batch_files, dependency_patterns, 
                    source_repo_name, source_file_path, dependencies
                )
                repo_impacts.extend(batch_impacts)
                
                # Progress indicator
                if i % (self.batch_size * 5) == 0:
                    print(f"Processed {min(i + self.batch_size, len(all_files))}/{len(all_files)} files in {target_repo_name}")
            
            elapsed_time = time.time() - start_time
            print(f"Completed comprehensive analysis of {target_repo_name} in {elapsed_time:.2f} seconds - found {len(repo_impacts)} impacts")
            
        except Exception as e:
            print(f"Error in comprehensive analysis of {target_repo_name}: {e}")
        
        return repo_impacts
    
    def _create_search_patterns(self, dependencies: List[Dict], source_repo_name: str, source_file_path: str) -> Dict[str, List[str]]:
        """Create efficient search patterns for dependencies"""
        patterns = {}
        
        for dep in dependencies:
            dep_name = dep.get('name', '')
            dep_type = dep.get('type', '')
            
            if dep_name:
                search_patterns = []
                
                # Basic name patterns
                search_patterns.extend([
                    dep_name,
                    f'"{dep_name}"',
                    f"'{dep_name}'",
                    f"{dep_name}(",
                    f"{dep_name}.",
                    f"= {dep_name}",
                ])
                
                # Type-specific patterns
                if dep_type == 'route':
                    # Extract route path from name like "GET /users/:id/status"
                    if '/' in dep_name:
                        route_path = dep_name.split(' ')[-1] if ' ' in dep_name else dep_name
                        search_patterns.extend([
                            route_path,
                            f'"{route_path}"',
                            f"'{route_path}'",
                        ])
                elif dep_type == 'function':
                    search_patterns.extend([
                        f"@{dep_name}",
                        f"def {dep_name}",
                        f"function {dep_name}",
                        f"{dep_name} =>"
                    ])
                elif dep_type == 'class':
                    search_patterns.extend([
                        f"class {dep_name}",
                        f"new {dep_name}",
                        f"extends {dep_name}"
                    ])
                
                patterns[dep_name] = search_patterns
        
        return patterns
    
    def _process_file_batch(self, target_repo_name: str, file_paths: List[str], 
                          dependency_patterns: Dict[str, List[str]], source_repo_name: str,
                          source_file_path: str, dependencies: List[Dict]) -> List[Dict]:
        """Process a batch of files efficiently"""
        batch_impacts = []
        
        for file_path in file_paths:
            try:
                file_content = self.get_file_content_from_repo(target_repo_name, file_path)
                
                if file_content:
                    # Quick pattern matching first
                    potential_matches = []
                    
                    for dep_name, patterns in dependency_patterns.items():
                        if any(pattern in file_content for pattern in patterns):
                            # Find the actual dependency object
                            matching_dep = next((d for d in dependencies if d.get('name') == dep_name), None)
                            if matching_dep:
                                potential_matches.append(matching_dep)
                    
                    # Detailed analysis only for files with potential matches
                    if potential_matches:
                        for dependency in potential_matches:
                            impact_analysis = self._analyze_cross_repo_impact(
                                source_repo_name, target_repo_name, file_path,
                                file_content, dependency, source_file_path
                            )
                            
                            if impact_analysis:
                                batch_impacts.append(impact_analysis)
                                
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                continue
        
        return batch_impacts
    
    def get_file_content_from_repo(self, repo_name: str, file_path: str) -> str:
        """Get file content from a specific repository"""
        try:
            repo = self.github_client.get_repo(repo_name)
            file_content = repo.get_contents(file_path)
            return file_content.decoded_content.decode('utf-8')
        except Exception as e:
            print(f"Error fetching file content from {repo_name}/{file_path}: {e}")
            return ""
    
    def get_repository_files(self, repo_name: str) -> List[str]:
        """Get all files in a specific repository"""
        try:
            repo = self.github_client.get_repo(repo_name)
            contents = repo.get_contents("")
            files = []
            
            def traverse_contents(contents_list):
                for content in contents_list:
                    if content.type == "file":
                        files.append(content.path)
                    elif content.type == "dir":
                        try:
                            traverse_contents(repo.get_contents(content.path))
                        except Exception as e:
                            print(f"Error accessing directory {content.path}: {e}")
            
            traverse_contents(contents)
            return files
        except Exception as e:
            print(f"Error fetching repository structure for {repo_name}: {e}")
            return []
    
    def _check_file_uses_dependency_cross_repo(self, file_content: str, source_repo_name: str, 
                                              source_file_path: str, dependency_name: str, 
                                              dependency_type: str) -> bool:
        """Check if a file potentially uses a dependency from another repository"""
        # Check for direct usage of dependency name
        usage_patterns = [
            f"{dependency_name}(",
            f"{dependency_name}.",
            f"= {dependency_name}",
            f"@{dependency_name}",
            f'"{dependency_name}"',
            f"'{dependency_name}'",
        ]
        
        # Check for imports that might reference the source repository/module
        source_module_patterns = [
            source_repo_name.split('/')[-1],  # Repository name
            os.path.basename(source_file_path).split('.')[0],  # File name without extension
        ]
        
        import_patterns = []
        for module in source_module_patterns:
            import_patterns.extend([
                f"from {module}",
                f"import {module}",
                f"require('{module}')",
                f'require("{module}")',
            ])
        
        for pattern in usage_patterns + import_patterns:
            if pattern in file_content:
                return True
        
        return False
    
    def _analyze_cross_repo_impact(self, source_repo: str, target_repo: str, target_file: str,
                                  target_content: str, dependency: Dict, source_file: str) -> Dict[str, Any]:
        """Analyze impact of changes on a specific file in another repository"""
        
        prompt = f"""
        Analyze the cross-repository impact of a code change on another repository:

        SOURCE REPOSITORY: {source_repo}
        SOURCE FILE: {source_file}
        CHANGED DEPENDENCY: {dependency}
        
        TARGET REPOSITORY: {target_repo}
        TARGET FILE: {target_file}
        
        TARGET FILE CONTENT:
        ```
        {target_content[:2500]}
        ```
        
        Please analyze:
        1. **Usage Patterns**: How is the changed dependency used in the target file?
        2. **Impact Assessment**: What specific parts of the target file will be affected?
        3. **Required Changes**: What changes are needed in the target repository?
        4. **Risk Level**: Assess the risk (LOW|MEDIUM|HIGH|CRITICAL)
        
        Focus on:
        - Import statements using the dependency
        - Function/method calls to the dependency
        - Class instantiations or inheritance
        - Variable assignments or references
        - Configuration or setup code
        
        Respond in JSON format:
        {{
            "has_impact": true/false,
            "usage_patterns": [
                {{
                    "line_context": "relevant line or section",
                    "usage_type": "import|function_call|class_usage|variable_reference|other",
                    "specific_code": "exact code using the dependency"
                }}
            ],
            "impact_details": {{
                "affected_lines": "line numbers or sections affected",
                "impact_description": "description of the impact",
                "breaking_change": true/false,
                "risk_level": "LOW|MEDIUM|HIGH|CRITICAL"
            }},
            "required_changes": [
                {{
                    "change_type": "import|function_call|class_usage|configuration|other",
                    "current_code": "current code that needs changing",
                    "suggested_fix": "suggested fix or update",
                    "reason": "why this change is needed"
                }}
            ],
            "summary": "brief summary of cross-repo impact"
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
            
            # Only return if there's actual impact
            if analysis.get('has_impact', False):
                analysis['affected_repo'] = target_repo
                analysis['affected_file'] = target_file
                analysis['source_dependency'] = dependency
                return analysis
            
            return None
            
        except Exception as e:
            print(f"Error analyzing cross-repo impact: {e}")
            return None
    
    def _generate_cross_repo_summary(self, cross_repo_impacts: Dict) -> str:
        """Generate summary of cross-repository impacts"""
        total_impacts = len(cross_repo_impacts['cross_repo_dependencies'])
        affected_repos_count = len(cross_repo_impacts['affected_repositories'])
        
        if total_impacts == 0:
            return "No cross-repository dependencies found."
        
        return f"Found {total_impacts} cross-repository impacts across {affected_repos_count} repositories."
    
    def save_cross_repo_analysis(self, analysis_results: Dict[str, Any], output_path: str):
        """Save cross-repository analysis results to YAML file"""
        with open(output_path, 'w', encoding='utf-8') as file:
            yaml.dump(analysis_results, file, default_flow_style=False, indent=2, allow_unicode=True)
        
        print(f"Cross-repository analysis saved to {output_path}")
