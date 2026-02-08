-- MySQL Database Schema for Crypto Arbitrage Bot
-- NOTE: Uses port 3307 for local Windows setup

-- Create database
CREATE DATABASE IF NOT EXISTS crypto_arbitrage;
USE crypto_arbitrage;

-- Settings Table (with fail-safe arbitrage settings)
CREATE TABLE IF NOT EXISTS settings (
    id VARCHAR(36) PRIMARY KEY,
    is_live_mode BOOLEAN DEFAULT FALSE,
    telegram_chat_id VARCHAR(255),
    telegram_enabled BOOLEAN DEFAULT FALSE,
    min_spread_threshold DECIMAL(5, 2) DEFAULT 0.5,
    max_trade_amount DECIMAL(20, 2) DEFAULT 1000.00,
    slippage_tolerance DECIMAL(5, 2) DEFAULT 0.5,
    -- Fail-safe arbitrage settings
    target_sell_spread DECIMAL(5, 2) DEFAULT 85.0,  -- Target spread % to trigger sell
    spread_check_interval INT DEFAULT 10,           -- Seconds between spread checks
    max_wait_time INT DEFAULT 3600,                 -- Max time to wait for target spread (seconds)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Wallet Table
CREATE TABLE IF NOT EXISTS wallet (
    id VARCHAR(36) PRIMARY KEY,
    address VARCHAR(42) NOT NULL UNIQUE,
    private_key_encrypted TEXT NOT NULL,
    balance_bnb DECIMAL(20, 8) DEFAULT 0,
    balance_usdt DECIMAL(20, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Tokens Table
CREATE TABLE IF NOT EXISTS tokens (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    contract_address VARCHAR(42) NOT NULL,
    monitored_exchanges JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_symbol (symbol),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Exchanges Table
CREATE TABLE IF NOT EXISTS exchanges (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    api_secret_encrypted TEXT NOT NULL,
    additional_params_encrypted TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (name),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Arbitrage Opportunities Table
CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    id VARCHAR(36) PRIMARY KEY,
    token_id VARCHAR(36) NOT NULL,
    token_symbol VARCHAR(20) NOT NULL,
    buy_exchange VARCHAR(100) NOT NULL,
    sell_exchange VARCHAR(100) NOT NULL,
    buy_price DECIMAL(20, 8) NOT NULL,
    sell_price DECIMAL(20, 8) NOT NULL,
    spread_percent DECIMAL(10, 4) NOT NULL,
    confidence DECIMAL(5, 2) NOT NULL,
    recommended_usdt_amount DECIMAL(20, 2),
    status ENUM('detected', 'executing', 'completed', 'failed', 'manual', 'monitoring') DEFAULT 'detected',
    is_manual_selection BOOLEAN DEFAULT FALSE,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    persistence_minutes INT DEFAULT 0,
    INDEX idx_status (status),
    INDEX idx_token_symbol (token_symbol),
    INDEX idx_detected (detected_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Fail-Safe Arbitrage State Table (tracks ongoing fail-safe executions)
CREATE TABLE IF NOT EXISTS failsafe_states (
    id VARCHAR(36) PRIMARY KEY,
    opportunity_id VARCHAR(36) NOT NULL,
    status ENUM('pending', 'funding_cex_a', 'bought', 'withdrawn', 'funding_cex_b', 'monitoring', 'selling', 'sold', 'completed', 'failed') DEFAULT 'pending',
    token_symbol VARCHAR(20) NOT NULL,
    buy_exchange VARCHAR(100) NOT NULL,
    sell_exchange VARCHAR(100) NOT NULL,
    tokens_held DECIMAL(20, 8) DEFAULT 0,
    usdt_invested DECIMAL(20, 2) DEFAULT 0,
    current_spread DECIMAL(10, 4) DEFAULT 0,
    target_spread DECIMAL(5, 2) DEFAULT 85.0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_opportunity (opportunity_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Transaction Logs Table
CREATE TABLE IF NOT EXISTS transaction_logs (
    id VARCHAR(36) PRIMARY KEY,
    opportunity_id VARCHAR(36) NOT NULL,
    step VARCHAR(100) NOT NULL,
    status ENUM('completed', 'failed', 'pending', 'started', 'checking', 'confirming', 'submitted', 'broadcast') NOT NULL,
    details JSON,
    is_live BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_opportunity (opportunity_id),
    INDEX idx_created (created_at),
    INDEX idx_step (step)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert default settings with fail-safe configuration
INSERT INTO settings (id, is_live_mode, telegram_enabled, min_spread_threshold, max_trade_amount, slippage_tolerance, target_sell_spread, spread_check_interval, max_wait_time)
VALUES (UUID(), FALSE, FALSE, 0.5, 1000.00, 0.5, 85.0, 10, 3600)
ON DUPLICATE KEY UPDATE id=id;
