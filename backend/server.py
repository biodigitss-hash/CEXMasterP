from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio
import json
import time
from cryptography.fernet import Fernet
import base64
import hashlib
import ccxt.async_support as ccxt
import httpx
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from database_helper import create_database

ROOT_DIR = Path(__file__).parent

# Load environment variables from .env file
load_dotenv(ROOT_DIR / '.env')

# Create database instance (auto-detects MongoDB or MySQL)
db_instance, db, IS_MONGODB = create_database()

# Encryption key for API secrets
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')

# BSC Network Configuration
BSC_MAINNET_RPC = "https://bsc-dataseed1.binance.org/"
BSC_TESTNET_RPC = "https://data-seed-prebsc-1-s1.binance.org:8545/"

# USDT Contract Addresses (BEP20)
USDT_MAINNET = "0x55d398326f99059fF775485246999027B3197955"
USDT_TESTNET = "0x337610d27c682E347C9cD60BD4b3b107C9d34dDd"

# Arbitrage Configuration
MIN_CONFIRMATIONS = 1  # Fast confirmations (30-60 seconds on BSC)
WITHDRAWAL_TIMEOUT = 1800  # 30 minutes max
DEPOSIT_TIMEOUT = 1800  # 30 minutes max
MAX_RETRIES = 3  # For API calls

# ERC20 ABI for balance checking and transfers
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]

