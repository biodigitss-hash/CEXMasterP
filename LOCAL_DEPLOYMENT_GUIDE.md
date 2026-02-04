# 🚀 Local System Deployment Guide
## BSC Multi-Exchange Crypto Arbitrage Bot

This guide will help you run the Crypto Arbitrage Bot on your local development machine.

---

## 📋 Prerequisites

Before starting, ensure you have the following installed:

### Required Software
- **Node.js** (v16 or higher) - [Download](https://nodejs.org/)
- **Python** (v3.9 or higher) - [Download](https://www.python.org/)
- **MongoDB** (v4.4 or higher) - [Download](https://www.mongodb.com/try/download/community)
- **Yarn** package manager - Install with: `npm install -g yarn`
- **Git** (optional, for cloning) - [Download](https://git-scm.com/)

### Verify Installation
```bash
node --version    # Should show v16+
python --version  # Should show 3.9+
mongod --version  # Should show 4.4+
yarn --version    # Should show 1.22+
```

---

## 📁 Step 1: Get the Project Files

### Option A: If you have the source code
```bash
# Navigate to your project directory
cd /path/to/crypto-arbitrage-bot
```

### Option B: If cloning from repository
```bash
git clone <your-repository-url>
cd crypto-arbitrage-bot
```

Your project structure should look like:
```
crypto-arbitrage-bot/
├── backend/
│   ├── server.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   ├── package.json
│   └── .env
├── test_result.md
└── README.md
```

---

## 🗄️ Step 2: Setup MongoDB

### Option A: Local MongoDB Installation

1. **Start MongoDB service:**
   
   **On macOS:**
   ```bash
   brew services start mongodb-community
   ```
   
   **On Linux:**
   ```bash
   sudo systemctl start mongod
   sudo systemctl enable mongod
   ```
   
   **On Windows:**
   - Start MongoDB from Services or run `mongod` in Command Prompt

2. **Verify MongoDB is running:**
   ```bash
   mongosh
   # You should see MongoDB shell
   # Type 'exit' to leave
   ```

### Option B: MongoDB Atlas (Cloud - Free Tier)

1. Create account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free cluster
3. Get your connection string (looks like: `mongodb+srv://username:password@cluster.mongodb.net/`)
4. Whitelist your IP address (or use 0.0.0.0/0 for testing)

---

## ⚙️ Step 3: Backend Setup

### 1. Navigate to backend directory
```bash
cd backend
```

### 2. Create Python virtual environment (recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the `backend/` directory:

```bash
# backend/.env

# MongoDB Configuration
MONGO_URL=mongodb://localhost:27017/
# For MongoDB Atlas, use:
# MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/

DB_NAME=crypto_arbitrage

# Encryption Key (generate a new one for production)
ENCRYPTION_KEY=your-32-character-encryption-key-here

# Telegram Bot (optional)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here

# CORS Origins (for local development)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Server Configuration
HOST=0.0.0.0
PORT=8001
```

**To generate a secure encryption key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 5. Start the backend server
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

**Test the backend:**
```bash
curl http://localhost:8001/api/health
# Should return: {"status":"healthy", ...}
```

---

## 🎨 Step 4: Frontend Setup

### 1. Open a new terminal and navigate to frontend directory
```bash
cd frontend
```

### 2. Install Node.js dependencies
```bash
yarn install
```

### 3. Configure environment variables

Create a `.env` file in the `frontend/` directory:

```bash
# frontend/.env

# Backend API URL
REACT_APP_BACKEND_URL=http://localhost:8001
```

### 4. Start the frontend development server
```bash
yarn start
```

The app should automatically open in your browser at `http://localhost:3000`

You should see:
```
Compiled successfully!

You can now view the app in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://192.168.x.x:3000
```

---

## ✅ Step 5: Verify Everything is Working

### 1. Access the Application
- Open your browser to: **http://localhost:3000**
- You should see the Arbitrage Dashboard

### 2. Check Backend Connection
- Open browser DevTools (F12)
- Go to Network tab
- Refresh the page
- You should see API calls to `http://localhost:8001/api/...` succeeding

### 3. Test Basic Functionality
- Click **Settings** icon - modal should open
- Click **Add Token** button - modal should open
- Click **Wallet** in sidebar - wallet modal should open
- Click **Activity** in sidebar - activity page should load

---

## 🔧 Common Issues & Solutions

### Issue: Backend won't start

**Error: "Address already in use"**
```bash
# Check what's using port 8001
lsof -i :8001  # macOS/Linux
netstat -ano | findstr :8001  # Windows

# Kill the process or use a different port
uvicorn server:app --host 0.0.0.0 --port 8002 --reload
```

**Error: "No module named 'motor'"**
```bash
# Make sure virtual environment is activated and reinstall
pip install -r requirements.txt
```

**Error: "Could not connect to MongoDB"**
```bash
# Check MongoDB is running
mongosh
# Or check your MONGO_URL in .env
```

### Issue: Frontend won't start

**Error: "Port 3000 is already in use"**
```bash
# Kill the process
lsof -i :3000  # macOS/Linux
npx kill-port 3000  # Any OS with npx

# Or set a different port
PORT=3001 yarn start
```

**Error: "Module not found"**
```bash
# Delete node_modules and reinstall
rm -rf node_modules yarn.lock
yarn install
```

### Issue: Cannot connect frontend to backend

**CORS errors in browser console**
- Check `CORS_ORIGINS` in backend/.env includes your frontend URL
- Restart backend after changing .env

**API calls failing**
- Verify backend is running: `curl http://localhost:8001/api/health`
- Check `REACT_APP_BACKEND_URL` in frontend/.env
- Restart frontend after changing .env

---

## 🎯 Production Build (Local Testing)

### Build Frontend for Production
```bash
cd frontend
yarn build
```

This creates an optimized production build in `frontend/build/`

### Serve Production Build
```bash
# Install serve globally
npm install -g serve

# Serve the build
serve -s build -l 3000
```

### Run Backend in Production Mode
```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --workers 4
```

---

## 📊 Monitoring & Logs

### View Backend Logs
When running locally with `--reload`, logs appear in your terminal.

### View Frontend Logs
- Browser DevTools Console (F12 → Console)
- Network tab for API requests

### MongoDB Logs
```bash
# Find MongoDB log file location
mongod --help | grep "log"

# View logs
tail -f /path/to/mongodb/mongod.log
```

---

## 🔐 Security Recommendations for Local Development

1. **Use strong encryption keys** - Generate new keys, don't use defaults
2. **Protect .env files** - Add `.env` to `.gitignore`
3. **Use test API keys** - Don't use production exchange API keys locally
4. **Test mode first** - Always test in TEST mode before LIVE mode
5. **Secure MongoDB** - Enable authentication for production use

---

## 🛑 Stopping the Application

### Stop Frontend
- Press `Ctrl+C` in the terminal running `yarn start`

### Stop Backend
- Press `Ctrl+C` in the terminal running `uvicorn`

### Stop MongoDB (if needed)
```bash
# macOS
brew services stop mongodb-community

# Linux
sudo systemctl stop mongod

# Windows
# Stop from Services or press Ctrl+C if running in terminal
```

---

## 📚 Next Steps

1. **Configure Exchanges**: Add your exchange API keys in the dashboard
2. **Add Tokens**: Add BEP20 tokens to monitor for arbitrage
3. **Setup Wallet**: Configure your BSC wallet for trade execution
4. **Test in TEST Mode**: Verify everything works with simulated trades
5. **Configure Telegram**: (Optional) Set up notifications
6. **Go LIVE**: Switch to LIVE mode when ready

---

## 🆘 Need Help?

- **Backend Errors**: Check `backend/server.py` for stack traces
- **Frontend Errors**: Check browser DevTools Console
- **Database Issues**: Verify MongoDB connection with `mongosh`
- **Environment Variables**: Double-check all `.env` files

---

## 📱 Development Tips

### Hot Reload
- Both frontend and backend support hot reload
- Changes to code automatically restart the servers
- No need to manually restart during development

### API Testing
Use curl or Postman to test API endpoints:
```bash
# Get settings
curl http://localhost:8001/api/settings

# Get stats
curl http://localhost:8001/api/stats

# Get health
curl http://localhost:8001/api/health
```

### Database Access
```bash
# Connect to MongoDB
mongosh

# Use your database
use crypto_arbitrage

# View collections
show collections

# Query data
db.tokens.find()
db.exchanges.find()
db.settings.find()
```

---

**✨ You're all set! Happy trading! ✨**
