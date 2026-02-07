# 🧪 LIVE Mode Verification Script

This script helps you verify if LIVE mode works with your actual exchange accounts.

## ⚠️ WARNING: Use with Extreme Caution

- Start with **very small amounts** ($1-5 USDT)
- Use **TEST mode first** to verify flows
- Understand you may lose money due to:
  - Exchange fees (0.1-0.5% per trade)
  - Price slippage
  - Transfer failures
  - Market volatility

---

## Pre-Verification Checklist

Before testing LIVE mode, ensure:

- [ ] Exchange API keys are configured correctly
- [ ] API keys have **trading permissions** enabled
- [ ] API keys have **withdrawal permissions** (if implementing transfers)
- [ ] You have USDT on the **buy exchange**
- [ ] You have TOKEN on the **sell exchange** (for current implementation)
- [ ] Wallet private key is configured (for balance checking)
- [ ] You understand the fees on each exchange
- [ ] You're prepared to potentially lose the test amount

---

## Step-by-Step Verification

### Step 1: Verify TEST Mode Works

```bash
# Access your application
# Navigate to Settings
# Ensure "TEST MODE" is enabled (should be yellow)
```

**Test Actions:**
1. Add a token (e.g., BNB, ETH, MATIC)
2. Add exchange API keys
3. Create a manual arbitrage opportunity
4. Execute in TEST mode
5. Check Activity page - should show simulated execution

**Expected Result:** ✅ Successful simulation without errors

---

### Step 2: Verify Exchange API Connectivity

```bash
# Test via terminal/backend

cd backend
source venv/bin/activate  # If using venv
python3
```

```python
import ccxt.async_support as ccxt
import asyncio

async def test_exchange():
    # Replace with your exchange and credentials
    exchange = ccxt.binance({
        'apiKey': 'your-api-key',
        'secret': 'your-api-secret',
        'enableRateLimit': True,
    })
    
    try:
        # Load markets
        await exchange.load_markets()
        print("✅ Exchange connected successfully")
        
        # Fetch balance
        balance = await exchange.fetch_balance()
        print(f"✅ USDT Balance: {balance['USDT']['free']}")
        print(f"✅ BTC Balance: {balance['BTC']['free']}")
        
        # Fetch ticker
        ticker = await exchange.fetch_ticker('BTC/USDT')
        print(f"✅ BTC/USDT Price: ${ticker['last']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await exchange.close()

asyncio.run(test_exchange())
```

**Expected Result:** ✅ All checks pass, no authentication errors

---

### Step 3: Verify Wallet Balance Checking

```bash
# In the application UI:
# 1. Click Wallet in sidebar
# 2. If not configured, add your wallet private key
# 3. Click "Refresh Balance"
```

**Expected Result:** 
- ✅ Shows real BNB balance from BSC Mainnet
- ✅ Shows real USDT balance from BSC Mainnet
- ✅ Network indicator shows "BSC Mainnet"

---

### Step 4: Pre-Position Funds (CRITICAL)

Since the current implementation doesn't transfer funds between exchanges:

**On Buy Exchange (e.g., Binance):**
- Ensure you have **at least $10 USDT**
- This will be used to buy tokens

**On Sell Exchange (e.g., KuCoin):**
- You need to **already have the token** you'll sell
- Example: If trading BNB, you need BNB on KuCoin
- Minimum: Enough to cover the trade amount

**Without pre-positioning both sides, the arbitrage will fail!**

---

### Step 5: Switch to LIVE Mode

```bash
# In Application UI:
# 1. Click Settings (gear icon)
# 2. Under "Trading Mode", click the toggle
# 3. Confirm the switch to LIVE MODE
# 4. You should see a RED warning banner appear
```

**Visual Indicators:**
- Mode toggle should be RED with "LIVE MODE" text
- Red warning banner: "Live Trading Mode Active"
- All execute buttons should show extra warnings

---

### Step 6: Create a Small Test Opportunity

**Option A: Manual Selection**
```bash
# 1. Click "Manual Selection" button
# 2. Select a token (BNB recommended - most liquid)
# 3. Select buy exchange (where you have USDT)
# 4. Select sell exchange (where you have the token)
# 5. Click "Create Opportunity"
```

**Option B: Use Real Detected Opportunity**
- Wait for automatic detection
- Choose opportunity with smallest spread
- Verify you have funds on both exchanges

---

### Step 7: Execute Small Test Trade

**Configuration:**
```
Amount: $1-5 USDT (VERY SMALL for first test)
```

**Execution Steps:**
1. Find your opportunity in dashboard
2. Click "EXECUTE LIVE" button
3. **CRITICAL:** Check the confirmation checkbox
4. Review the warning message carefully
5. Click final execute button
6. Monitor in Activity page

---

### Step 8: Monitor Execution

**Check in Real-Time:**

1. **Activity Page:**
   - Should show "In Progress" status
   - Watch transaction logs appear

2. **Exchange Websites:**
   - Login to buy exchange → check order history
   - Login to sell exchange → check order history
   - Verify orders are actually placed

3. **Check Balances:**
   - Buy exchange USDT should decrease
   - Buy exchange TOKEN should increase
   - Sell exchange TOKEN should decrease
   - Sell exchange USDT should increase

---