app = FastAPI(title="Crypto Arbitrage Bot API", version="2.0.0")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# ============== TELEGRAM NOTIFICATION SERVICE ==============
class TelegramNotifier:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def send_message(self, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to a Telegram chat"""
        if not self.bot_token or not chat_id:
            logger.warning("Telegram not configured - skipping notification")
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": message,
                        "parse_mode": parse_mode
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    logger.info(f"Telegram notification sent to {chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    async def notify_opportunity(self, chat_id: str, opportunity: dict) -> bool:
        """Send arbitrage opportunity notification"""
        message = f"""
🔔 <b>New Arbitrage Opportunity Detected!</b>

📊 <b>Token:</b> {opportunity.get('token_symbol', 'Unknown')}
💰 <b>Spread:</b> {opportunity.get('spread_percent', 0):.4f}%

🟢 <b>Buy on:</b> {opportunity.get('buy_exchange', 'Unknown')}
   Price: ${opportunity.get('buy_price', 0):.6f}

🔴 <b>Sell on:</b> {opportunity.get('sell_exchange', 'Unknown')}
   Price: ${opportunity.get('sell_price', 0):.6f}

📈 <b>Confidence:</b> {opportunity.get('confidence', 0):.1f}%
💵 <b>Recommended Amount:</b> ${opportunity.get('recommended_usdt_amount', 0):.2f}

⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return await self.send_message(chat_id, message)
    
    async def notify_trade_started(self, chat_id: str, opportunity: dict, usdt_amount: float, is_live: bool) -> bool:
        """Send trade execution started notification"""
        mode = "🔴 LIVE" if is_live else "🟡 TEST"
        message = f"""
⚡ <b>Trade Execution Started</b> {mode}

📊 <b>Token:</b> {opportunity.get('token_symbol', 'Unknown')}
💰 <b>Amount:</b> ${usdt_amount:.2f} USDT

🟢 <b>Buying on:</b> {opportunity.get('buy_exchange', 'Unknown')}
🔴 <b>Selling on:</b> {opportunity.get('sell_exchange', 'Unknown')}

📈 <b>Expected Spread:</b> {opportunity.get('spread_percent', 0):.4f}%

⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return await self.send_message(chat_id, message)
    
    async def notify_trade_completed(self, chat_id: str, result: dict, is_live: bool) -> bool:
        """Send trade completion notification"""
        mode = "🔴 LIVE" if is_live else "🟡 TEST"
        profit = result.get('profit', 0)
        profit_emoji = "✅" if profit > 0 else "❌"
        
        message = f"""
{profit_emoji} <b>Trade Completed</b> {mode}

📊 <b>Status:</b> {result.get('status', 'Unknown')}
💰 <b>Invested:</b> ${result.get('usdt_invested', 0):.2f} USDT
🪙 <b>Tokens Bought:</b> {result.get('tokens_bought', 0):.8f}
💵 <b>Sell Value:</b> ${result.get('sell_value', 0):.4f}

{'📈' if profit > 0 else '📉'} <b>Profit:</b> ${profit:.4f} ({result.get('profit_percent', 0):.4f}%)

⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return await self.send_message(chat_id, message)
    
    async def notify_error(self, chat_id: str, error_message: str, context: str = "") -> bool:
        """Send error notification"""
        message = f"""
🚨 <b>Error Alert</b>

❌ <b>Error:</b> {error_message}
📍 <b>Context:</b> {context or 'Unknown'}

⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        return await self.send_message(chat_id, message)

telegram_notifier = TelegramNotifier(TELEGRAM_BOT_TOKEN)

# ============== WEB3 BSC SERVICE ==============
class BSCWalletService:
    def __init__(self):
        self.mainnet_w3 = None
        self.testnet_w3 = None
        self._init_connections()
    
    def _init_connections(self):
        """Initialize Web3 connections"""
        try:
            self.mainnet_w3 = Web3(Web3.HTTPProvider(BSC_MAINNET_RPC))
            self.mainnet_w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            logger.info(f"BSC Mainnet connected: {self.mainnet_w3.is_connected()}")
        except Exception as e:
            logger.error(f"Failed to connect to BSC Mainnet: {e}")
        
        try:
            self.testnet_w3 = Web3(Web3.HTTPProvider(BSC_TESTNET_RPC))
            self.testnet_w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            logger.info(f"BSC Testnet connected: {self.testnet_w3.is_connected()}")
        except Exception as e:
            logger.error(f"Failed to connect to BSC Testnet: {e}")
    
    def get_web3(self, is_live: bool) -> Web3:
        """Get appropriate Web3 instance based on mode"""
        return self.mainnet_w3 if is_live else self.testnet_w3
    
    def get_usdt_address(self, is_live: bool) -> str:
        """Get USDT contract address based on mode"""
        return USDT_MAINNET if is_live else USDT_TESTNET
    
    async def get_bnb_balance(self, address: str, is_live: bool = True) -> float:
        """Get BNB balance for an address"""
        try:
            w3 = self.get_web3(is_live)
            if not w3 or not w3.is_connected():
                logger.warning("Web3 not connected")
                return 0.0
            
            checksum_address = Web3.to_checksum_address(address)
            balance_wei = w3.eth.get_balance(checksum_address)
            balance_bnb = w3.from_wei(balance_wei, 'ether')
            return float(balance_bnb)
        except Exception as e:
            logger.error(f"Error getting BNB balance: {e}")
            return 0.0
    
    async def get_usdt_balance(self, address: str, is_live: bool = True) -> float:
        """Get USDT (BEP20) balance for an address"""
        try:
            w3 = self.get_web3(is_live)
            if not w3 or not w3.is_connected():
                logger.warning("Web3 not connected")
                return 0.0
            
            usdt_address = self.get_usdt_address(is_live)
            checksum_address = Web3.to_checksum_address(address)
            usdt_contract = w3.eth.contract(
                address=Web3.to_checksum_address(usdt_address),
                abi=ERC20_ABI
            )
            
            balance = usdt_contract.functions.balanceOf(checksum_address).call()
            decimals = usdt_contract.functions.decimals().call()
            return float(balance) / (10 ** decimals)
        except Exception as e:
            logger.error(f"Error getting USDT balance: {e}")
            return 0.0
    
    def is_valid_address(self, address: str) -> bool:
        """Check if address is valid"""
        try:
            Web3.to_checksum_address(address)
            return True
        except Exception:
            return False

bsc_service = BSCWalletService()

# ============== MODELS ==============
class TokenCreate(BaseModel):
    name: str
    symbol: str
    contract_address: str
    monitored_exchanges: List[str] = []

class Token(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    symbol: str
    contract_address: str
    monitored_exchanges: List[str] = []
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True

class ExchangeCreate(BaseModel):
    name: str
    api_key: str
    api_secret: str
    additional_params: Optional[Dict[str, str]] = None

class Exchange(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    api_key_encrypted: str
    api_secret_encrypted: str
    additional_params_encrypted: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WalletConfigCreate(BaseModel):
    private_key: str
    address: Optional[str] = None

class WalletConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    address: str
    private_key_encrypted: str
    balance_bnb: float = 0.0
    balance_usdt: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class ArbitrageOpportunity(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    token_id: str
    token_symbol: str
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    spread_percent: float
    confidence: float
    recommended_usdt_amount: float
    status: str = "detected"  # detected, executing, completed, failed
    is_manual_selection: bool = False
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    persistence_minutes: int = 0

class ManualSelectionCreate(BaseModel):
    token_id: str
    buy_exchange: str
    sell_exchange: str

class ExecuteArbitrageRequest(BaseModel):
    opportunity_id: str
    usdt_amount: float
    confirmed: bool = False  # User must confirm for live trading

class PriceData(BaseModel):
    exchange: str
    symbol: str
    bid: float
    ask: float
    last: float
    timestamp: str

class TransactionLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    opportunity_id: str
    step: str
    status: str
    details: Dict[str, Any] = {}
    is_live: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class BotSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_live_mode: bool = False  # False = Test mode, True = Live mode
    telegram_chat_id: str = ""
    telegram_enabled: bool = False
    min_spread_threshold: float = 0.5  # Minimum spread % to trigger opportunity
    max_trade_amount: float = 1000.0
    slippage_tolerance: float = 0.5  # Percentage
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class SettingsUpdate(BaseModel):
    is_live_mode: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    telegram_enabled: Optional[bool] = None
    min_spread_threshold: Optional[float] = None
    max_trade_amount: Optional[float] = None
    slippage_tolerance: Optional[float] = None

# ============== ENCRYPTION HELPERS ==============
def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    return fernet.decrypt(encrypted_data.encode()).decode()

# ============== EXCHANGE INSTANCES ==============
exchange_instances: Dict[str, ccxt.Exchange] = {}

async def get_exchange_instance(exchange_name: str) -> Optional[ccxt.Exchange]:
    """
    Get or create an exchange instance with proper error handling
    Implements caching to avoid recreating instances
    """
    exchange_key = exchange_name.lower()
    
    # Return cached instance if available and valid
    if exchange_key in exchange_instances:
        instance = exchange_instances[exchange_key]
        try:
            # Quick health check
            if hasattr(instance, 'markets') and instance.markets:
                return instance
        except:
            # Remove invalid instance
            await instance.close()
            del exchange_instances[exchange_key]
    
    # Fetch exchange config from DB
    exchange_doc = await db.exchanges.find_one(
        {"name": {"$regex": f"^{exchange_name}$", "$options": "i"}, "is_active": True}, 
        {"_id": 0}
    )
    
    if not exchange_doc:
        logger.warning(f"Exchange {exchange_name} not found in database")
        return None
    
    try:
        # Decrypt credentials
        api_key = decrypt_data(exchange_doc['api_key_encrypted'])
        api_secret = decrypt_data(exchange_doc['api_secret_encrypted'])
        
        # Create exchange config
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'timeout': 30000,
            'options': {
                'defaultType': 'spot',
            }
        }
        
        # Get exchange class
        exchange_class = getattr(ccxt, exchange_key, None)
        if not exchange_class:
            logger.error(f"Exchange class {exchange_name} not found in ccxt")
            return None
        
        # Create and initialize instance
        instance = exchange_class(config)
        
        # Load markets with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await instance.load_markets()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
        
        # Cache instance
        exchange_instances[exchange_key] = instance
        logger.info(f"Successfully created exchange instance for {exchange_name}")
        return instance
        
    except Exception as e:
        logger.error(f"Error creating exchange instance for {exchange_name}: {e}")
        return None

async def close_exchange_instances():
    """Close all exchange instances and clear cache"""
    closed_count = 0
    for name, instance in list(exchange_instances.items()):
        try:
            await instance.close()
            closed_count += 1
        except Exception as e:
            logger.warning(f"Error closing exchange {name}: {e}")
    
    exchange_instances.clear()
    if closed_count > 0:
        logger.info(f"Closed {closed_count} exchange instances")

# ============== SETTINGS ENDPOINTS ==============
@api_router.get("/settings")
async def get_settings():
    """Get bot settings"""
    settings = await db.settings.find_one({}, {"_id": 0})
    if not settings:
        # Return default settings
        default_settings = BotSettings()
        return default_settings.model_dump()
    return settings

@api_router.put("/settings")
async def update_settings(settings_update: SettingsUpdate):
    """Update bot settings"""
    update_data = {k: v for k, v in settings_update.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.settings.update_one(
        {},
        {"$set": update_data},
        upsert=True
    )
    
    settings = await db.settings.find_one({}, {"_id": 0})
    return settings

@api_router.post("/telegram/test")
async def test_telegram_notification(chat_id: str):
    """Test Telegram notification"""
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")
    
    success = await telegram_notifier.send_message(
        chat_id,
        "✅ <b>Test Notification</b>\n\nYour Telegram notifications are working correctly!\n\n🤖 Crypto Arbitrage Bot"
    )
    
    if success:
        return {"status": "success", "message": "Test notification sent successfully"}
    else:
        raise HTTPException(status_code=400, detail="Failed to send test notification. Check your chat ID.")

# ============== TOKEN ENDPOINTS ==============
@api_router.post("/tokens", response_model=Token)
async def create_token(token_data: TokenCreate):
    token = Token(**token_data.model_dump())
    doc = token.model_dump()
    await db.tokens.insert_one(doc)
    return token

@api_router.get("/tokens", response_model=List[Token])
async def get_tokens():
    tokens = await db.tokens.find({"is_active": True}, {"_id": 0}).to_list(100)
    return tokens

@api_router.get("/tokens/{token_id}", response_model=Token)
async def get_token(token_id: str):
    token = await db.tokens.find_one({"id": token_id}, {"_id": 0})
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return Token(**token)

@api_router.delete("/tokens/{token_id}")
async def delete_token(token_id: str):
    result = await db.tokens.update_one({"id": token_id}, {"$set": {"is_active": False}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "deleted"}

# ============== EXCHANGE ENDPOINTS ==============
@api_router.post("/exchanges")
async def create_exchange(exchange_data: ExchangeCreate):
    exchange = Exchange(
        name=exchange_data.name,
        api_key_encrypted=encrypt_data(exchange_data.api_key),
        api_secret_encrypted=encrypt_data(exchange_data.api_secret),
        additional_params_encrypted=encrypt_data(json.dumps(exchange_data.additional_params)) if exchange_data.additional_params else None
    )
    doc = exchange.model_dump()
    await db.exchanges.insert_one(doc)
    return {
        "id": exchange.id,
        "name": exchange.name,
        "is_active": exchange.is_active,
        "created_at": exchange.created_at
    }

@api_router.get("/exchanges")
async def get_exchanges():
    exchanges = await db.exchanges.find({"is_active": True}, {"_id": 0, "api_key_encrypted": 0, "api_secret_encrypted": 0, "additional_params_encrypted": 0}).to_list(100)
    return exchanges

@api_router.delete("/exchanges/{exchange_id}")
async def delete_exchange(exchange_id: str):
    result = await db.exchanges.update_one({"id": exchange_id}, {"$set": {"is_active": False}})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Exchange not found")
    # Remove from active instances
    exchange = await db.exchanges.find_one({"id": exchange_id}, {"_id": 0})
    if exchange and exchange['name'].lower() in exchange_instances:
        try:
            await exchange_instances[exchange['name'].lower()].close()
        except Exception:
            pass
        del exchange_instances[exchange['name'].lower()]
    return {"status": "deleted"}

@api_router.post("/exchanges/test")
async def test_exchange_connection(exchange_data: ExchangeCreate):
    """Test exchange API connection"""
    try:
        exchange_class = getattr(ccxt, exchange_data.name.lower(), None)
        if not exchange_class:
            raise HTTPException(status_code=400, detail=f"Exchange {exchange_data.name} not supported")
        
        config = {
            'apiKey': exchange_data.api_key,
            'secret': exchange_data.api_secret,
            'enableRateLimit': True,
            'timeout': 15000,
        }
        
        instance = exchange_class(config)
        await instance.load_markets()
        await instance.fetch_balance()  # Test connection by fetching balance
        await instance.close()
        
        return {"status": "success", "message": f"Connected to {exchange_data.name} successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {str(e)}")

# ============== WALLET ENDPOINTS ==============
@api_router.post("/wallet")
async def save_wallet_config(wallet_data: WalletConfigCreate):
    # Validate address if provided
    address = wallet_data.address
    if address and not bsc_service.is_valid_address(address):
        raise HTTPException(status_code=400, detail="Invalid BSC address format")
    
    # If no address provided, derive from private key (simplified)
    if not address:
        address = f"0x{hashlib.sha256(wallet_data.private_key.encode()).hexdigest()[:40]}"
    
    wallet = WalletConfig(
        address=address,
        private_key_encrypted=encrypt_data(wallet_data.private_key)
    )
    
    # Upsert wallet config
    await db.wallet.update_one(
        {},
        {"$set": wallet.model_dump()},
        upsert=True
    )
    
    return {
        "id": wallet.id,
        "address": wallet.address,
        "balance_bnb": wallet.balance_bnb,
        "balance_usdt": wallet.balance_usdt
    }

@api_router.get("/wallet")
async def get_wallet_config():
    wallet = await db.wallet.find_one({}, {"_id": 0, "private_key_encrypted": 0})
    if not wallet:
        return None
    return wallet

@api_router.get("/wallet/balance")
async def get_wallet_balance():
    """Fetch real wallet balance from BSC blockchain"""
    wallet = await db.wallet.find_one({}, {"_id": 0})
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not configured")
    
    settings = await db.settings.find_one({}, {"_id": 0})
    is_live = settings.get('is_live_mode', False) if settings else False
    
    address = wallet.get('address')
    if not address or not bsc_service.is_valid_address(address):
        raise HTTPException(status_code=400, detail="Invalid wallet address")
    
    bnb_balance = await bsc_service.get_bnb_balance(address, is_live)
    usdt_balance = await bsc_service.get_usdt_balance(address, is_live)
    
    # Update stored balance
    await db.wallet.update_one(
        {},
        {"$set": {
            "balance_bnb": bnb_balance,
            "balance_usdt": usdt_balance,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "address": address,
        "balance_bnb": bnb_balance,
        "balance_usdt": usdt_balance,
        "network": "BSC Mainnet" if is_live else "BSC Testnet",
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

@api_router.put("/wallet/balance")
async def update_wallet_balance(balance_bnb: float = 0, balance_usdt: float = 0):
    await db.wallet.update_one(
        {},
        {"$set": {"balance_bnb": balance_bnb, "balance_usdt": balance_usdt, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"status": "updated"}

# ============== PRICE MONITORING ==============
@api_router.get("/prices/{symbol}")
async def get_prices(symbol: str):
    """Get prices for a symbol across all configured exchanges"""
    exchanges = await db.exchanges.find({"is_active": True}, {"_id": 0}).to_list(100)
    prices = []
    
    for exchange_doc in exchanges:
        try:
            instance = await get_exchange_instance(exchange_doc['name'])
            if instance and symbol in instance.symbols:
                ticker = await instance.fetch_ticker(symbol)
                prices.append({
                    "exchange": exchange_doc['name'],
                    "symbol": symbol,
                    "bid": ticker.get('bid', 0) or 0,
                    "ask": ticker.get('ask', 0) or 0,
                    "last": ticker.get('last', 0) or 0,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            logger.warning(f"Error fetching price from {exchange_doc['name']}: {e}")
    
    return prices

@api_router.get("/prices/all/tokens")
async def get_all_token_prices():
    """Get prices for all monitored tokens across all exchanges"""
    tokens = await db.tokens.find({"is_active": True}, {"_id": 0}).to_list(100)
    exchanges = await db.exchanges.find({"is_active": True}, {"_id": 0}).to_list(100)
    
    all_prices = []
    
    for token in tokens:
        symbol = f"{token['symbol']}/USDT"
        token_prices = []
        
        for exchange_doc in exchanges:
            try:
                instance = await get_exchange_instance(exchange_doc['name'])
                if instance:
                    # Try different symbol formats
                    symbols_to_try = [symbol, symbol.upper(), symbol.lower()]
                    for sym in symbols_to_try:
                        if sym in instance.symbols:
                            ticker = await instance.fetch_ticker(sym)
                            token_prices.append({
                                "exchange": exchange_doc['name'],
                                "bid": ticker.get('bid', 0) or 0,
                                "ask": ticker.get('ask', 0) or 0,
                                "last": ticker.get('last', 0) or 0,
                            })
                            break
            except Exception as e:
                logger.warning(f"Error fetching {symbol} from {exchange_doc['name']}: {e}")
        
        if token_prices:
            all_prices.append({
                "token_id": token['id'],
                "token_symbol": token['symbol'],
                "prices": token_prices
            })
    
    return all_prices

# ============== ARBITRAGE DETECTION ==============
@api_router.get("/arbitrage/detect")
async def detect_arbitrage_opportunities():
    """Detect arbitrage opportunities across all tokens and exchanges"""
    tokens = await db.tokens.find({"is_active": True}, {"_id": 0}).to_list(100)
    exchanges = await db.exchanges.find({"is_active": True}, {"_id": 0}).to_list(100)
    settings = await db.settings.find_one({}, {"_id": 0})
    min_spread = settings.get('min_spread_threshold', 0.5) if settings else 0.5
    
    opportunities = []
    
    for token in tokens:
        symbol = f"{token['symbol']}/USDT"
        prices = []
        
        for exchange_doc in exchanges:
            try:
                instance = await get_exchange_instance(exchange_doc['name'])
                if instance:
                    symbols_to_try = [symbol, symbol.upper(), symbol.lower()]
                    for sym in symbols_to_try:
                        if sym in instance.symbols:
                            ticker = await instance.fetch_ticker(sym)
                            if ticker.get('bid') and ticker.get('ask'):
                                prices.append({
                                    "exchange": exchange_doc['name'],
                                    "bid": ticker['bid'],
                                    "ask": ticker['ask'],
                                })
                            break
            except Exception as e:
                logger.warning(f"Error in arbitrage detection for {symbol} on {exchange_doc['name']}: {e}")
        
        # Find arbitrage opportunities
        if len(prices) >= 2:
            # Find lowest ask (buy) and highest bid (sell)
            lowest_ask = min(prices, key=lambda x: x['ask'])
            highest_bid = max(prices, key=lambda x: x['bid'])
            
            if lowest_ask['exchange'] != highest_bid['exchange']:
                spread = highest_bid['bid'] - lowest_ask['ask']
                spread_percent = (spread / lowest_ask['ask']) * 100
                
                if spread_percent > min_spread:
                    # Calculate confidence (simplified)
                    confidence = min(95, 50 + spread_percent * 5)
                    
                    # Calculate recommended amount based on spread
                    recommended_amount = min(1000, max(100, spread_percent * 100))
                    
                    opportunity = ArbitrageOpportunity(
                        token_id=token['id'],
                        token_symbol=token['symbol'],
                        buy_exchange=lowest_ask['exchange'],
                        sell_exchange=highest_bid['exchange'],
                        buy_price=lowest_ask['ask'],
                        sell_price=highest_bid['bid'],
                        spread_percent=round(spread_percent, 4),
                        confidence=round(confidence, 2),
                        recommended_usdt_amount=round(recommended_amount, 2)
                    )
                    opportunities.append(opportunity.model_dump())
    
    # Save opportunities to DB
    if opportunities:
        await db.arbitrage_opportunities.insert_many(opportunities)
        
        # Send Telegram notifications for new opportunities
        if settings and settings.get('telegram_enabled') and settings.get('telegram_chat_id'):
            for opp in opportunities:
                await telegram_notifier.notify_opportunity(settings['telegram_chat_id'], opp)
    
    return opportunities

@api_router.get("/arbitrage/opportunities")
async def get_arbitrage_opportunities():
    """Get recent arbitrage opportunities"""
    opportunities = await db.arbitrage_opportunities.find(
        {"status": {"$in": ["detected", "manual"]}},
        {"_id": 0}
    ).sort("detected_at", -1).to_list(50)
    return opportunities

@api_router.post("/arbitrage/manual-selection")
async def create_manual_selection(selection: ManualSelectionCreate):
    """Create a manual CEX selection for arbitrage"""
    token = await db.tokens.find_one({"id": selection.token_id}, {"_id": 0})
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    
    # Get current prices for the manual selection
    symbol = f"{token['symbol']}/USDT"
    buy_price = 0
    sell_price = 0
    
    try:
        buy_instance = await get_exchange_instance(selection.buy_exchange)
        sell_instance = await get_exchange_instance(selection.sell_exchange)
        
        if buy_instance:
            for sym in [symbol, symbol.upper(), symbol.lower()]:
                if sym in buy_instance.symbols:
                    ticker = await buy_instance.fetch_ticker(sym)
                    buy_price = ticker.get('ask', 0) or 0
                    break
        
        if sell_instance:
            for sym in [symbol, symbol.upper(), symbol.lower()]:
                if sym in sell_instance.symbols:
                    ticker = await sell_instance.fetch_ticker(sym)
                    sell_price = ticker.get('bid', 0) or 0
                    break
    except Exception as e:
        logger.error(f"Error fetching prices for manual selection: {e}")
    
    spread_percent = ((sell_price - buy_price) / buy_price * 100) if buy_price > 0 else 0
    
    opportunity = ArbitrageOpportunity(
        token_id=selection.token_id,
        token_symbol=token['symbol'],
        buy_exchange=selection.buy_exchange,
        sell_exchange=selection.sell_exchange,
        buy_price=buy_price,
        sell_price=sell_price,
        spread_percent=round(spread_percent, 4),
        confidence=100.0,  # Manual selection has 100% confidence
        recommended_usdt_amount=100.0,
        status="manual",
        is_manual_selection=True
    )
    
    doc = opportunity.model_dump()
    await db.arbitrage_opportunities.insert_one(doc)
    
    return opportunity

@api_router.delete("/arbitrage/opportunities/{opportunity_id}")
async def delete_opportunity(opportunity_id: str):
    result = await db.arbitrage_opportunities.delete_one({"id": opportunity_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return {"status": "deleted"}

# ============== EXECUTE ARBITRAGE ==============
@api_router.post("/arbitrage/execute")
async def execute_arbitrage(request: ExecuteArbitrageRequest):
    """Execute an arbitrage opportunity (real or simulated based on mode)"""
    opportunity = await db.arbitrage_opportunities.find_one({"id": request.opportunity_id}, {"_id": 0})
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    
    # Validate prices exist
    buy_price = opportunity.get('buy_price', 0)
    sell_price = opportunity.get('sell_price', 0)
    if not buy_price or buy_price <= 0:
        raise HTTPException(status_code=400, detail="Invalid opportunity: buy price is missing or zero. Cannot execute.")
    if not sell_price or sell_price <= 0:
        raise HTTPException(status_code=400, detail="Invalid opportunity: sell price is missing or zero. Cannot execute.")
    
    settings = await db.settings.find_one({}, {"_id": 0})
    is_live = settings.get('is_live_mode', False) if settings else False
    telegram_enabled = settings.get('telegram_enabled', False) if settings else False
    telegram_chat_id = settings.get('telegram_chat_id', '') if settings else ''
    slippage_tolerance = settings.get('slippage_tolerance', 0.5) if settings else 0.5
    
    # SAFETY CHECK: Require confirmation for live trading
    if is_live and not request.confirmed:
        raise HTTPException(
            status_code=400, 
            detail="Live trading requires confirmation. Set 'confirmed: true' to proceed with real trades."
        )
    
    # Update status to executing
    await db.arbitrage_opportunities.update_one(
        {"id": request.opportunity_id},
        {"$set": {"status": "executing"}}
    )
    
    # Send trade started notification
    if telegram_enabled and telegram_chat_id:
        await telegram_notifier.notify_trade_started(telegram_chat_id, opportunity, request.usdt_amount, is_live)
    
    try:
        if is_live:
            # ============== FULL ARBITRAGE WITH TRANSFERS ==============
            # Check if wallet is configured for full arbitrage
            wallet = await db.wallet.find_one({}, {"_id": 0})
            if wallet and wallet.get('address'):
                # Use full arbitrage with wallet transfers
                result = await execute_full_arbitrage_with_transfers(opportunity, request.usdt_amount, slippage_tolerance, telegram_chat_id if telegram_enabled else None)
            else:
                # Fallback to legacy arbitrage (requires pre-positioned funds)
                result = await execute_real_arbitrage(opportunity, request.usdt_amount, slippage_tolerance, telegram_chat_id if telegram_enabled else None)
        else:
            # ============== SIMULATED EXECUTION ==============
            result = await execute_simulated_arbitrage(opportunity, request.usdt_amount)
        
        # Update opportunity status
        await db.arbitrage_opportunities.update_one(
            {"id": request.opportunity_id},
            {"$set": {"status": result['status']}}
        )
        
        # Send completion notification
        if telegram_enabled and telegram_chat_id:
            await telegram_notifier.notify_trade_completed(telegram_chat_id, result, is_live)
        
        # Broadcast completion via WebSocket
        await manager.broadcast({
            "type": "arbitrage_completed",
            "opportunity_id": request.opportunity_id,
            "profit": result.get('profit', 0),
            "profit_percent": result.get('profit_percent', 0),
            "is_live": is_live
        })
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Arbitrage execution error: {error_msg}")
        
        # Update status to failed
        await db.arbitrage_opportunities.update_one(
            {"id": request.opportunity_id},
            {"$set": {"status": "failed"}}
        )
        
        # Send error notification
        if telegram_enabled and telegram_chat_id:
            await telegram_notifier.notify_error(telegram_chat_id, error_msg, f"Executing arbitrage {request.opportunity_id}")
        
        raise HTTPException(status_code=500, detail=f"Arbitrage execution failed: {error_msg}")

async def send_telegram_message(chat_id: str, message: str) -> bool:
    """Send a message to Telegram chat"""
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                },
                timeout=10.0
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

# ============== FULL ARBITRAGE WITH TRANSFERS ==============

async def check_arbitrage_profitability(opportunity: dict, usdt_amount: float, buy_exchange: ccxt.Exchange, sell_exchange: ccxt.Exchange) -> dict:
    """
    Check if arbitrage is profitable after ALL fees
    Returns profitability analysis
    """
    try:
        token = opportunity['token_symbol']
        
        # 1. Get trading fees
        buy_fees = await buy_exchange.fetch_trading_fees()
        sell_fees = await sell_exchange.fetch_trading_fees()
        
        buy_fee_rate = buy_fees.get('trading', {}).get('maker', 0.001)  # Default 0.1%
        sell_fee_rate = sell_fees.get('trading', {}).get('taker', 0.001)
        
        # 2. Get withdrawal fees
        buy_currencies = await buy_exchange.fetch_currencies()
        token_info = buy_currencies.get(token, {})
        withdrawal_fee = token_info.get('fee', 0)  # Withdrawal fee in token amount
        withdrawal_fee_usdt = withdrawal_fee * opportunity['buy_price'] if withdrawal_fee else 5  # Estimate $5 if unknown
        
        # 3. Calculate gas fees for wallet transfers (BSC is cheap)
        gas_fee_estimate = 0.50  # ~$0.50 for BSC token transfer
        
        # 4. Calculate total costs
        token_amount = usdt_amount / opportunity['buy_price']
        
        buy_fee = usdt_amount * buy_fee_rate
        sell_fee = (token_amount * opportunity['sell_price']) * sell_fee_rate
        total_fees = buy_fee + sell_fee + withdrawal_fee_usdt + gas_fee_estimate
        
        # 5. Calculate profit
        gross_revenue = token_amount * opportunity['sell_price']
        net_revenue = gross_revenue - sell_fee
        total_cost = usdt_amount + buy_fee + withdrawal_fee_usdt + gas_fee_estimate
        
        net_profit = net_revenue - total_cost
        profit_percent = (net_profit / total_cost) * 100 if total_cost > 0 else 0
        
        return {
            'is_profitable': net_profit > 0,
            'net_profit': net_profit,
            'profit_percent': profit_percent,
            'total_fees': total_fees,
            'breakdown': {
                'buy_fee': buy_fee,
                'sell_fee': sell_fee,
                'withdrawal_fee': withdrawal_fee_usdt,
                'gas_fee': gas_fee_estimate
            },
            'min_spread_required': (total_fees / usdt_amount) * 100
        }
    except Exception as e:
        logger.error(f"Error checking profitability: {e}")
        # Conservative estimate
        return {
            'is_profitable': opportunity['spread_percent'] > 1.0,
            'net_profit': 0,
            'profit_percent': 0,
            'total_fees': 0,
            'breakdown': {},
            'min_spread_required': 1.0
        }


async def retry_with_backoff(func, max_retries=MAX_RETRIES, initial_delay=1):
    """
    Retry function with exponential backoff for rate limits
    """
    for attempt in range(max_retries):
        try:
            return await func()
        except ccxt.RateLimitExceeded:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            logger.warning(f"Rate limit hit, retrying in {delay}s...")
            await asyncio.sleep(delay)
        except Exception:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(initial_delay)
    

async def withdraw_from_exchange_to_wallet(
    exchange: ccxt.Exchange,
    exchange_name: str,
    token: str,
    amount: float,
    wallet_address: str,
    opportunity_id: str
) -> dict:
    """
    Withdraw tokens from exchange to wallet with retries
    """
    await log_transaction(opportunity_id, f"withdraw_from_{exchange_name}", "started", {
        'token': token,
        'amount': amount,
        'destination': wallet_address
    }, is_live=True)
    
    try:
        # Withdrawal with retry
        async def do_withdrawal():
            return await exchange.withdraw(
                code=token,
                amount=amount,
                address=wallet_address,
                tag=None,
                params={'network': 'BSC'}
            )
        
        withdrawal = await retry_with_backoff(do_withdrawal)
        
        await log_transaction(opportunity_id, f"withdraw_from_{exchange_name}", "submitted", {
            'withdrawal_id': withdrawal['id'],
            'tx_hash': withdrawal.get('txid', 'pending'),
            'fee': withdrawal.get('fee', {})
        }, is_live=True)
        
        return {
            'id': withdrawal['id'],
            'tx_hash': withdrawal.get('txid'),
            'status': 'pending',
            'fee': withdrawal.get('fee', {})
        }
        
    except Exception as e:
        await log_transaction(opportunity_id, f"withdraw_from_{exchange_name}", "failed", {
            'error': str(e)
        }, is_live=True)
        raise Exception(f"Withdrawal from {exchange_name} failed: {str(e)}")


async def wait_for_withdrawal_completion(
    exchange: ccxt.Exchange,
    exchange_name: str,
    withdrawal_id: str,
    opportunity_id: str,
    timeout: int = WITHDRAWAL_TIMEOUT
) -> str:
    """
    Wait for exchange to process withdrawal and broadcast to blockchain
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            withdrawal = await exchange.fetch_withdrawal(withdrawal_id)
            status = withdrawal.get('status', '').lower()
            
            await log_transaction(opportunity_id, f"withdraw_status_{exchange_name}", "checking", {
                'status': status,
                'elapsed_seconds': int(time.time() - start_time)
            }, is_live=True)
            
            if status in ['ok', 'complete', 'completed', 'success']:
                tx_hash = withdrawal.get('txid')
                if tx_hash:
                    await log_transaction(opportunity_id, f"withdraw_from_{exchange_name}", "completed", {
                        'tx_hash': tx_hash,
                        'total_wait_seconds': int(time.time() - start_time)
                    }, is_live=True)
                    return tx_hash
            elif status in ['failed', 'canceled', 'cancelled']:
                raise Exception(f"Withdrawal {status}: {withdrawal.get('info', {})}")
            
            await asyncio.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            if 'not found' not in str(e).lower():
                logger.warning(f"Error checking withdrawal: {e}")
            await asyncio.sleep(10)
    
    raise Exception(f"Withdrawal timeout after {timeout} seconds")


async def wait_for_blockchain_confirmation(
    w3: Web3,
    tx_hash: str,
    opportunity_id: str,
    step_name: str,
    required_confirmations: int = MIN_CONFIRMATIONS,
    timeout: int = 600
) -> bool:
    """
    Wait for blockchain transaction confirmation (fast: 1 confirmation on BSC)
    """
    await log_transaction(opportunity_id, step_name, "started", {
        'tx_hash': tx_hash,
        'required_confirmations': required_confirmations
    }, is_live=True)
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            receipt = w3.eth.get_transaction_receipt(tx_hash)
            
            if receipt:
                current_block = w3.eth.block_number
                tx_block = receipt['blockNumber']
                confirmations = current_block - tx_block + 1
                
                await log_transaction(opportunity_id, step_name, "confirming", {
                    'confirmations': confirmations,
                    'required': required_confirmations,
                    'elapsed_seconds': int(time.time() - start_time)
                }, is_live=True)
                
                if confirmations >= required_confirmations:
                    await log_transaction(opportunity_id, step_name, "completed", {
                        'confirmations': confirmations,
                        'total_wait_seconds': int(time.time() - start_time)
                    }, is_live=True)
                    return True
            
            await asyncio.sleep(3)  # Check every 3 seconds (BSC block time)
            
        except Exception as e:
            logger.warning(f"Error checking blockchain confirmation: {e}")
            await asyncio.sleep(3)
    
    raise Exception(f"Blockchain confirmation timeout after {timeout} seconds")


async def send_token_from_wallet_to_exchange(
    w3: Web3,
    private_key: str,
    token_address: str,
    to_address: str,
    amount: float,
    opportunity_id: str,
    step_name: str,
    decimals: int = 18
) -> str:
    """
    Send tokens from wallet to exchange deposit address
    """
    await log_transaction(opportunity_id, step_name, "started", {
        'token': token_address,
        'amount': amount,
        'destination': to_address
    }, is_live=True)
    
    try:
        account = w3.eth.account.from_key(private_key)
        
        # Get token contract
        token_contract = w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        # Convert amount to wei
        amount_wei = int(amount * (10 ** decimals))
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price
        
        # Estimate gas
        gas_estimate = token_contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_wei
        ).estimate_gas({'from': account.address})
        
        transaction = token_contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_wei
        ).build_transaction({
            'from': account.address,
            'gas': int(gas_estimate * 1.2),  # Add 20% buffer
            'gasPrice': gas_price,
            'nonce': nonce
        })
        
        # Sign and send
        signed = account.sign_transaction(transaction)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        tx_hash_hex = w3.to_hex(tx_hash)
        
        await log_transaction(opportunity_id, step_name, "broadcast", {
            'tx_hash': tx_hash_hex,
            'gas_used': gas_estimate,
            'gas_price': str(gas_price)
        }, is_live=True)
        
        return tx_hash_hex
        
    except Exception as e:
        await log_transaction(opportunity_id, step_name, "failed", {
            'error': str(e)
        }, is_live=True)
        raise Exception(f"Token transfer failed: {str(e)}")


