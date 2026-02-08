# 🪟 Windows Setup Guide - Quick Fix for Server Error

## Error You're Seeing:
```
KeyError: 'MONGO_URL'  ← OLD ERROR (FIXED)
```

## ✅ FIXED - Server Now Uses MySQL

The bot now uses **MySQL database** instead of MongoDB.

---

## 🚀 Quick Start on Windows

### Step 1: Install Prerequisites

#### 1.1 Install Python 3.9+
1. Download from: https://www.python.org/downloads/
2. **IMPORTANT:** Check "Add Python to PATH" during installation
3. Verify installation:
```powershell
python --version
# Should show Python 3.9 or higher
```

#### 1.2 Install MySQL
1. Download from: https://dev.mysql.com/downloads/installer/
2. Choose "mysql-installer-community" (includes everything)
3. Install with default settings
4. **IMPORTANT:** Remember your root password!
5. Verify it's running:
```powershell
# Open Services (Win+R, type "services.msc")
# Look for "MySQL80" - should be Running
```

**Detailed MySQL Setup:** See `/app/MYSQL_WINDOWS_SETUP.md`

#### 1.3 Install Node.js
1. Download from: https://nodejs.org/ (LTS version)
2. Install with default settings
3. Verify:
```powershell
node --version
npm --version
```

---

## Step 2: Setup MySQL Database

### 2.1 Create Database
```powershell
# Login to MySQL
mysql -u root -p
# Enter your root password when prompted

# In MySQL console:
CREATE DATABASE crypto_arbitrage;
USE crypto_arbitrage;

# Import the schema (from project root):
source database_schema.sql;

# Or manually run all CREATE TABLE statements from database_schema.sql

# Verify tables created:
SHOW TABLES;
# Should show: arbitrage_opportunities, exchanges, settings, tokens, transaction_logs, wallet

# Exit MySQL:
exit;
```

### 2.2 Test Connection (Optional)
```powershell
mysql -u root -p crypto_arbitrage
SHOW TABLES;
exit;
```

---

## Step 3: Configure Backend

#### 3.1 Open PowerShell/Command Prompt
```powershell
# Navigate to your project
cd C:\Users\USER\Desktop\CEX BOT\CEX\CEXMasterP
```

#### 3.2 Go to Backend Folder
```powershell
cd backend
```

#### 3.3 Create Virtual Environment (Recommended)
```powershell
# Create venv
python -m venv venv

# Activate it
venv\Scripts\activate

# You should see (venv) in your prompt
```

#### 3.4 Install Dependencies
```powershell
pip install -r requirements.txt

# This takes 2-5 minutes
```

#### 3.5 Create .env File (Optional but Recommended)
Create a file named `.env` in the `backend` folder with this content:

```env
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=crypto_arbitrage

# Encryption Key - GENERATE A NEW ONE!
ENCRYPTION_KEY=

# Optional: Telegram Bot Token
TELEGRAM_BOT_TOKEN=

# Server Configuration
HOST=0.0.0.0
PORT=8001

# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

#### 3.6 Generate Encryption Key
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Copy the output (looks like: gAAAAABh...)
# Paste it as ENCRYPTION_KEY in .env file
```

#### 3.7 Start Backend Server
```powershell
# Make sure you're in backend folder with venv activated
python server.py

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8001
# INFO:     Application startup complete.
```

**✅ Backend is now running!**

Leave this window open. Open a new PowerShell window for frontend.

---

### Step 3: Setup Frontend

#### 3.1 Open New PowerShell Window
```powershell
# Navigate to project
cd C:\Users\USER\Desktop\CEX BOT\CEX\CEXMasterP

# Go to frontend folder
cd frontend
```

#### 3.2 Install Yarn (if not installed)
```powershell
npm install -g yarn
```

#### 3.3 Install Dependencies
```powershell
yarn install

# This takes 3-5 minutes
```

#### 3.4 Create Frontend .env File
Create a file named `.env` in the `frontend` folder:

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

#### 3.5 Start Frontend
```powershell
yarn start

# Browser will open automatically to http://localhost:3000
```

