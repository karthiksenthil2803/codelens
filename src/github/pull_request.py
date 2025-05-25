import os
from pathlib import Path

class PRReader:
    def __init__(self, github_client):
        self.github_client = github_client

    def read_commits(self, repo_name, pr_number):
        repo = self.github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        return [commit for commit in pr.get_commits()]

    def save_commits_to_folder(self, repo_name, pr_number, commits):
        base_path = Path(f"./data/{repo_name.replace('/', '_')}/pr_{pr_number}")
        base_path.mkdir(parents=True, exist_ok=True)
        for idx, commit in enumerate(commits):
            sha = commit.sha
            commit_message = commit.commit.message
            file_details = []
            for file in commit.files:
                filename = file.filename
                patch = file.patch if file.patch else "(Binary or no patch available)"
                file_details.append(f"File: {filename}\nPatch:\n{patch}\n\n")
            commit_content = f"Commit: {sha}\nMessage: {commit_message}\n\n" + "".join(file_details)
            with open(base_path / f"commit_{idx+1}_{sha[:7]}.txt", "w", encoding="utf-8") as f:
                f.write(commit_content)