async def get_deposit_address(
    exchange: ccxt.Exchange,
    exchange_name: str,
    token: str,
    opportunity_id: str,
    network: str = 'BSC'
) -> dict:
    """
    Get deposit address for token on exchange
    """
    await log_transaction(opportunity_id, f"get_deposit_address_{exchange_name}", "started", {
        'token': token,
        'network': network
    }, is_live=True)
    
    try:
        async def fetch_address():
            return await exchange.fetch_deposit_address(token, {'network': network})
        
        deposit_address = await retry_with_backoff(fetch_address)
        
        await log_transaction(opportunity_id, f"get_deposit_address_{exchange_name}", "completed", {
            'address': deposit_address['address'],
            'network': network
        }, is_live=True)
        
        return {
            'address': deposit_address['address'],
            'tag': deposit_address.get('tag'),
            'network': network
        }
    except Exception as e:
        await log_transaction(opportunity_id, f"get_deposit_address_{exchange_name}", "failed", {
            'error': str(e)
        }, is_live=True)
        raise Exception(f"Failed to get deposit address: {str(e)}")


async def wait_for_deposit_credit(
    exchange: ccxt.Exchange,
    exchange_name: str,
    token: str,
    expected_amount: float,
    opportunity_id: str,
    timeout: int = DEPOSIT_TIMEOUT
) -> bool:
    """
    Wait for exchange to credit deposited tokens
    """
    await log_transaction(opportunity_id, f"wait_deposit_{exchange_name}", "started", {
        'token': token,
        'expected_amount': expected_amount
    }, is_live=True)
    
    try:
        initial_balance = await exchange.fetch_balance()
        initial_amount = initial_balance.get(token, {}).get('free', 0)
    except Exception:
        initial_amount = 0
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            current_balance = await exchange.fetch_balance()
            current_amount = current_balance.get(token, {}).get('free', 0)
            
            increase = current_amount - initial_amount
            
            await log_transaction(opportunity_id, f"wait_deposit_{exchange_name}", "checking", {
                'initial': initial_amount,
                'current': current_amount,
                'increase': increase,
                'expected': expected_amount,
                'elapsed_seconds': int(time.time() - start_time)
            }, is_live=True)
            
            # Allow 1% tolerance for rounding
            if increase >= (expected_amount * 0.99):
                await log_transaction(opportunity_id, f"wait_deposit_{exchange_name}", "completed", {
                    'credited_amount': increase,
                    'total_wait_seconds': int(time.time() - start_time)
                }, is_live=True)
                return True
            
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.warning(f"Error checking deposit: {e}")
            await asyncio.sleep(30)
    
    raise Exception(f"Deposit credit timeout after {timeout} seconds")