**✅ Frontend is now running!**

---

## 🎯 Quick Fix Summary

### What Was Fixed:
1. ✅ Changed `os.environ['MONGO_URL']` to `os.environ.get('MONGO_URL', 'default')`
2. ✅ Server now uses defaults if .env is missing
3. ✅ No more KeyError

### Default Values (Used if .env is missing):
- MongoDB URL: `mongodb://localhost:27017/`
- Database Name: `crypto_arbitrage`
- Host: `0.0.0.0`
- Port: `8001`

---

## 🔧 Troubleshooting

### Issue: "python is not recognized"
**Fix:**
1. Reinstall Python and check "Add Python to PATH"
2. Or add manually:
   - Search for "Environment Variables" in Windows
   - Edit System PATH
   - Add: `C:\Python39` (or your Python install location)
   - Restart PowerShell

### Issue: "MongoDB connection failed"
**Fix:**
1. Open Services (Win+R → services.msc)
2. Find "MongoDB Server"
3. Right-click → Start
4. If not found, reinstall MongoDB

### Issue: "Port 8001 already in use"
**Fix:**
```powershell
# Find and kill the process
netstat -ano | findstr :8001
# Note the PID (last number)
taskkill /PID <PID> /F
```

### Issue: "Module not found"
**Fix:**
```powershell
# Activate venv (if not already)
venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Permission denied"
**Fix:**
- Run PowerShell as Administrator
- Or use Command Prompt instead

---

## 📝 File Locations

### Backend .env File:
```
C:\Users\USER\Desktop\CEX BOT\CEX\CEXMasterP\backend\.env
```

### Frontend .env File:
```
C:\Users\USER\Desktop\CEX BOT\CEX\CEXMasterP\frontend\.env
```

---

## ✅ Verification

### Check Backend is Running:
1. Open browser
2. Go to: http://localhost:8001/api/health
3. Should see: `{"status": "healthy", ...}`

### Check Frontend is Running:
1. Browser should open automatically to http://localhost:3000
2. You should see the Arbitrage Dashboard

---

## 🎮 Using the App

### First Time Setup:
1. **Configure Wallet**
   - Click "Wallet" in sidebar
   - Add your BSC wallet address
   - Add your private key (will be encrypted)
   - Click "Save Wallet"

2. **Add Exchange API Keys**
   - Click "Add Exchange"
   - Enter exchange details
   - Add API Key and Secret
   - Save

3. **Add Tokens to Monitor**
   - Click "Add Token"
   - Enter token details (BNB, ETH, etc.)
   - Select exchanges
   - Save

4. **Start Trading**
   - Wait for opportunities to appear
   - Click "EXECUTE TEST" to test
   - Switch to LIVE when ready

---

## 🚨 Important Notes

### For Windows Users:
- Use `\` instead of `/` in paths
- Use PowerShell or Command Prompt
- Run as Administrator if permission issues
- Antivirus might block some operations

### For Best Performance:
- Keep both PowerShell windows open
- Don't close browser during trades
- Monitor for any error messages
- Check MongoDB is always running

### Security:
- Never share your .env files
- Keep private keys secure
- Use strong encryption keys
- Don't commit .env to git

---

## 📚 Additional Resources

### Documentation Files:
1. `/app/LOCAL_INSTALLATION_COMPLETE_GUIDE.md` - Detailed guide
2. `/app/FULL_ARBITRAGE_IMPLEMENTED.md` - Feature docs
3. `/app/OPTIMIZATION_REPORT.md` - Performance guide
4. `/app/FINAL_STATUS_REPORT.md` - Current status

### Getting Help:
- Check logs in PowerShell windows
- Review error messages
- Consult documentation
- Verify all prerequisites installed

---

## 🎉 Success!

If you see:
- ✅ Backend: "Application startup complete"
- ✅ Frontend: Dashboard loads in browser
- ✅ No errors in PowerShell windows

**You're ready to start trading!**

---

**Need more help? Check the complete installation guide in `/app/LOCAL_INSTALLATION_COMPLETE_GUIDE.md`**
