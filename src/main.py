import os
import sys
import requests
import yaml
from flask import Flask, request, jsonify
from github import Github
from dotenv import load_dotenv
import time

app = Flask(__name__)

load_dotenv()
github_token = os.getenv("GITHUB_TOKEN")
print(f"GitHub Token: {github_token}")
github_client = Github(github_token)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from src.github.webhook import WebhookListener
from src.github.pull_request import PRReader
from src.github.comment import PRCommenter
from src.analysis.dependency_analyzer import DependencyAnalyzer

webhook_listener = WebhookListener()
pr_reader = PRReader(github_client)
pr_commenter = PRCommenter(github_client)
dependency_analyzer = DependencyAnalyzer(github_client)

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    if webhook_listener.is_pull_request_opened(payload):
        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]
        commit_data = pr_reader.read_commits(repo_name, pr_number)
        pr_reader.save_commits_to_folder(repo_name, pr_number, commit_data)
        pr_commenter.comment_on_pr(repo_name, pr_number, "Thanks for the PR! The bot has read your commits.")
    return jsonify({"status": "processed"})

if __name__ == '__main__':
    # app.run(debug=True)
    # repo_name = 'karthiksenthil2803/get-your-guide-web-scraper'
    repo_name = 'karthiksenthil2803/test-codelens'
    pr_number = 1
    commits = pr_reader.read_commits(repo_name, pr_number)
    pr_reader.save_commits_to_folder(repo_name, pr_number, commits)
    
    # Analyze dependencies for generated YAML files
    import glob
    yaml_pattern = f"src/data/{repo_name.replace('/', '_')}_PR_{pr_number}/**/*.yaml"
    yaml_files = glob.glob(yaml_pattern, recursive=True)
    
    # Specify target repositories for cross-repo analysis (limit to most important ones)
    cross_repo_targets = [
        'karthiksenthil2803/test-codelens-2',
        # Add more repositories as needed, but keep the list small for performance
    ]
    
    total_start_time = time.time()
    
    for yaml_file in yaml_files:
        if yaml_file.endswith('.yaml') and 'analysis' not in yaml_file:
            print(f"Analyzing dependencies for: {yaml_file}")
            file_start_time = time.time()
            
            analysis_results = dependency_analyzer.analyze_dependencies(
                repo_name, yaml_file, cross_repo_targets
            )
            
            # Save analysis results
            analysis_output_path = yaml_file.replace('.yaml', '_analysis.yaml')
            dependency_analyzer.save_analysis(analysis_results, analysis_output_path)
            
            # Save cross-repository analysis separately if impacts found
            cross_repo_impacts = analysis_results.get('cross_repository_impacts', {})
            if cross_repo_impacts.get('cross_repo_dependencies'):
                cross_repo_output_path = yaml_file.replace('.yaml', '_cross_repo_analysis.yaml')
                dependency_analyzer.cross_repo_analyzer.save_cross_repo_analysis(
                    cross_repo_impacts, cross_repo_output_path
                )
            
            file_elapsed = time.time() - file_start_time
            print(f"Completed analysis for {yaml_file} in {file_elapsed:.2f} seconds\n")
    
    total_elapsed = time.time() - total_start_time
    print(f"Total analysis completed in {total_elapsed:.2f} seconds")