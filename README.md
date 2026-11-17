# ShiftSync

ShiftSync is a duty/shift scheduling app made of three services:

| Folder        | What it is                                   | Tech                              | Port |
| ------------- | -------------------------------------------- | --------------------------------- | ---- |
| `frontend/`   | Web UI (single `index.html` served by Nginx) | HTML/JS, Nginx                    | 80   |
| `backend/`    | REST API + database                          | Node.js, Express, SQLite          | 3000 |
| `ml-service/` | Schedule generation / prediction service     | Python, FastAPI, scikit-learn, OR-Tools | 5000 |
| `k8s/`        | Kubernetes manifests for deployment          | YAML                              | –    |

Repository: https://github.com/lmaaoAki/Shiftsync

---

## 1. Install the tools (one time)

| Tool | Why | Download |
| ---- | --- | -------- |
| **Git** | Commit, branch, push, pull | https://git-scm.com/downloads |
| **VS Code** | Editor with built-in Git support | https://code.visualstudio.com |
| **Node.js 20+** | Run the backend | https://nodejs.org |
| **Python 3.11** | Run the ML service | https://www.python.org/downloads |
| *(optional)* Docker Desktop | Build the containers in `deployment notes` | https://www.docker.com/products/docker-desktop |

Verify in a terminal:

```bash
git --version
node --version
python --version
```

Tell Git who you are (one time):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

Use the same email as your GitHub account so commits are linked to you.

---

## 2. Load the repo into VS Code

You have two ways. **Option A is recommended**, because it connects VS Code to GitHub from the start.

### Option A: Clone from GitHub (recommended)

1. Open VS Code.
2. Press `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`) to open the Command Palette.
3. Type **Git: Clone** and press Enter.
4. Paste the repo URL:
   ```
   https://github.com/lmaaoAki/Shiftsync.git
   ```
5. Choose a folder on your computer to save it in.
6. When VS Code asks **"Would you like to open the cloned repository?"**, click **Open**.
7. If asked, sign in to GitHub in the browser popup and approve access.

Or do the same from a terminal:

```bash
git clone https://github.com/lmaaoAki/Shiftsync.git
cd Shiftsync
code .
```

### Option B: Use the folder you already have (from the .zip)

Only use this if you want to keep the local copy you already unpacked.

1. Unzip `Shiftsync2_2.zip`.
2. In VS Code: **File → Open Folder…** and select the folder that **directly contains** `backend/`, `frontend/`, `k8s/` and `ml-service/`.
   > The zip has an extra wrapper: `Shiftsync2.2/Shiftsync2/`. Open the inner `Shiftsync2` folder, not the outer one, unless that is how the files are laid out on GitHub.
