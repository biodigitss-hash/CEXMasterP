# 🪟 MySQL Setup for Windows - Complete Guide

## Quick Overview

Your Crypto Arbitrage Bot uses **MySQL on port 3307** for the database. This guide shows you how to set it up on Windows.

**IMPORTANT:** The default MySQL port is 3306, but this setup uses **port 3307** to avoid conflicts with other installations.

---

## Step 1: Install MySQL

### Download MySQL
1. Go to: https://dev.mysql.com/downloads/installer/
2. Download **MySQL Installer for Windows**
3. Choose "mysql-installer-community" (larger file, includes everything)

### Install MySQL
1. Run the installer
2. Choose **"Developer Default"** or **"Server only"**
3. Click **Next** through the configuration
4. **Important Settings:**
   - **Port: 3307** ⚠️ (NOT the default 3306!)
   - Root Password: **Create a strong password and remember it!**
   - Windows Service: **MySQL80** (check "Start at System Startup")
   - Authentication: Choose **"Use Strong Password Encryption"**

5. Click **Execute** to install
6. Click **Finish**

### Verify MySQL is Running
```powershell
# Open PowerShell and run:
sc query MySQL80

# Should show: STATE : 4  RUNNING
```

---

## Step 2: Create Database

### Option A: Using MySQL Command Line
```powershell
# Login to MySQL (note the port 3307)
mysql -u root -p -P 3307
# Enter your root password when prompted

# In MySQL console, run:
CREATE DATABASE crypto_arbitrage;
USE crypto_arbitrage;

# Import schema file
SOURCE database_schema.sql;

# Or paste each CREATE TABLE statement from database_schema.sql

# Verify tables were created:
SHOW TABLES;

# Should show:
# - arbitrage_opportunities
# - exchanges
# - failsafe_states
# - settings
# - tokens
# - transaction_logs
# - wallet

# Exit MySQL:
exit;
```

### Option B: Using MySQL Workbench (GUI)
1. Open MySQL Workbench (installed with MySQL)
2. Click on **Local instance MySQL80**
3. Enter root password
4. Click **"Create Schema"** button (cylinder icon)
5. Name: `crypto_arbitrage`
6. Click **Apply**
7. Open `database_schema.sql` file
8. Execute all CREATE TABLE statements
9. Verify tables appear in left sidebar

---

## Step 3: Configure Backend

### Update .env File
Open `backend\.env` and update these lines:

```env
# MySQL Configuration (port 3307)
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=your_actual_password_here
MYSQL_DATABASE=crypto_arbitrage

# Generate Encryption Key
ENCRYPTION_KEY=paste_generated_key_here

# App Configuration
CORS_ORIGINS="*"
TELEGRAM_BOT_TOKEN=""
```

### Generate Encryption Key
```powershell
cd backend
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Copy the output and paste as ENCRYPTION_KEY in .env
```

---

## Step 4: Install Python Dependencies

```powershell
cd backend

# Create virtual environment (if not done)
python -m venv venv

# Activate venv
venv\Scripts\activate

# Install dependencies including MySQL driver
pip install -r requirements.txt

# Should install aiomysql and PyMySQL
```

---

## Step 5: Test MySQL Connection

### Quick Test Script
Create a file `test_mysql.py` in backend folder:

```python
import asyncio
import aiomysql

async def test_connection():
    try:
        conn = await aiomysql.connect(
            host='localhost',
            port=3307,  # Note: port 3307
            user='root',
            password='your_password',  # Change this!
            db='crypto_arbitrage'
        )
        
        async with conn.cursor() as cur:
            await cur.execute("SHOW TABLES")
            tables = await cur.fetchall()
            print("✅ MySQL Connection Successful!")
            print(f"Tables found: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
        
        conn.close()
    except Exception as e:
        print(f"❌ MySQL Connection Failed: {e}")

asyncio.run(test_connection())
```

Run it:
```powershell
python test_mysql.py

# Should show:
# ✅ MySQL Connection Successful!
# Tables found: 7
#   - arbitrage_opportunities
#   - exchanges
#   - failsafe_states
#   - settings
#   - tokens
#   - transaction_logs
#   - wallet
```

---

## Step 6: Start the Application

### Start Backend
Double-click `start-backend.bat` or run:
```powershell
cd backend
venv\Scripts\activate
python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Should see:
# INFO: MySQL connection pool created: crypto_arbitrage
# INFO: Application started successfully with MySQL
# INFO: Uvicorn running on http://0.0.0.0:8001
```

### Start Frontend (New Window)
Double-click `start-frontend.bat` or run:
```powershell
cd frontend
yarn start

# Browser opens to http://localhost:3000
```

---

## 🔧 Troubleshooting

