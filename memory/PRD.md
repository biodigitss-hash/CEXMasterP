# Crypto Arbitrage Bot - PRD

## Original Problem Statement
Build a BSC Multi-Exchange Arbitrage Bot with:
- Dashboard for monitoring tokens and arbitrage opportunities
- Manual CEX selection for buy/sell exchanges
- Token management (BEP20 tokens)
- Exchange management (Binance, Gate.io, Huobi with API credentials)
- Wallet configuration with encrypted private key storage
- Real-time WebSocket updates
- **TRUE Automated Arbitrage** with fail-safe execution
- **Fail-Safe Spread Monitoring** - Only sell when target spread is reached

## Architecture
- **Frontend**: React + Tailwind CSS + Framer Motion + Shadcn/UI
- **Backend**: FastAPI + MongoDB (preview) / MySQL (production) + ccxt + Web3.py
- **Database**: Dual support - MongoDB for preview, MySQL (port 3307) for local/production
- **Real-time**: WebSocket for live updates and spread monitoring
- **Security**: Fernet encryption for API keys and private keys
- **Notifications**: Telegram Bot API

## User Personas
1. **Crypto Trader**: Monitors arbitrage opportunities across exchanges
2. **Bot Operator**: Configures tokens, exchanges, and executes trades

## Core Requirements

### Implemented ✅
- [x] Dashboard with stats and opportunities
- [x] Add/manage BEP20 tokens
- [x] Add/manage CEX with encrypted API credentials
- [x] Manual buy/sell exchange selection
- [x] Wallet configuration with encrypted private key
- [x] Arbitrage opportunity detection
- [x] Execute arbitrage (simulation mode)
- [x] WebSocket real-time updates
- [x] Activity page with transaction history
- [x] Test/Live Mode toggle with confirmation
- [x] **TRUE Automated Arbitrage** flow
- [x] **Fail-Safe Arbitrage Execution** with spread monitoring

### NEW: Fail-Safe Arbitrage Execution (Feb 8, 2026)

The fail-safe arbitrage execution follows this flow:

1. **Fund first CEX** (buy exchange) and immediately buy token
2. **Withdraw** purchased token to external wallet
3. **Fund second CEX** (sell exchange) via API and wait
4. **Monitor spread continuously** - watching until target is reached
5. **Only sell when spread hits target** (default: 85%)
6. If spread never hits target within max_wait_time, sell anyway (fail-safe)
7. **Withdraw profits** back to external wallet

### Fail-Safe Settings
- `target_sell_spread`: Target spread % to trigger sell (default: 85%)
- `spread_check_interval`: Seconds between spread checks (default: 10)
- `max_wait_time`: Max time to wait for target spread (default: 3600 seconds = 1 hour)

## API Endpoints

### Settings
- `GET /api/settings` - Get bot configuration (includes fail-safe settings)
- `PUT /api/settings` - Update settings (mode, Telegram, thresholds, fail-safe)

### Telegram
- `POST /api/telegram/test?chat_id=<id>` - Test notification

### Wallet
- `GET /api/wallet` - Get wallet config
- `GET /api/wallet/balance` - Fetch real BSC balance
- `POST /api/wallet` - Save wallet configuration

### Tokens
- `GET /api/tokens` - List all tokens
- `POST /api/tokens` - Add new token
- `DELETE /api/tokens/{id}` - Remove token

### Exchanges
- `GET /api/exchanges` - List all exchanges
- `POST /api/exchanges` - Add new exchange
- `POST /api/exchanges/test` - Test exchange connection
- `DELETE /api/exchanges/{id}` - Remove exchange

### Arbitrage
- `GET /api/arbitrage/detect` - Detect opportunities
- `GET /api/arbitrage/opportunities` - List opportunities
- `POST /api/arbitrage/manual-selection` - Create manual selection
- `POST /api/arbitrage/execute` - Execute with fail-safe logic
- `DELETE /api/arbitrage/opportunities/{id}` - Delete opportunity

### Activity
- `GET /api/activity` - Get all activity logs with trade history
- `GET /api/transactions/{opportunity_id}` - Get transaction logs for specific trade
- `GET /api/trades/history` - Get completed trade history

### Health
- `GET /api/health` - Health check with BSC connection status
- `GET /api/stats` - Dashboard statistics

## Database Schema

### MongoDB Collections (Preview Environment)
- `settings` - Bot configuration including fail-safe settings
- `wallet` - Encrypted wallet configuration
- `tokens` - Monitored tokens
- `exchanges` - Exchange API credentials
- `arbitrage_opportunities` - Detected opportunities
- `transaction_logs` - Execution logs
- `failsafe_states` - Fail-safe arbitrage state tracking

### MySQL Tables (Local/Production - Port 3307)
Same structure as MongoDB, defined in `/app/database_schema.sql`

## Safety Features
1. **Default to Test Mode**: No real trades without explicit mode change
2. **Double Confirmation**: UI checkbox + API confirmed parameter
3. **Price Validation**: Cannot execute with zero or missing prices
4. **Slippage Protection**: Automatic abort if prices change too much
5. **Warning Banners**: Clear visual indicators for live mode
6. **Fail-Safe Monitoring**: Only sells at target spread or timeout

## Configuration

### Environment Variables
**Backend (.env)**:
```env
# MySQL (Local/Production - port 3307)
MYSQL_HOST=localhost
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=crypto_arbitrage

# MongoDB (Preview)
MONGO_URL=mongodb://localhost:27017
DB_NAME=crypto_arbitrage

# App Config
CORS_ORIGINS="*"
ENCRYPTION_KEY=your_key
TELEGRAM_BOT_TOKEN=your_bot_token
```

**Frontend (.env)**:
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

## Files Reference
- `/app/backend/server.py` - Main FastAPI application
- `/app/backend/database_helper.py` - Dual MongoDB/MySQL support
- `/app/backend/.env` - Backend configuration
- `/app/frontend/src/App.js` - Main React app with routing
- `/app/frontend/src/components/` - React components
- `/app/database_schema.sql` - MySQL schema
- `/app/MYSQL_WINDOWS_SETUP.md` - MySQL setup guide

## Completed Work (Feb 8, 2026)

### This Session
1. ✅ Fixed database layer - created dual MongoDB/MySQL support
2. ✅ Implemented fail-safe arbitrage execution with spread monitoring
3. ✅ Added new settings: target_sell_spread, spread_check_interval, max_wait_time
4. ✅ Updated .bat files for MySQL port 3307
5. ✅ Updated database schema with fail-safe tables
6. ✅ Updated documentation (MYSQL_WINDOWS_SETUP.md)
7. ✅ Verified all navigation working (Dashboard, Tokens, Exchanges, Wallet, Activity)
8. ✅ Backend running with MongoDB in preview environment
9. ✅ Added Fail-Safe settings UI to SettingsModal.jsx

## Upcoming Tasks
1. End-to-end testing of fail-safe arbitrage with real exchanges
2. Security enhancements (API key IP whitelisting instructions)
3. Add spread monitoring UI component showing real-time updates

## Backlog
- ML-based spread prediction
- Risk management settings
- Portfolio analytics
- Historical arbitrage logs with real PnL
- Order status polling improvements