### Step 9: Analyze Results

**Successful Execution Looks Like:**

```
Activity Page:
- Status: ✅ COMPLETED
- Buy Order ID: 123456789
- Sell Order ID: 987654321
- Profit/Loss: $X.XX

Transaction Logs:
- price_check: completed
- buy_order: completed
- sell_order: completed
- completed: completed
```

**Failed Execution Looks Like:**

```
Activity Page:
- Status: ❌ FAILED
- Error message displayed

Common Errors:
- "Insufficient balance" (didn't pre-position funds)
- "Symbol not found" (token not available on exchange)
- "Invalid API key" (API permissions issue)
- "Order would trigger" (price protection)
```

---

### Step 10: Calculate Actual Profit/Loss

**Formula:**
```
Net Profit = Sell Revenue - Buy Cost - Fees

Where:
- Sell Revenue = Sell Price × Token Amount
- Buy Cost = Buy Price × Token Amount
- Fees = (Buy Fee + Sell Fee + Network Fee)
```

**Example:**
```
Buy 0.01 BTC at $45,000 = $450
Sell 0.01 BTC at $45,100 = $451
Expected Profit = $1

But with fees:
Buy Fee (0.1%) = $0.45
Sell Fee (0.1%) = $0.45
Network Fee = $0 (no transfer)
Total Fees = $0.90

Actual Profit = $1.00 - $0.90 = $0.10 (90% eaten by fees!)
```

**This is why arbitrage needs larger spreads (1%+) to be profitable!**

---

## 🚨 Common Issues and Solutions

### Issue 1: "Insufficient Balance" Error

**Cause:** Token not pre-positioned on sell exchange

**Solution:**
1. Manually transfer tokens to sell exchange first
2. Wait for deposit confirmation
3. Then execute arbitrage

### Issue 2: "Symbol Not Found"

**Cause:** Token trading pair doesn't exist on exchange

**Solution:**
1. Check exchange website for exact symbol format
2. Verify token is listed on both exchanges
3. Some tokens have different symbols (USDT vs USDT.e)

### Issue 3: Orders Execute but No Profit

**Cause:** Fees eating all profit

**Solution:**
1. Only trade when spread > 1%
2. Use larger amounts to reduce fee percentage
3. Check exchange fee tiers (higher volume = lower fees)

### Issue 4: Slippage Protection Triggers

**Cause:** Price changed between detection and execution

**Solution:**
1. Increase slippage tolerance in settings
2. Execute faster (manual opportunities)
3. Use limit orders instead of market orders

### Issue 5: One Order Succeeds, Other Fails

**Cause:** Current implementation's main weakness

**Solution:**
1. Pre-position funds on both exchanges
2. Monitor balances regularly
3. Manually rebalance as needed

---

## 📊 What Success Looks Like

**After Successful Test:**
- ✅ Both orders visible on exchange websites
- ✅ Balances updated correctly on both exchanges
- ✅ Activity log shows completed status
- ✅ Profit/loss calculated (may be negative after fees)
- ✅ No errors in transaction logs

**This Proves:**
- Exchange API integration works
- Live order placement works
- Order execution is real (not simulated)
- Logging and tracking works

**But Remember:**
- ⚠️ This is NOT true automated arbitrage
- ⚠️ Funds must be pre-positioned
- ⚠️ No automatic transfers between exchanges
- ⚠️ Manual rebalancing required

---

## 🎯 Realistic Expectations

### What Works in LIVE Mode:
- Detecting arbitrage opportunities ✅
- Placing real orders on exchanges ✅
- Monitoring execution in real-time ✅
- Logging all transactions ✅
- Calculating profit/loss ✅

### What Doesn't Work (Yet):
- Automatic fund transfers between exchanges ❌
- Using BSC wallet to bridge exchanges ❌
- Fully automated arbitrage loop ❌
- Withdrawal and deposit automation ❌

### Bottom Line:
**The bot is a "Semi-Automated Trading Assistant"** - it detects opportunities and executes trades, but requires manual fund management between exchanges.

---

## ⚠️ Risk Disclosure

**By testing LIVE mode, you acknowledge:**

1. You may lose money due to:
   - Market volatility
   - Exchange fees
   - Technical failures
   - Price slippage
   - Human error

2. The bot is provided "as-is" without guarantees

3. You are responsible for:
   - Managing exchange accounts
   - Monitoring fund balances
   - Understanding risks
   - Complying with regulations

4. Cryptocurrency trading is risky:
   - Only trade what you can afford to lose
   - Never trade with borrowed money
   - Understand tax implications

**Start with tiny amounts ($1-5) and only scale up after multiple successful tests!**

---

## 📝 Verification Checklist

After testing, confirm:

- [ ] TEST mode executes successfully
- [ ] Exchange API keys work correctly
- [ ] Wallet balance checking works
- [ ] Can switch to LIVE mode
- [ ] LIVE orders actually place on exchanges
- [ ] Activity logs record everything
- [ ] Balances update correctly
- [ ] Understand fee impact on profit
- [ ] Comfortable with manual fund management
- [ ] Know how to stop/pause trading

**If all checked, the LIVE mode is working as designed!**

(But remember: it's designed for semi-automated trading with manual fund management, not fully automated cross-exchange arbitrage)