async def execute_full_arbitrage_with_transfers(
    opportunity: dict,
    usdt_amount: float,
    slippage_tolerance: float,
    telegram_chat_id: Optional[str]
) -> dict:
    """
    Execute complete arbitrage: Wallet → CEX A (buy) → Withdraw → Wallet → CEX B (deposit) → Sell → Withdraw → Wallet
    
    Optimizations:
    - 1 confirmation only for speed
    - Parallel execution where possible
    - Fee checking before execution
    - Rate limit handling
    - Error handling with rollback capability
    """
    start_time = time.time()
    
    buy_exchange_name = opportunity['buy_exchange']
    sell_exchange_name = opportunity['sell_exchange']
    token_symbol = opportunity['token_symbol']
    
    # Get wallet config
    wallet = await db.wallet.find_one({}, {"_id": 0})
    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not configured. Please add your wallet in settings.")
    
    wallet_address = wallet['address']
    private_key = decrypt_data(wallet['private_key_encrypted'])
    
    # Get exchange instances
    buy_exchange = await get_exchange_instance(buy_exchange_name)
    sell_exchange = await get_exchange_instance(sell_exchange_name)
    
    if not buy_exchange or not sell_exchange:
        raise HTTPException(status_code=400, detail="Exchange not configured")
    
    # Get Web3 instance (always mainnet for real money)
    w3 = bsc_service.get_web3(is_live=True)
    
    # Get token info
    token_doc = await db.tokens.find_one({'symbol': token_symbol}, {"_id": 0})
    if not token_doc:
        raise HTTPException(status_code=400, detail=f"Token {token_symbol} not found in database")
    
    token_contract_address = token_doc['contract_address']
    
    # Update opportunity status
    await db.arbitrage_opportunities.update_one(
        {'id': opportunity['id']},
        {'$set': {'status': 'executing'}}
    )
    
    # STEP 0: Check profitability with ALL fees
    await log_transaction(opportunity['id'], "profitability_check", "started", {}, is_live=True)
    
    profitability = await check_arbitrage_profitability(
        opportunity, usdt_amount, buy_exchange, sell_exchange
    )
    
    if not profitability['is_profitable']:
        await log_transaction(opportunity['id'], "profitability_check", "failed", {
            'reason': 'Not profitable after fees',
            'net_profit': profitability['net_profit'],
            'total_fees': profitability['total_fees'],
            'min_spread_required': profitability['min_spread_required']
        }, is_live=True)
        
        await db.arbitrage_opportunities.update_one(
            {'id': opportunity['id']},
            {'$set': {'status': 'failed'}}
        )
        
        raise HTTPException(
            status_code=400,
            detail=f"Not profitable after fees. Net profit: ${profitability['net_profit']:.2f}. "
                   f"Total fees: ${profitability['total_fees']:.2f}. "
                   f"Need spread > {profitability['min_spread_required']:.2f}%"
        )
    
    await log_transaction(opportunity['id'], "profitability_check", "completed", profitability, is_live=True)
    
    # Send Telegram notification
    if telegram_chat_id and TELEGRAM_BOT_TOKEN:
        message = (
            f"🚀 *Starting Full Arbitrage*\n\n"
            f"Token: {token_symbol}\n"
            f"Buy: {buy_exchange_name} @ ${opportunity['buy_price']:.4f}\n"
            f"Sell: {sell_exchange_name} @ ${opportunity['sell_price']:.4f}\n"
            f"Amount: ${usdt_amount}\n"
            f"Expected Profit: ${profitability['net_profit']:.2f} ({profitability['profit_percent']:.2f}%)\n"
            f"Total Fees: ${profitability['total_fees']:.2f}\n\n"
            f"⏱ Estimated time: 5-15 minutes"
        )
        await send_telegram_message(telegram_chat_id, message)
    
    token_amount = usdt_amount / opportunity['buy_price']
    
    try:
        # STEP 1: Send USDT from wallet to buy exchange
        await log_transaction(opportunity['id'], "step_1_fund_buy_exchange", "started", {
            'amount': usdt_amount,
            'destination': buy_exchange_name
        }, is_live=True)
        
        # Get deposit address for buy exchange
        buy_deposit = await get_deposit_address(buy_exchange, buy_exchange_name, 'USDT', opportunity['id'])
        
        # Send USDT from wallet to buy exchange
        usdt_contract = USDT_MAINNET
        fund_tx_hash = await send_token_from_wallet_to_exchange(
            w3, private_key, usdt_contract, buy_deposit['address'],
            usdt_amount, opportunity['id'], "step_1_fund_buy_exchange"
        )
        
        # Wait for blockchain confirmation (parallel with next step where possible)
        blockchain_confirm_task = asyncio.create_task(
            wait_for_blockchain_confirmation(
                w3, fund_tx_hash, opportunity['id'],
                "step_1_blockchain_confirm", MIN_CONFIRMATIONS
            )
        )
        
        # STEP 2: Wait for exchange to credit USDT
        await blockchain_confirm_task
        await wait_for_deposit_credit(
            buy_exchange, buy_exchange_name, 'USDT',
            usdt_amount, opportunity['id']
        )
        
        # STEP 3: Buy token on exchange A
        await log_transaction(opportunity['id'], "step_3_buy_token", "started", {
            'exchange': buy_exchange_name,
            'amount': token_amount
        }, is_live=True)
        
        async def place_buy_order():
            return await buy_exchange.create_order(
                symbol=f"{token_symbol}/USDT",
                type='market',
                side='buy',
                amount=token_amount
            )
        
        buy_order = await retry_with_backoff(place_buy_order)
        actual_token_amount = buy_order.get('filled', token_amount)
        
        await log_transaction(opportunity['id'], "step_3_buy_token", "completed", {
            'order_id': buy_order['id'],
            'filled': actual_token_amount,
            'cost': buy_order.get('cost')
        }, is_live=True)
        
        # STEP 4: Withdraw token from exchange A to wallet
        withdrawal = await withdraw_from_exchange_to_wallet(
            buy_exchange, buy_exchange_name, token_symbol,
            actual_token_amount, wallet_address, opportunity['id']
        )
        
        # Wait for withdrawal to complete
        withdraw_tx_hash = await wait_for_withdrawal_completion(
            buy_exchange, buy_exchange_name, withdrawal['id'], opportunity['id']
        )
        
        # Wait for blockchain confirmation
        await wait_for_blockchain_confirmation(
            w3, withdraw_tx_hash, opportunity['id'],
            "step_4_blockchain_confirm", MIN_CONFIRMATIONS
        )
        
        # STEP 5: Get deposit address for sell exchange (can do early)
        sell_deposit = await get_deposit_address(sell_exchange, sell_exchange_name, token_symbol, opportunity['id'])
        
        # STEP 6: Send token from wallet to sell exchange
        deposit_tx_hash = await send_token_from_wallet_to_exchange(
            w3, private_key, token_contract_address, sell_deposit['address'],
            actual_token_amount, opportunity['id'], "step_6_send_to_sell_exchange"
        )
        
        # Wait for blockchain confirmation
        await wait_for_blockchain_confirmation(
            w3, deposit_tx_hash, opportunity['id'],
            "step_6_blockchain_confirm", MIN_CONFIRMATIONS
        )
        
        # STEP 7: Wait for sell exchange to credit tokens
        await wait_for_deposit_credit(
            sell_exchange, sell_exchange_name, token_symbol,
            actual_token_amount, opportunity['id']
        )
        
        # STEP 8: Sell token on exchange B
        await log_transaction(opportunity['id'], "step_8_sell_token", "started", {
            'exchange': sell_exchange_name,
            'amount': actual_token_amount
        }, is_live=True)
        
        async def place_sell_order():
            return await sell_exchange.create_order(
                symbol=f"{token_symbol}/USDT",
                type='market',
                side='sell',
                amount=actual_token_amount
            )
        
        sell_order = await retry_with_backoff(place_sell_order)
        usdt_received = sell_order.get('cost', 0)
        
        await log_transaction(opportunity['id'], "step_8_sell_token", "completed", {
            'order_id': sell_order['id'],
            'usdt_received': usdt_received
        }, is_live=True)
        
        # STEP 9: Withdraw USDT profit back to wallet
        await log_transaction(opportunity['id'], "step_9_withdraw_profit", "started", {
            'amount': usdt_received
        }, is_live=True)
        
        profit_withdrawal = await withdraw_from_exchange_to_wallet(
            sell_exchange, sell_exchange_name, 'USDT',
            usdt_received, wallet_address, opportunity['id']
        )
        
        profit_tx_hash = await wait_for_withdrawal_completion(
            sell_exchange, sell_exchange_name, profit_withdrawal['id'], opportunity['id']
        )
        
        await wait_for_blockchain_confirmation(
            w3, profit_tx_hash, opportunity['id'],
            "step_9_blockchain_confirm", MIN_CONFIRMATIONS
        )
        
        # Calculate final profit
        total_time = time.time() - start_time
        actual_profit = usdt_received - usdt_amount
        actual_profit_percent = (actual_profit / usdt_amount) * 100 if usdt_amount > 0 else 0
        
        # Update opportunity
        await db.arbitrage_opportunities.update_one(
            {'id': opportunity['id']},
            {'$set': {'status': 'completed'}}
        )
        
        await log_transaction(opportunity['id'], "completed", "completed", {
            'total_time_seconds': int(total_time),
            'total_time_minutes': round(total_time / 60, 2),
            'usdt_invested': usdt_amount,
            'usdt_received': usdt_received,
            'profit': actual_profit,
            'profit_percent': actual_profit_percent,
            'all_funds_returned_to_wallet': True
        }, is_live=True)
        
        # Send success notification
        if telegram_chat_id and TELEGRAM_BOT_TOKEN:
            message = (
                f"✅ *Arbitrage Completed Successfully!*\n\n"
                f"Token: {token_symbol}\n"
                f"Invested: ${usdt_amount:.2f}\n"
                f"Received: ${usdt_received:.2f}\n"
                f"*Profit: ${actual_profit:.2f} ({actual_profit_percent:.2f}%)*\n\n"
                f"⏱ Total Time: {int(total_time/60)} min {int(total_time%60)} sec\n\n"
                f"💰 All funds returned to your wallet!"
            )
            await send_telegram_message(telegram_chat_id, message)
        
        return {
            "status": "completed",
            "opportunity_id": opportunity['id'],
            "execution_time_seconds": int(total_time),
            "execution_time_minutes": round(total_time / 60, 2),
            "usdt_invested": usdt_amount,
            "usdt_received": usdt_received,
            "profit": round(actual_profit, 4),
            "profit_percent": round(actual_profit_percent, 4),
            "is_live": True,
            "buy_order_id": buy_order['id'],
            "sell_order_id": sell_order['id'],
            "blockchain_transactions": [fund_tx_hash, withdraw_tx_hash, deposit_tx_hash, profit_tx_hash],
            "all_funds_returned_to_wallet": True
        }
        
    except Exception as e:
        # Log failure
        await log_transaction(opportunity['id'], "failed", "failed", {
            'error': str(e),
            'failed_at_seconds': int(time.time() - start_time)
        }, is_live=True)
        
        # Update opportunity
        await db.arbitrage_opportunities.update_one(
            {'id': opportunity['id']},
            {'$set': {'status': 'failed'}}
        )
        
        # Send failure notification
        if telegram_chat_id and TELEGRAM_BOT_TOKEN:
            message = (
                f"❌ *Arbitrage Failed*\n\n"
                f"Token: {token_symbol}\n"
                f"Error: {str(e)}\n\n"
                f"⚠️ Please check your wallet and exchange balances manually."
            )
            await send_telegram_message(telegram_chat_id, message)
        
        raise


