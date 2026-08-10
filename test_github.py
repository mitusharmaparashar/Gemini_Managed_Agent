from services.github_service import GitHubService

github = GitHubService()

url = input("Enter GitHub PR URL: ").strip()

try:
    pr = github.get_pr(url)

    print("=" * 60)
    print("Title :", pr["title"])
    print("State :", pr["state"])
    print("Author:", pr["user"]["login"])

except Exception as e:
    print(e)