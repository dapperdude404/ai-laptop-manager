# Publish AI Laptop Manager to GitHub

Target account: `dapperdude404`
Suggested repository name: `ai-laptop-manager`

## Route A — Let ChatGPT upload the project

1. While logged in to GitHub, visit https://github.com/new.
2. Set **Owner** to `dapperdude404`.
3. Set **Repository name** to `ai-laptop-manager`.
4. Select **Private** for a private project, or **Public** if you want to share the source openly.
5. **Do not** initialize the repository with a README, .gitignore, or license (these source files are already present; a license can be chosen separately).
6. Click **Create repository**.
7. Return to ChatGPT and send: `Created https://github.com/dapperdude404/ai-laptop-manager — please upload the AI Laptop Manager source.`

This method allows the connected GitHub app to add the project files to the existing empty repository. GitHub creation itself must be done by the account owner if the connected app has no create-repository permission/action.

## Route B — Publish from Windows yourself (optional)

Requires Git for Windows and GitHub authentication in the terminal. In the extracted project folder, open Terminal and run:

```powershell
git init -b main
git add .
git commit -m "Initial release: AI Laptop Manager v1.0"
git remote add origin https://github.com/dapperdude404/ai-laptop-manager.git
git push -u origin main
```

Create an empty GitHub repository first. If `git` prompts for identity, configure `user.name` and `user.email` for your Git commits. Use GitHub's supported authentication (for example Git Credential Manager); do **not** put access tokens in source files or commands shared online.

## Before making public

- Do not upload local JSON diagnostic reports, personal screenshots, `.venv`, build outputs, or passwords.
- `.gitignore` excludes local Python cache, virtual environments, executables, and build outputs.
- Tests are included. Windows GitHub Actions can build an executable artifact, but it has not yet been validated on the owner's Dell laptop.
- The program is a local rules-based utility, not an autonomous AI agent, antivirus, or guaranteed repair tool.
- No open-source license has been chosen. Add one only after choosing the terms you want for reuse.