### Error: "Can't connect to MySQL server on 'localhost:3307'"

**Check if MySQL is running:**
```powershell
sc query MySQL80

# If stopped, start it:
net start MySQL80
```

**Check if MySQL is using port 3307:**
```powershell
netstat -an | findstr "3307"
# Should show LISTENING on 0.0.0.0:3307
```

**Check firewall:**
- Windows Defender Firewall might block MySQL
- Add exception for MySQL (port 3307)

### Error: "Access denied for user 'root'@'localhost'"

**Wrong password:**
1. Check your password in `.env`
2. Try resetting MySQL root password

### Error: "Unknown database 'crypto_arbitrage'"

**Database not created:**
```powershell
mysql -u root -p -P 3307
CREATE DATABASE crypto_arbitrage;
exit;
```

### Error: "Table doesn't exist"

**Tables not created:**
1. Run all CREATE TABLE statements from `database_schema.sql`
2. Or import the schema file:
   ```powershell
   mysql -u root -p -P 3307 crypto_arbitrage < database_schema.sql
   ```

### Error: "Module 'aiomysql' not found"

**Missing dependency:**
```powershell
venv\Scripts\activate
pip install aiomysql PyMySQL
```

---

## 🆕 New Fail-Safe Arbitrage Feature

The database now includes support for **fail-safe arbitrage execution**:

### New Settings Available:
- **target_sell_spread**: Target spread % to trigger sell (default: 85%)
- **spread_check_interval**: Seconds between spread checks (default: 10)
- **max_wait_time**: Max time to wait for target spread in seconds (default: 3600 = 1 hour)

### How Fail-Safe Works:
1. **Fund first CEX** and immediately buy token
2. **Withdraw** purchased token to external wallet
3. **Fund second CEX** and wait
4. **Monitor spread** continuously
5. **Only sell** when spread hits target (85% default)
6. If spread never hits target within max_wait_time, sell anyway (fail-safe)

This protects your investment by ensuring you only sell at favorable conditions.

---

## 📊 MySQL Management Tools

### MySQL Workbench (Recommended)
- Included with MySQL installation
- Visual database management
- Easy to view data, run queries
- Execute SQL scripts

### Command Line (Advanced)
```powershell
# Login (port 3307)
mysql -u root -p -P 3307

# Use database
USE crypto_arbitrage;

# View tables
SHOW TABLES;

# View data
SELECT * FROM settings;
SELECT * FROM tokens;
SELECT * FROM exchanges;
SELECT * FROM failsafe_states;

# Count records
SELECT COUNT(*) FROM arbitrage_opportunities;

# Exit
exit;
```

---

## 🔒 Security Best Practices

### Create Non-Root User (Recommended)
```sql
-- Login as root (port 3307)
mysql -u root -p -P 3307

-- Create new user
CREATE USER 'arbitrage_user'@'localhost' IDENTIFIED BY 'strong_password_here';

-- Grant permissions
GRANT ALL PRIVILEGES ON crypto_arbitrage.* TO 'arbitrage_user'@'localhost';
FLUSH PRIVILEGES;

-- Test new user
exit;
mysql -u arbitrage_user -p -P 3307
```

Then update `.env`:
```env
MYSQL_USER=arbitrage_user
MYSQL_PASSWORD=strong_password_here
```

---

## ✅ Verification Checklist

Before running the bot, verify:

- [ ] MySQL installed and running (sc query MySQL80)
- [ ] MySQL configured on **port 3307**
- [ ] Database created (crypto_arbitrage)
- [ ] All 7 tables created (SHOW TABLES)
- [ ] .env file updated with MySQL credentials
- [ ] Python dependencies installed (aiomysql)
- [ ] Test connection successful (python test_mysql.py)
- [ ] Backend starts without errors
- [ ] Frontend connects successfully

---

## 🎯 Quick Start Summary

```powershell
# 1. Install MySQL (use port 3307 during installation)

# 2. Create database
mysql -u root -p -P 3307
CREATE DATABASE crypto_arbitrage;
SOURCE database_schema.sql;
exit;

# 3. Configure backend
cd backend
# Edit .env file with MySQL credentials (port 3307)

# 4. Install dependencies
venv\Scripts\activate
pip install -r requirements.txt

# 5. Start backend
start-backend.bat  # Or: python -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# 6. Start frontend (new window)
start-frontend.bat  # Or: cd frontend && yarn start
```

---

**🎉 MySQL setup complete! Your bot is now configured with fail-safe arbitrage.**

For application usage, see:
- `/app/WINDOWS_SETUP_GUIDE.md` - General Windows setup
- `/app/FULL_ARBITRAGE_IMPLEMENTED.md` - Features guide
