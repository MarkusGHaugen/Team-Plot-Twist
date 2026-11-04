# Start here — Team Plot Twist 1.0.0

A **repository** is the project folder plus its change history. GitHub stores a shared copy online. Being a collaborator in this repository gives access to this project only.

## Get access and download

1. Create a GitHub account and send your username to the group owner.
2. Accept the invitation to the private Team Plot Twist repository.
3. Install [GitHub Desktop](https://desktop.github.com/download/), sign in, and choose **File → Clone Repository**. Select Team Plot Twist and choose a folder on your computer.

For a quick trial you can instead extract the supplied `Team-Plot-Twist-1.0.0.zip`. A ZIP does not automatically receive later updates. Once the shared repository is available, cloning it is recommended for contributing.

## Run

Install Python 3.12 and uv using the links in README. Open a terminal **inside the project folder** and run:

```bash
uv sync --locked
uv run streamlit run app.py --server.port 8535
```

Open http://localhost:8535. The first dependency installation needs internet access. On macOS, double-click `run-team.command`; on Windows use `run-team.bat`. If the Mac launcher is not executable, run `chmod +x run-team.command` once in the terminal.

## Make your first change

1. In GitHub Desktop, click **Fetch origin**, then **Pull origin** if offered.
2. Choose **Current Branch → New Branch**, for example `feature/anna-better-dialogue`.
3. Edit the code and play the game. Run `uv run pytest -q`.
4. Review the changed files. Do not include your database, `.venv`, passwords or `.env` files.
5. Write a short commit summary, click **Commit**, then **Publish branch / Push origin**.
6. Click **Create Pull Request**. Ask another group member to review it, then merge on GitHub.
7. Switch back to `main` and pull the merged update.

See CONTRIBUTING for releases and how to avoid conflicts when several people edit the same file.

## Owner: create the shared repository

The local project and source archive are already prepared. Create a **new**, empty private GitHub repository named **Team-Plot-Twist**, with no generated README, licence or gitignore. Do not select an existing repository as a fork or template. Then connect this project to that repository and upload its initial code. If using GitHub Desktop, add this existing local repository and use **Publish repository**, keeping **Keep this code private** checked.

After it is uploaded: **Settings → Collaborators → Add people**. Invite your group members by GitHub username. Share that repository's URL with them after they accept. No group invitations have been sent yet.

Official guidance: [creating a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository) and [inviting collaborators](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository).
