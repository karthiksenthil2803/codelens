import os
import json
import time
import hashlib
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed

class RepositoryCache:
    """Cache repository files locally to avoid GitHub API rate limits"""
    
    def __init__(self, github_client, cache_dir: str = "src/cache/repositories"):
        self.github_client = github_client
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache configuration
        self.max_file_size = 1000000  # 1MB max file size
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.max_workers = 3  # Conservative to avoid rate limits
        self.code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.go', '.rs', '.rb', '.php', '.json', '.yaml', '.yml', '.md']
        
        # Rate limiting
        self.api_calls_count = 0
        self.api_calls_start_time = time.time()
        self.max_api_calls_per_hour = 4000  # Conservative limit
        
    def _get_repo_cache_dir(self, repo_name: str) -> Path:
        """Get cache directory for a specific repository"""
        safe_repo_name = repo_name.replace('/', '_')
        return self.cache_dir / safe_repo_name
    
    def _get_cache_metadata_path(self, repo_name: str) -> Path:
        """Get path to cache metadata file"""
        return self._get_repo_cache_dir(repo_name) / "cache_metadata.json"
    
    def _is_cache_valid(self, repo_name: str) -> bool:
        """Check if cache is still valid based on TTL"""
        metadata_path = self._get_cache_metadata_path(repo_name)
        if not metadata_path.exists():
            return False
        
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            cache_time = metadata.get('cache_time', 0)
            return (time.time() - cache_time) < self.cache_ttl
        except Exception:
            return False
    
    def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        
        # Reset counter every hour
        if current_time - self.api_calls_start_time > 3600:
            self.api_calls_count = 0
            self.api_calls_start_time = current_time
        
        # Check if we're approaching rate limit
        if self.api_calls_count >= self.max_api_calls_per_hour:
            sleep_time = 3600 - (current_time - self.api_calls_start_time)
            if sleep_time > 0:
                print(f"Rate limit reached. Sleeping for {sleep_time:.0f} seconds...")
                time.sleep(sleep_time)
                self.api_calls_count = 0
                self.api_calls_start_time = time.time()
    
    def _safe_api_call(self, func, *args, **kwargs):
        """Make a safe API call with rate limiting"""
        self._check_rate_limit()
        self.api_calls_count += 1
        return func(*args, **kwargs)
    
    def download_repository_files(self, repo_name: str, force_refresh: bool = False) -> Dict[str, str]:
        """Download and cache all relevant files from a repository"""
        if not force_refresh and self._is_cache_valid(repo_name):
            print(f"Using cached files for {repo_name}")
            return self.load_cached_files(repo_name)
        
        print(f"Downloading files from {repo_name}...")
        repo_cache_dir = self._get_repo_cache_dir(repo_name)
        repo_cache_dir.mkdir(parents=True, exist_ok=True)
        
        cached_files = {}
        
        try:
            repo = self._safe_api_call(self.github_client.get_repo, repo_name)
            
            # Get all files using search API to minimize rate limit impact
            all_files = self._get_repository_files_efficiently(repo_name)
            
            print(f"Found {len(all_files)} files to cache in {repo_name}")
            
            # Download files in batches to respect rate limits
            batch_size = 10
            total_downloaded = 0
            
            for i in range(0, len(all_files), batch_size):
                batch_files = all_files[i:i + batch_size]
                
                for file_path in batch_files:
                    try:
                        content = self._download_single_file(repo, file_path)
                        if content:
                            cached_files[file_path] = content
                            self._save_file_to_cache(repo_name, file_path, content)
                            total_downloaded += 1
                        
                        # Small delay between files to be nice to the API
                        time.sleep(0.1)
                        
                    except Exception as e:
                        print(f"Error downloading {file_path}: {e}")
                        continue
                
                print(f"Downloaded {total_downloaded}/{len(all_files)} files from {repo_name}")
                
                # Longer pause between batches
                if i + batch_size < len(all_files):
                    time.sleep(1)
            
            # Save cache metadata
            self._save_cache_metadata(repo_name, {
                'cache_time': time.time(),
                'total_files': len(cached_files),
                'repo_name': repo_name
            })
            
            print(f"Successfully cached {len(cached_files)} files from {repo_name}")
            
        except Exception as e:
            print(f"Error downloading repository {repo_name}: {e}")
            # Try to load existing cache if available
            cached_files = self.load_cached_files(repo_name)
        
        return cached_files
    
    def _get_repository_files_efficiently(self, repo_name: str) -> List[str]:
        """Get repository files using efficient methods to minimize API calls"""
        files = []
        
        try:
            # Use search API for each extension to get files efficiently
            for ext in self.code_extensions:
                try:
                    query = f"repo:{repo_name} extension:{ext.lstrip('.')}"
                    search_results = self._safe_api_call(self.github_client.search_code, query)
                    
                    for item in search_results:
                        if item.path not in files:
                            files.append(item.path)
                    
                    # Small delay between searches
                    time.sleep(0.2)
                    
                except Exception as e:
                    print(f"Search failed for extension {ext}: {e}")
                    continue
            
            # Fallback to tree API if search didn't return enough files
            if len(files) < 10:  # Threshold for fallback
                tree_files = self._get_files_from_git_tree(repo_name)
                for file_path in tree_files:
                    if file_path not in files:
                        files.append(file_path)
        
        except Exception as e:
            print(f"Error getting repository files for {repo_name}: {e}")
        
        return files
    
    def _get_files_from_git_tree(self, repo_name: str) -> List[str]:
        """Get files using Git tree API as fallback"""
        files = []
        
        try:
            repo = self._safe_api_call(self.github_client.get_repo, repo_name)
            
            # Get default branch
            default_branch = repo.default_branch
            
            # Get git tree recursively
            tree = self._safe_api_call(repo.get_git_tree, default_branch, recursive=True)
            
            for item in tree.tree:
                if item.type == 'blob':  # It's a file
                    file_path = item.path
                    if any(file_path.endswith(ext) for ext in self.code_extensions):
                        files.append(file_path)
        
        except Exception as e:
            print(f"Error getting git tree for {repo_name}: {e}")
        
        return files
    
    def _download_single_file(self, repo, file_path: str) -> Optional[str]:
        """Download a single file with size and encoding checks"""
        try:
            file_content_obj = self._safe_api_call(repo.get_contents, file_path)
            
            # Skip if file is too large
            if file_content_obj.size > self.max_file_size:
                print(f"Skipping large file: {file_path} ({file_content_obj.size} bytes)")
                return None
            
            # Decode content
            content = file_content_obj.decoded_content.decode('utf-8')
            return content
            
        except UnicodeDecodeError:
            print(f"Skipping binary file: {file_path}")
            return None
        except Exception as e:
            print(f"Error downloading {file_path}: {e}")
            return None
    
    def _save_file_to_cache(self, repo_name: str, file_path: str, content: str):
        """Save a file to the cache directory"""
        cache_file_path = self._get_repo_cache_dir(repo_name) / f"{file_path.replace('/', '_')}"
        
        try:
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error saving cached file {file_path}: {e}")
    
    def _save_cache_metadata(self, repo_name: str, metadata: Dict):
        """Save cache metadata"""
        metadata_path = self._get_cache_metadata_path(repo_name)
        
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving cache metadata: {e}")
    
    def load_cached_files(self, repo_name: str) -> Dict[str, str]:
        """Load cached files for a repository"""
        cached_files = {}
        repo_cache_dir = self._get_repo_cache_dir(repo_name)
        
        if not repo_cache_dir.exists():
            return cached_files
        
        try:
            for cache_file in repo_cache_dir.iterdir():
                if cache_file.is_file() and cache_file.name != "cache_metadata.json":
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Convert cached filename back to original path
                        original_path = cache_file.name.replace('_', '/')
                        cached_files[original_path] = content
                        
                    except Exception as e:
                        print(f"Error loading cached file {cache_file}: {e}")
                        continue
        
        except Exception as e:
            print(f"Error loading cached files for {repo_name}: {e}")
        
        return cached_files
    
    def get_cached_file_content(self, repo_name: str, file_path: str) -> Optional[str]:
        """Get content of a specific cached file"""
        cached_files = self.load_cached_files(repo_name)
        return cached_files.get(file_path)
    
    def clear_cache(self, repo_name: str = None):
        """Clear cache for a specific repository or all repositories"""
        if repo_name:
            repo_cache_dir = self._get_repo_cache_dir(repo_name)
            if repo_cache_dir.exists():
                import shutil
                shutil.rmtree(repo_cache_dir)
                print(f"Cleared cache for {repo_name}")
        else:
            if self.cache_dir.exists():
                import shutil
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                print("Cleared all repository cache")
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics"""
        stats = {
            'total_repositories': 0,
            'total_files': 0,
            'total_size_mb': 0,
            'repositories': []
        }
        
        if not self.cache_dir.exists():
            return stats
        
        for repo_dir in self.cache_dir.iterdir():
            if repo_dir.is_dir():
                repo_stats = {
                    'repo_name': repo_dir.name,
                    'file_count': 0,
                    'size_mb': 0,
                    'cache_valid': False
                }
                
                # Count files and calculate size
                for file_path in repo_dir.iterdir():
                    if file_path.is_file():
                        repo_stats['file_count'] += 1
                        repo_stats['size_mb'] += file_path.stat().st_size / (1024 * 1024)
                
                # Check if cache is valid
                repo_name = repo_dir.name.replace('_', '/')
                repo_stats['cache_valid'] = self._is_cache_valid(repo_name)
                
                stats['repositories'].append(repo_stats)
                stats['total_repositories'] += 1
                stats['total_files'] += repo_stats['file_count']
                stats['total_size_mb'] += repo_stats['size_mb']
        
        return stats
    
    def bulk_download_repositories(self, repo_names: List[str], force_refresh: bool = False) -> Dict[str, Dict[str, str]]:
        """Download multiple repositories efficiently"""
        all_cached_files = {}
        
        print(f"Starting bulk download of {len(repo_names)} repositories...")
        
        # Use ThreadPoolExecutor with conservative worker count
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_repo = {
                executor.submit(self.download_repository_files, repo_name, force_refresh): repo_name
                for repo_name in repo_names
            }
            
            for future in as_completed(future_to_repo):
                repo_name = future_to_repo[future]
                try:
                    cached_files = future.result(timeout=300)  # 5 minute timeout per repo
                    all_cached_files[repo_name] = cached_files
                    print(f"Completed caching {repo_name}")
                except Exception as e:
                    print(f"Failed to cache {repo_name}: {e}")
                    all_cached_files[repo_name] = {}
        
        print(f"Bulk download completed. Cached {len(all_cached_files)} repositories.")
        return all_cached_files