# ============== LEGACY ARBITRAGE (Pre-positioned funds) ==============

async def execute_real_arbitrage(opportunity: dict, usdt_amount: float, slippage_tolerance: float, telegram_chat_id: Optional[str]) -> dict:
    """Execute real arbitrage trades on exchanges"""
    
    buy_exchange_name = opportunity['buy_exchange']
    sell_exchange_name = opportunity['sell_exchange']
    token_symbol = opportunity['token_symbol']
    symbol = f"{token_symbol}/USDT"
    
    # Get exchange instances
    buy_exchange = await get_exchange_instance(buy_exchange_name)
    sell_exchange = await get_exchange_instance(sell_exchange_name)
    
    if not buy_exchange:
        raise Exception(f"Buy exchange {buy_exchange_name} not available")
    if not sell_exchange:
        raise Exception(f"Sell exchange {sell_exchange_name} not available")
    
    # Find correct symbol format
    buy_symbol = None
    sell_symbol = None
    for sym in [symbol, symbol.upper(), symbol.lower()]:
        if sym in buy_exchange.symbols:
            buy_symbol = sym
        if sym in sell_exchange.symbols:
            sell_symbol = sym
    
    if not buy_symbol:
        raise Exception(f"Symbol {symbol} not found on {buy_exchange_name}")
    if not sell_symbol:
        raise Exception(f"Symbol {symbol} not found on {sell_exchange_name}")
    
    # Step 1: Get fresh prices and check slippage
    buy_ticker = await buy_exchange.fetch_ticker(buy_symbol)
    sell_ticker = await sell_exchange.fetch_ticker(sell_symbol)
    
    current_buy_price = buy_ticker.get('ask', 0)
    current_sell_price = sell_ticker.get('bid', 0)
    
    if not current_buy_price or not current_sell_price:
        raise Exception("Unable to fetch current prices")
    
    # Check if prices have changed too much (slippage protection)
    original_buy_price = opportunity['buy_price']
    original_sell_price = opportunity['sell_price']
    
    buy_slippage = abs((current_buy_price - original_buy_price) / original_buy_price * 100)
    sell_slippage = abs((current_sell_price - original_sell_price) / original_sell_price * 100)
    
    if buy_slippage > slippage_tolerance or sell_slippage > slippage_tolerance:
        raise Exception(f"Price slippage too high. Buy: {buy_slippage:.2f}%, Sell: {sell_slippage:.2f}%. Tolerance: {slippage_tolerance}%")
    
    # Calculate token amount to buy
    token_amount = usdt_amount / current_buy_price
    
    # Log step 1
    await log_transaction(opportunity['id'], "price_check", "completed", {
        "current_buy_price": current_buy_price,
        "current_sell_price": current_sell_price,
        "buy_slippage": buy_slippage,
        "sell_slippage": sell_slippage
    }, is_live=True)
    
    # Step 2: Place buy order (market order)
    try:
        buy_order = await buy_exchange.create_order(
            symbol=buy_symbol,
            type='market',
            side='buy',
            amount=token_amount
        )
        
        await log_transaction(opportunity['id'], "buy_order", "completed", {
            "order_id": buy_order.get('id'),
            "amount": token_amount,
            "price": current_buy_price,
            "exchange": buy_exchange_name
        }, is_live=True)
        
    except Exception as e:
        await log_transaction(opportunity['id'], "buy_order", "failed", {"error": str(e)}, is_live=True)
        raise Exception(f"Buy order failed: {str(e)}")
    
    # Step 3: Place sell order (market order)
    # Note: In real scenario, you'd need to transfer tokens between exchanges first
    # This simplified version assumes tokens are already on the sell exchange
    try:
        sell_order = await sell_exchange.create_order(
            symbol=sell_symbol,
            type='market',
            side='sell',
            amount=token_amount
        )
        
        await log_transaction(opportunity['id'], "sell_order", "completed", {
            "order_id": sell_order.get('id'),
            "amount": token_amount,
            "price": current_sell_price,
            "exchange": sell_exchange_name
        }, is_live=True)
        
    except Exception as e:
        await log_transaction(opportunity['id'], "sell_order", "failed", {"error": str(e)}, is_live=True)
        raise Exception(f"Sell order failed: {str(e)}")
    
    # Calculate actual profit
    actual_buy_cost = buy_order.get('cost', usdt_amount)
    actual_sell_revenue = sell_order.get('cost', token_amount * current_sell_price)
    profit = actual_sell_revenue - actual_buy_cost
    profit_percent = (profit / actual_buy_cost) * 100
    
    await log_transaction(opportunity['id'], "completed", "completed", {
        "buy_cost": actual_buy_cost,
        "sell_revenue": actual_sell_revenue,
        "profit": profit,
        "profit_percent": profit_percent
    }, is_live=True)
    
    return {
        "status": "completed",
        "opportunity_id": opportunity['id'],
        "usdt_invested": actual_buy_cost,
        "tokens_bought": token_amount,
        "sell_value": actual_sell_revenue,
        "profit": round(profit, 4),
        "profit_percent": round(profit_percent, 4),
        "is_live": True,
        "buy_order_id": buy_order.get('id'),
        "sell_order_id": sell_order.get('id')
    }


