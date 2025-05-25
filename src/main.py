import os
import sys
import requests
from flask import Flask, request, jsonify
from github import Github

app = Flask(__name__)

github_token = os.getenv("GITHUB_TOKEN")
github_client = Github(github_token)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from src.github.webhook import WebhookListener
from src.github.pull_request import PRReader
from src.github.comment import PRCommenter

webhook_listener = WebhookListener()
pr_reader = PRReader(github_client)
pr_commenter = PRCommenter(github_client)

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
    repo_name = 'karthiksenthil2803/codelens'
    pr_number = 1
    commits = pr_reader.read_commits(repo_name, pr_number)
    pr_reader.save_commits_to_folder(repo_name, pr_number, commits)
    # pr_commenter.comment_on_pr(repo_name, pr_number, "Test comment")