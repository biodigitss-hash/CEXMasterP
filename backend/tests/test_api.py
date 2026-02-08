"""
Crypto Arbitrage Bot API Tests
Tests all backend endpoints including fail-safe arbitrage settings
"""

import pytest
import requests
import os
import uuid

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://tradebotsql.preview.emergentagent.com"


class TestHealthEndpoints:
    """Health and basic endpoint tests"""
    
    def test_health_endpoint(self):
        """Test /api/health returns 200 with correct structure"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "mode" in data
        assert "bsc_mainnet_connected" in data
        assert "bsc_testnet_connected" in data
        print(f"✓ Health endpoint working: {data}")
    
    def test_root_api_endpoint(self):
        """Test /api/ root endpoint"""
        response = requests.get(f"{BASE_URL}/api/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        print(f"✓ Root API endpoint working: {data}")


class TestSettingsAPI:
    """Settings API tests including fail-safe settings"""
    
    def test_get_settings(self):
        """Test GET /api/settings returns fail-safe settings"""
        response = requests.get(f"{BASE_URL}/api/settings")
        assert response.status_code == 200
        data = response.json()
        
        # Check standard settings
        assert "is_live_mode" in data
        assert "min_spread_threshold" in data
        assert "max_trade_amount" in data
        assert "slippage_tolerance" in data
        
        # Check fail-safe settings (new)
        assert "target_sell_spread" in data, "Missing target_sell_spread in settings"
        assert "spread_check_interval" in data, "Missing spread_check_interval in settings"
        assert "max_wait_time" in data, "Missing max_wait_time in settings"
        
        # Verify default values
        assert isinstance(data["target_sell_spread"], (int, float))
        assert isinstance(data["spread_check_interval"], int)
        assert isinstance(data["max_wait_time"], int)
        
        print(f"✓ Settings retrieved with fail-safe config: target_sell_spread={data['target_sell_spread']}%, spread_check_interval={data['spread_check_interval']}s, max_wait_time={data['max_wait_time']}s")
    
    def test_update_settings(self):
        """Test PUT /api/settings updates settings correctly"""
        # Get current settings first
        get_response = requests.get(f"{BASE_URL}/api/settings")
        original_settings = get_response.json()
        
        # Update settings
        new_settings = {
            "min_spread_threshold": 0.75,
            "target_sell_spread": 90.0,
            "spread_check_interval": 15,
            "max_wait_time": 7200
        }
        
        response = requests.put(f"{BASE_URL}/api/settings", json=new_settings)
        assert response.status_code == 200
        data = response.json()
        
        # Verify updates
        assert data["min_spread_threshold"] == 0.75
        assert data["target_sell_spread"] == 90.0
        assert data["spread_check_interval"] == 15
        assert data["max_wait_time"] == 7200
        
        print(f"✓ Settings updated successfully")
        
        # Restore original settings
        restore_settings = {
            "min_spread_threshold": original_settings.get("min_spread_threshold", 0.5),
            "target_sell_spread": original_settings.get("target_sell_spread", 85.0),
            "spread_check_interval": original_settings.get("spread_check_interval", 10),
            "max_wait_time": original_settings.get("max_wait_time", 3600)
        }
        requests.put(f"{BASE_URL}/api/settings", json=restore_settings)
        print(f"✓ Settings restored to original values")


class TestTokensAPI:
    """Token CRUD operations tests"""
    
    @pytest.fixture
    def test_token_id(self):
        """Create a test token and return its ID, cleanup after test"""
        token_data = {
            "name": "TEST_Token",
            "symbol": "TEST",
            "contract_address": f"0x{uuid.uuid4().hex[:40]}",
            "monitored_exchanges": ["binance", "kucoin"]
        }
        response = requests.post(f"{BASE_URL}/api/tokens", json=token_data)
        assert response.status_code == 200
        token_id = response.json()["id"]
        yield token_id
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tokens/{token_id}")
    
    def test_create_token(self):
        """Test POST /api/tokens creates a token"""
        token_data = {
            "name": "TEST_CreateToken",
            "symbol": "TCRT",
            "contract_address": f"0x{uuid.uuid4().hex[:40]}",
            "monitored_exchanges": ["binance"]
        }
        response = requests.post(f"{BASE_URL}/api/tokens", json=token_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["name"] == "TEST_CreateToken"
        assert data["symbol"] == "TCRT"
        assert data["is_active"] == True
        
        print(f"✓ Token created: {data['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/tokens/{data['id']}")
    
    def test_get_tokens(self):
        """Test GET /api/tokens returns list of tokens"""
        response = requests.get(f"{BASE_URL}/api/tokens")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} tokens")
    
    def test_get_token_by_id(self, test_token_id):
        """Test GET /api/tokens/{id} returns specific token"""
        response = requests.get(f"{BASE_URL}/api/tokens/{test_token_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_token_id
        print(f"✓ Retrieved token by ID: {test_token_id}")
    
    def test_delete_token(self):
        """Test DELETE /api/tokens/{id} soft deletes token"""
        # Create token first
        token_data = {
            "name": "TEST_DeleteToken",
            "symbol": "TDEL",
            "contract_address": f"0x{uuid.uuid4().hex[:40]}",
            "monitored_exchanges": []
        }
        create_response = requests.post(f"{BASE_URL}/api/tokens", json=token_data)
        token_id = create_response.json()["id"]
        
        # Delete token
        delete_response = requests.delete(f"{BASE_URL}/api/tokens/{token_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"
        
        print(f"✓ Token deleted: {token_id}")


class TestExchangesAPI:
    """Exchange CRUD operations tests"""
    
    def test_create_exchange(self):
        """Test POST /api/exchanges creates an exchange"""
        exchange_data = {
            "name": "binance",
            "api_key": "TEST_api_key_12345",
            "api_secret": "TEST_api_secret_67890"
        }
        response = requests.post(f"{BASE_URL}/api/exchanges", json=exchange_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert data["name"] == "binance"
        assert data["is_active"] == True
        # Verify encrypted fields are not returned
        assert "api_key_encrypted" not in data
        assert "api_secret_encrypted" not in data
        
        print(f"✓ Exchange created: {data['id']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/exchanges/{data['id']}")
    
    def test_get_exchanges(self):
        """Test GET /api/exchanges returns list without sensitive data"""
        response = requests.get(f"{BASE_URL}/api/exchanges")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Verify no sensitive data is returned
        for exchange in data:
            assert "api_key_encrypted" not in exchange
            assert "api_secret_encrypted" not in exchange
        
        print(f"✓ Retrieved {len(data)} exchanges (no sensitive data exposed)")
    
    def test_delete_exchange(self):
        """Test DELETE /api/exchanges/{id} soft deletes exchange"""
        # Create exchange first
        exchange_data = {
            "name": "kucoin",
            "api_key": "TEST_delete_key",
            "api_secret": "TEST_delete_secret"
        }
        create_response = requests.post(f"{BASE_URL}/api/exchanges", json=exchange_data)
        exchange_id = create_response.json()["id"]
        
        # Delete exchange
        delete_response = requests.delete(f"{BASE_URL}/api/exchanges/{exchange_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"
        
        print(f"✓ Exchange deleted: {exchange_id}")


class TestWalletAPI:
    """Wallet configuration tests"""
    
    def test_save_wallet_config(self):
        """Test POST /api/wallet saves wallet configuration"""
        wallet_data = {
            "private_key": "TEST_private_key_" + uuid.uuid4().hex,
            "address": "0x742d35Cc6634C0532925a3b844Bc9e7595f1e123"
        }
        response = requests.post(f"{BASE_URL}/api/wallet", json=wallet_data)
        assert response.status_code == 200
        data = response.json()
        
        assert "id" in data
        assert "address" in data
        assert data["address"] == wallet_data["address"]
        # Verify private key is not returned
        assert "private_key_encrypted" not in data
        assert "private_key" not in data
        
        print(f"✓ Wallet config saved: {data['address']}")
    
    def test_get_wallet_config(self):
        """Test GET /api/wallet returns wallet without private key"""
        response = requests.get(f"{BASE_URL}/api/wallet")
        # May return null if no wallet configured
        assert response.status_code == 200
        data = response.json()
        
        if data:
            assert "private_key_encrypted" not in data
            assert "address" in data
            print(f"✓ Wallet retrieved: {data['address']}")
        else:
            print(f"✓ No wallet configured (null response)")


class TestActivityAPI:
    """Activity/Transaction log tests"""
    
    def test_get_activity(self):
        """Test GET /api/activity returns transaction logs"""
        response = requests.get(f"{BASE_URL}/api/activity")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} activity logs")


class TestArbitrageAPI:
    """Arbitrage detection and execution tests"""
    
    def test_get_opportunities(self):
        """Test GET /api/arbitrage/opportunities returns list"""
        response = requests.get(f"{BASE_URL}/api/arbitrage/opportunities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Retrieved {len(data)} arbitrage opportunities")
    
    def test_detect_arbitrage(self):
        """Test GET /api/arbitrage/detect triggers detection"""
        response = requests.get(f"{BASE_URL}/api/arbitrage/detect")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Arbitrage detection completed, found {len(data)} opportunities")


class TestStatsAPI:
    """Stats endpoint tests"""
    
    def test_get_stats(self):
        """Test GET /api/stats returns dashboard statistics"""
        response = requests.get(f"{BASE_URL}/api/stats")
        assert response.status_code == 200
        data = response.json()
        
        assert "tokens" in data
        assert "exchanges" in data
        assert "opportunities" in data
        assert "completed_trades" in data
        assert "is_live_mode" in data
        
        print(f"✓ Stats retrieved: tokens={data['tokens']}, exchanges={data['exchanges']}, opportunities={data['opportunities']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