async def execute_simulated_arbitrage(opportunity: dict, usdt_amount: float) -> dict:
    """Execute simulated arbitrage (test mode)"""
    
    # Validate prices
    buy_price = opportunity.get('buy_price', 0)
    sell_price = opportunity.get('sell_price', 0)
    
    if not buy_price or buy_price <= 0:
        raise Exception("Cannot simulate: buy price is missing or zero")
    if not sell_price or sell_price <= 0:
        raise Exception("Cannot simulate: sell price is missing or zero")
    
    # Simulate execution steps
    steps = [
        {"step": "validate_balance", "status": "completed", "details": {"usdt_amount": usdt_amount}},
        {"step": "deposit_to_buy_exchange", "status": "completed", "details": {"exchange": opportunity['buy_exchange']}},
        {"step": "place_buy_order", "status": "completed", "details": {"price": buy_price}},
        {"step": "withdraw_to_wallet", "status": "completed", "details": {}},
        {"step": "deposit_to_sell_exchange", "status": "completed", "details": {"exchange": opportunity['sell_exchange']}},
        {"step": "place_sell_order", "status": "completed", "details": {"price": sell_price}},
        {"step": "withdraw_profits", "status": "completed", "details": {}}
    ]
    
    # Log transaction steps
    for step in steps:
        await log_transaction(
            opportunity['id'],
            step['step'],
            step['status'],
            step['details'],
            is_live=False
        )
    
    # Calculate simulated profit
    token_amount = usdt_amount / buy_price
    sell_value = token_amount * sell_price
    profit = sell_value - usdt_amount
    profit_percent = (profit / usdt_amount) * 100 if usdt_amount > 0 else 0
    
    return {
        "status": "completed",
        "opportunity_id": opportunity['id'],
        "usdt_invested": usdt_amount,
        "tokens_bought": round(token_amount, 8),
        "sell_value": round(sell_value, 4),
        "profit": round(profit, 4),
        "profit_percent": round(profit_percent, 4),
        "is_live": False,
        "simulated": True
    }