3. Open the integrated terminal (`` Ctrl+` ``) and connect the folder to GitHub:
   ```bash
   git init
   git remote add origin https://github.com/lmaaoAki/Shiftsync.git
   git fetch origin
   git branch -M main
   git reset origin/main
   ```
   `git reset origin/main` links your files to the existing GitHub history without deleting your local changes.
4. Run `git status` to see what differs from GitHub.

> **Check:** the Source Control icon (branch symbol, left sidebar, or `Ctrl+Shift+G`) should show your repo and the branch name (e.g. `main`) at the bottom-left of the VS Code window. If you see "Initialize Repository" instead, Git is not set up in that folder yet.

---

## 3. Run the project locally

Open three terminals in VS Code (`Terminal → New Terminal`, then the **+** button).

**Backend**
```bash
cd backend
npm install
npm start
```
Runs on http://localhost:3000. Optional environment variables: `PORT`, `DB_FILE`, `ML_SERVICE_URL`, `APP_SECRET_KEY`.

**ML service**
```bash
cd ml-service
python -m venv venv
# Windows:      venv\Scripts\activate
# Mac/Linux:    source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 5000
```

> When running locally (not in Kubernetes), point the backend at the ML service:
> ```bash
> # Windows PowerShell
> $env:ML_SERVICE_URL="http://localhost:5000"; npm start
> # Mac/Linux
> ML_SERVICE_URL=http://localhost:5000 npm start
> ```
> The default (`http://shiftsync-ml-service:5000`) only works inside Kubernetes/Docker.

**Frontend**

Open `frontend/index.html` in the browser, or right-click it in VS Code and choose **Open with Live Server** (install the *Live Server* extension first). Check that the API URL used in `index.html` matches your backend.

**Docker / Kubernetes**: see `deployment notes` in the project root for the build and `kubectl` commands.

---

## 4. Everyday Git workflow in VS Code

### The Source Control panel

Open it with `Ctrl+Shift+G`. Changed files appear under **Changes**.

### Commit your work

1. Edit your files and save.
2. In Source Control, hover over a file and click **+** to stage it (or click **+** next to "Changes" to stage everything).
3. Type a message in the box, e.g. `Fix shift overlap check`.
4. Click **Commit**.
5. Click **Sync Changes** (or **Publish Branch** for a new branch) to push to GitHub.

Terminal equivalent:
```bash
git add .
git commit -m "Fix shift overlap check"
git push
```

### Pull the latest changes

Click **… → Pull** in Source Control, or the sync icon in the bottom-left status bar. Or:
```bash
git pull
```
Always pull **before** you start working to avoid conflicts.

### Create a branch

1. Click the branch name at the bottom-left of VS Code.
2. Choose **+ Create new branch…** and type a name, e.g. `feature/login-page`.
3. Work and commit as usual.
4. Click **Publish Branch** to push it to GitHub.

Terminal equivalent:
```bash
git checkout -b feature/login-page
git push -u origin feature/login-page
```

### Switch between branches

Click the branch name at the bottom-left and pick another branch. Or:
```bash
git checkout main
```
Commit or stash your changes before switching.

### Pull a branch someone else created

```bash
git fetch
git checkout feature/their-branch
git pull
```
In VS Code: click the branch name, and remote branches appear as `origin/their-branch`. Selecting one creates a local copy that tracks it.

### Merge a branch into `main`

The easiest way is on GitHub: push your branch, click **Compare & pull request**, then **Merge**. Afterwards:
```bash
git checkout main
git pull
```

Or locally:
```bash
git checkout main
git pull
git merge feature/login-page
git push
```

### Resolving merge conflicts

VS Code highlights conflicts in the file with buttons: **Accept Current Change**, **Accept Incoming Change**, **Accept Both Changes**. Pick one for each conflict, save, stage the file, then commit.

---

## 5. Suggested branch naming

| Prefix | Use for | Example |
| ------ | ------- | ------- |
| `feature/` | New features | `feature/shift-swap` |
| `fix/` | Bug fixes | `fix/ml-timeout` |
| `docs/` | Documentation | `docs/readme-update` |

Keep `main` working. Do your changes on a branch and merge through a pull request.

---

## 6. Before you commit: things to check

- **Add a `.gitignore`** so you do not commit generated files. Create a file named `.gitignore` in the project root with:
  ```
  node_modules/
  venv/
  __pycache__/
  *.sqlite
  data/
  .env
  ```
- **Secrets:** `k8s/01-secrets.yaml` contains `APP_SECRET_KEY` in plain text. If the GitHub repo is public, anyone can read it. Replace it with a new value that you never commit, and consider adding that file to `.gitignore`.
- **Line endings:** the files use Windows (CRLF) endings. If Git shows every line as changed, run `git config --global core.autocrlf true` (Windows) or `input` (Mac/Linux).

---

## 7. Troubleshooting

| Problem | Fix |
| ------- | --- |
| `git` is not recognized | Install Git and restart VS Code |
| VS Code shows "Initialize Repository" | Run `git init` in the folder, or re-open the cloned folder |
| `Permission denied` / login popup keeps appearing | Sign in again via the **Accounts** icon (bottom-left) → GitHub |
| Push rejected (`non-fast-forward`) | Run `git pull` first, resolve any conflicts, then push |
| `npm install` fails on `sqlite3` | Make sure Node 20 is installed; on Windows install the C++ build tools if prompted |
| Backend cannot reach ML service | Set `ML_SERVICE_URL=http://localhost:5000` (see section 3) |
| Wrong folder opened (no `backend/` in the sidebar) | **File → Open Folder** and pick the folder that directly contains `backend/` |
