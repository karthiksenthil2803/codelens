import os
from pathlib import Path
import yaml

class PRReader:
    def __init__(self, github_client):
        self.github_client = github_client

    def read_commits(self, repo_name, pr_number):
        repo = self.github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        return [commit for commit in pr.get_commits()]

    def save_commits_to_folder(self, repo_name, pr_number, commit_data):
        base_folder_name = f"{repo_name.replace('/', '_')}_PR_{pr_number}"
        base_folder_path = os.path.join("src/data", base_folder_name)
        os.makedirs(base_folder_path, exist_ok=True)
        
        # Structure data by files changed
        files_changed = {}
        
        for commit in commit_data:
            commit_sha = commit.sha
            commit_message = commit.commit.message
            
            # Get files changed in this commit
            for file in commit.files:
                filename = file.filename
                if filename not in files_changed:
                    files_changed[filename] = {
                        'file_path': filename,
                        'changes': [],
                        'total_additions': 0,
                        'total_deletions': 0
                    }
                
                change_info = {
                    'commit_sha': commit_sha,
                    'commit_message': commit_message,
                    'status': file.status,  # 'added', 'modified', 'removed'
                    'additions': file.additions,
                    'deletions': file.deletions,
                    'patch': file.patch if hasattr(file, 'patch') and file.patch else None
                }
                
                files_changed[filename]['changes'].append(change_info)
                files_changed[filename]['total_additions'] += file.additions
                files_changed[filename]['total_deletions'] += file.deletions
        
        # Save YAML files maintaining the original repository structure
        for filename, file_data in files_changed.items():
            # Create the directory structure matching the repository
            file_dir = os.path.dirname(filename)
            base_filename = os.path.basename(filename)
            yaml_filename = f"{base_filename}.yaml"
            
            if file_dir:
                target_dir = os.path.join(base_folder_path, file_dir)
                os.makedirs(target_dir, exist_ok=True)
                yaml_file_path = os.path.join(target_dir, yaml_filename)
            else:
                # File is in root directory
                yaml_file_path = os.path.join(base_folder_path, yaml_filename)
            
            output_data = {
                'pull_request': {
                    'repo_name': repo_name,
                    'pr_number': pr_number,
                    'total_commits': len(commit_data)
                },
                'file_changed': file_data
            }
            
            with open(yaml_file_path, 'w', encoding='utf-8') as yaml_file:
                yaml.dump(output_data, yaml_file, default_flow_style=False, indent=2, allow_unicode=True)
            
            print(f"File changes saved to {yaml_file_path}")