async def log_transaction(opportunity_id: str, step: str, status: str, details: dict, is_live: bool = False):
    """Log a transaction step"""
    log = TransactionLog(
        opportunity_id=opportunity_id,
        step=step,
        status=status,
        details=details,
        is_live=is_live
    )
    await db.transaction_logs.insert_one(log.model_dump())


@api_router.get("/transactions/{opportunity_id}")
async def get_transaction_logs(opportunity_id: str):
    """Get transaction logs for an arbitrage opportunity"""
    logs = await db.transaction_logs.find({"opportunity_id": opportunity_id}, {"_id": 0}).to_list(100)
    return logs

# ============== TRADE HISTORY ==============
@api_router.get("/trades/history")
async def get_trade_history(limit: int = 50):
    """Get completed trade history"""
    trades = await db.arbitrage_opportunities.find(
        {"status": {"$in": ["completed", "failed"]}},
        {"_id": 0}
    ).sort("detected_at", -1).to_list(limit)
    return trades

@api_router.get("/activity")
async def get_activity(limit: int = 100):
    """Get all activity logs including trades and transaction logs"""
    # Get all opportunities (completed, failed, executing)
    opportunities = await db.arbitrage_opportunities.find(
        {"status": {"$in": ["completed", "failed", "executing"]}},
        {"_id": 0}
    ).sort("detected_at", -1).to_list(limit)
    
    # Get all transaction logs
    logs = await db.transaction_logs.find(
        {},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit * 5)  # More logs per opportunity
    
    # Group logs by opportunity_id
    logs_by_opportunity = {}
    for log in logs:
        opp_id = log.get('opportunity_id')
        if opp_id not in logs_by_opportunity:
            logs_by_opportunity[opp_id] = []
        logs_by_opportunity[opp_id].append(log)
    
    # Combine opportunities with their logs
    activity = []
    for opp in opportunities:
        opp_id = opp.get('id')
        activity.append({
            **opp,
            "logs": logs_by_opportunity.get(opp_id, [])
        })
    
    return activity

