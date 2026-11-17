use to deploy in vs code using git hub

terminal 1:
cd backend
npm install
npm start

cd ml-service
py -3.11 -m venv venv
venv\Scripts\activate (only works for windows)
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 5000

terminal 2:
cd backend (note: backend/server.s must have "app.use(express.static(path.join(__dirname, '../frontend')));" underneath "app.use(express.json({ limit: '10mb' }));" before npm start for it to work)
$env:ML_SERVICE_URL="http://localhost:5000"; npm start

note that both terminals should be running
localhost:3000

to commit to another branch:
# 1. Create and switch to your new branch immediately
git switch -c my-new-branch

# 2. Stage your file changes
git add .

# 3. Commit the staged changes
git commit -m "Your descriptive commit message"

# 4. Push the branch and track it on GitHub/GitLab
git push -u origin my-new-branch
