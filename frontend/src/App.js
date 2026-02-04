import { useState, useEffect, useCallback } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import Dashboard from "@/components/Dashboard";
import Sidebar from "@/components/Sidebar";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// WebSocket connection
let ws = null;

function App() {
  const [stats, setStats] = useState({ tokens: 0, exchanges: 0, opportunities: 0, completed_trades: 0, wallet: null, is_live_mode: false });
  const [tokens, setTokens] = useState([]);
  const [exchanges, setExchanges] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [prices, setPrices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activePage, setActivePage] = useState("dashboard");
  const [settings, setSettings] = useState({
    is_live_mode: false,
    telegram_chat_id: "",
    telegram_enabled: false,
    min_spread_threshold: 0.5,
    max_trade_amount: 1000,
    slippage_tolerance: 0.5
  });

  const fetchSettings = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/settings`);
      setSettings(res.data);
    } catch (error) {
      console.error("Error fetching settings:", error);
    }
  }, []);

  const updateSettings = useCallback(async (newSettings) => {
    try {
      const res = await axios.put(`${API}/settings`, newSettings);
      setSettings(res.data);
      toast.success("Settings updated successfully");
      return res.data;
    } catch (error) {
      console.error("Error updating settings:", error);
      toast.error("Failed to update settings");
      throw error;
    }
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, tokensRes, exchangesRes, oppsRes] = await Promise.all([
        axios.get(`${API}/stats`),
        axios.get(`${API}/tokens`),
        axios.get(`${API}/exchanges`),
        axios.get(`${API}/arbitrage/opportunities`)
      ]);
      
      setStats(statsRes.data);
      setTokens(tokensRes.data);
      setExchanges(exchangesRes.data);
      setOpportunities(oppsRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Failed to fetch data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchPrices = useCallback(async () => {
    if (tokens.length === 0 || exchanges.length === 0) return;
    
    try {
      const res = await axios.get(`${API}/prices/all/tokens`);
      setPrices(res.data);
    } catch (error) {
      console.error("Error fetching prices:", error);
    }
  }, [tokens.length, exchanges.length]);

  const detectArbitrage = useCallback(async () => {
    if (tokens.length === 0 || exchanges.length === 0) return;
    
    try {
      const res = await axios.get(`${API}/arbitrage/detect`);
      if (res.data.length > 0) {
        setOpportunities(prev => [...res.data, ...prev]);
        toast.success(`${res.data.length} new arbitrage opportunity detected!`);
      }
    } catch (error) {
      console.error("Error detecting arbitrage:", error);
    }
  }, [tokens.length, exchanges.length]);

  // Initialize WebSocket
  useEffect(() => {
    const wsUrl = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');
    
    const connectWebSocket = () => {
      ws = new WebSocket(`${wsUrl}/api/ws`);
      
      ws.onopen = () => {
        console.log("WebSocket connected");
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "arbitrage_completed") {
          const modeLabel = data.is_live ? "🔴 LIVE" : "🟡 TEST";
          toast.success(`${modeLabel} Arbitrage completed! Profit: $${data.profit} (${data.profit_percent}%)`);
          fetchData();
        }
      };
      
      ws.onclose = () => {
        console.log("WebSocket disconnected, reconnecting...");
        setTimeout(connectWebSocket, 3000);
      };
      
      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    };
    
    connectWebSocket();
    
    return () => {
      if (ws) ws.close();
    };
  }, [fetchData]);

  // Initial data fetch
  useEffect(() => {
    fetchData();
    fetchSettings();
  }, [fetchData, fetchSettings]);

  // Periodic price updates
  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, 30000); // Every 30 seconds
    return () => clearInterval(interval);
  }, [fetchPrices]);

  // Periodic arbitrage detection
  useEffect(() => {
    const interval = setInterval(detectArbitrage, 60000); // Every 60 seconds
    return () => clearInterval(interval);
  }, [detectArbitrage]);

  return (
    <div className="min-h-screen bg-background dark">
      <BrowserRouter>
        <div className="flex">
          <Sidebar activePage={activePage} setActivePage={setActivePage} />
          <main className="flex-1 min-h-screen overflow-auto">
            <Routes>
              <Route 
                path="/" 
                element={
                  <Dashboard 
                    stats={stats}
                    tokens={tokens}
                    setTokens={setTokens}
                    exchanges={exchanges}
                    setExchanges={setExchanges}
                    opportunities={opportunities}
                    setOpportunities={setOpportunities}
                    prices={prices}
                    isLoading={isLoading}
                    fetchData={fetchData}
                    fetchPrices={fetchPrices}
                    detectArbitrage={detectArbitrage}
                    settings={settings}
                    updateSettings={updateSettings}
                  />
                } 
              />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
      <Toaster richColors position="top-right" />
    </div>
  );
}

export default App;