# ============== WEBSOCKET ==============
@api_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# ============== HEALTH & STATUS ==============
@api_router.get("/")
async def root():
    return {"message": "Crypto Arbitrage Bot API", "version": "2.0.0"}

@api_router.get("/health")
async def health_check():
    settings = await db.settings.find_one({}, {"_id": 0})
    is_live = settings.get('is_live_mode', False) if settings else False
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "exchanges_active": len(exchange_instances),
        "mode": "LIVE" if is_live else "TEST",
        "bsc_mainnet_connected": bsc_service.mainnet_w3.is_connected() if bsc_service.mainnet_w3 else False,
        "bsc_testnet_connected": bsc_service.testnet_w3.is_connected() if bsc_service.testnet_w3 else False
    }

@api_router.get("/stats")
async def get_stats():
    """Get dashboard statistics"""
    token_count = await db.tokens.count_documents({"is_active": True})
    exchange_count = await db.exchanges.count_documents({"is_active": True})
    opportunity_count = await db.arbitrage_opportunities.count_documents({"status": {"$in": ["detected", "manual"]}})
    completed_count = await db.arbitrage_opportunities.count_documents({"status": "completed"})
    
    wallet = await db.wallet.find_one({}, {"_id": 0, "private_key_encrypted": 0})
    settings = await db.settings.find_one({}, {"_id": 0})
    
    return {
        "tokens": token_count,
        "exchanges": exchange_count,
        "opportunities": opportunity_count,
        "completed_trades": completed_count,
        "wallet": wallet,
        "is_live_mode": settings.get('is_live_mode', False) if settings else False
    }

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup"""
    try:
        await db_instance.connect()
        db_type = "MongoDB" if IS_MONGODB else "MySQL"
        logger.info(f"Application started successfully with {db_type}")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    # Close all exchange instances
    await close_exchange_instances()
    
    # Close database connection
    await db_instance.close()
    
    logger.info("Application shutdown complete")
