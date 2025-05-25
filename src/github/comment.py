class PRCommenter:
    def __init__(self, github_client):
        self.github_client = github_client

    def comment_on_pr(self, repo_name, pr_number, message):
        repo = self.github_client.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        print(pr)
        pr.create_issue_comment(message)