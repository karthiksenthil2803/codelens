import os
import argparse
import time
from pathlib import Path
from typing import List, Optional
from src.cache.repository_cache import RepositoryCache
from github import Github
from dotenv import load_dotenv

class CacheManager:
    """Utility class for managing repository cache"""
    
    def __init__(self):
        load_dotenv()
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN not found in environment variables")
        
        self.github_client = Github(github_token)
        self.cache = RepositoryCache(self.github_client)
    
    def cache_repositories(self, repo_names: List[str], force_refresh: bool = False):
        """Cache multiple repositories"""
        print(f"Caching {len(repo_names)} repositories...")
        
        start_time = time.time()
        results = self.cache.bulk_download_repositories(repo_names, force_refresh)
        elapsed_time = time.time() - start_time
        
        print(f"\nCaching completed in {elapsed_time:.2f} seconds")
        print(f"Successfully cached {len(results)} repositories")
        
        # Show individual results
        for repo_name, files in results.items():
            print(f"  {repo_name}: {len(files)} files")
    
    def show_cache_stats(self):
        """Display cache statistics"""
        stats = self.cache.get_cache_stats()
        
        print("Repository Cache Statistics")
        print("=" * 40)
        print(f"Total Repositories: {stats['total_repositories']}")
        print(f"Total Files: {stats['total_files']}")
        print(f"Total Size: {stats['total_size_mb']:.2f} MB")
        print()
        
        if stats['repositories']:
            print("Repository Details:")
            print("-" * 60)
            print(f"{'Repository':<30} {'Files':<8} {'Size (MB)':<10} {'Valid':<8}")
            print("-" * 60)
            
            for repo in stats['repositories']:
                print(f"{repo['repo_name']:<30} {repo['file_count']:<8} {repo['size_mb']:<10.2f} {repo['cache_valid']:<8}")
    
    def clear_cache(self, repo_name: Optional[str] = None):
        """Clear cache for specific repository or all"""
        if repo_name:
            self.cache.clear_cache(repo_name)
            print(f"Cleared cache for {repo_name}")
        else:
            self.cache.clear_cache()
            print("Cleared all cache")
    
    def refresh_cache(self, repo_names: List[str]):
        """Refresh cache for specific repositories"""
        print(f"Refreshing cache for {len(repo_names)} repositories...")
        self.cache_repositories(repo_names, force_refresh=True)
    
    def validate_cache(self) -> List[str]:
        """Validate cache and return list of invalid repositories"""
        stats = self.cache.get_cache_stats()
        invalid_repos = []
        
        for repo in stats['repositories']:
            if not repo['cache_valid']:
                invalid_repos.append(repo['repo_name'].replace('_', '/'))
        
        if invalid_repos:
            print(f"Found {len(invalid_repos)} repositories with invalid cache:")
            for repo in invalid_repos:
                print(f"  - {repo}")
        else:
            print("All cached repositories are valid")
        
        return invalid_repos

def main():
    """CLI interface for cache management"""
    parser = argparse.ArgumentParser(description="Manage repository cache")
    parser.add_argument('command', choices=['cache', 'stats', 'clear', 'refresh', 'validate'],
                       help='Command to execute')
    parser.add_argument('--repos', nargs='+', help='Repository names (format: owner/repo)')
    parser.add_argument('--repo', help='Single repository name for clear command')
    parser.add_argument('--force', action='store_true', help='Force refresh cache')
    
    args = parser.parse_args()
    
    try:
        cache_manager = CacheManager()
        
        if args.command == 'cache':
            if not args.repos:
                print("Error: --repos required for cache command")
                return
            cache_manager.cache_repositories(args.repos, args.force)
        
        elif args.command == 'stats':
            cache_manager.show_cache_stats()
        
        elif args.command == 'clear':
            cache_manager.clear_cache(args.repo)
        
        elif args.command == 'refresh':
            if not args.repos:
                print("Error: --repos required for refresh command")
                return
            cache_manager.refresh_cache(args.repos)
        
        elif args.command == 'validate':
            invalid_repos = cache_manager.validate_cache()
            if invalid_repos and input("Refresh invalid repositories? (y/n): ").lower() == 'y':
                cache_manager.refresh_cache(invalid_repos)
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
