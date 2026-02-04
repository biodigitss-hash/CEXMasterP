import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { 
  TrendingUp, 
  TrendingDown, 
  Coins, 
  Building2, 
  Wallet,
  RefreshCw,
  Plus,
  Zap,
  AlertTriangle,
  CheckCircle,
  Settings,
  Bell,
  Shield,
  ToggleLeft,
  ToggleRight
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import AddTokenModal from "@/components/AddTokenModal";
import AddExchangeModal from "@/components/AddExchangeModal";
import WalletModal from "@/components/WalletModal";
import ArbitrageCard from "@/components/ArbitrageCard";
import ManualSelectionModal from "@/components/ManualSelectionModal";
import SettingsModal from "@/components/SettingsModal";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
};

export default function Dashboard({ 
  stats, 
  tokens, 
  setTokens,
  exchanges, 
  setExchanges,
  opportunities, 
  setOpportunities,
  prices,
  isLoading, 
  fetchData,
  fetchPrices,
  detectArbitrage,
  settings,
  updateSettings,
  activePage,
  setActivePage
}) {
  const [showAddToken, setShowAddToken] = useState(false);
  const [showAddExchange, setShowAddExchange] = useState(false);
  const [showWallet, setShowWallet] = useState(false);
  const [showManualSelection, setShowManualSelection] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Handle navigation-triggered modals
  useEffect(() => {
    if (activePage === "wallet") {
      setShowWallet(true);
      setActivePage("dashboard"); // Reset to dashboard after opening modal
    } else if (activePage === "tokens") {
      setShowAddToken(true);
      setActivePage("dashboard");
    } else if (activePage === "exchanges") {
      setShowAddExchange(true);
      setActivePage("dashboard");
    }
  }, [activePage, setActivePage]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await Promise.all([fetchData(), fetchPrices(), detectArbitrage()]);
    setIsRefreshing(false);
  };

  const handleModeToggle = async () => {
    await updateSettings({ is_live_mode: !settings.is_live_mode });
  };

  // Get price data for a token
  const getTokenPrices = (tokenSymbol) => {
    const tokenPrice = prices.find(p => p.token_symbol === tokenSymbol);
    return tokenPrice?.prices || [];
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div data-testid="dashboard" className="p-6 md:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono font-bold text-2xl md:text-3xl text-white tracking-tight uppercase">
            Arbitrage Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            BSC Multi-Exchange Arbitrage Bot
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Mode Toggle */}
          <div 
            className={`flex items-center gap-2 px-3 py-1.5 rounded-sm cursor-pointer transition-all ${
              settings.is_live_mode 
                ? 'bg-red-500/20 border border-red-500/50' 
                : 'bg-yellow-500/20 border border-yellow-500/50'
            }`}
            onClick={handleModeToggle}
            data-testid="mode-toggle"
          >
            {settings.is_live_mode ? (
              <>
                <ToggleRight className="w-4 h-4 text-red-400" />
                <span className="text-xs font-semibold text-red-400 uppercase tracking-wider">Live Mode</span>
              </>
            ) : (
              <>
                <ToggleLeft className="w-4 h-4 text-yellow-400" />
                <span className="text-xs font-semibold text-yellow-400 uppercase tracking-wider">Test Mode</span>
              </>
            )}
          </div>
          
          {/* Telegram Status */}
          {settings.telegram_enabled && (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-sm bg-blue-500/20 border border-blue-500/30">
              <Bell className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-xs text-blue-400">TG</span>
            </div>
          )}
          
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div className="live-indicator" />
            <span className="uppercase tracking-wider">Live</span>
          </div>
          
          <Button 
            data-testid="settings-btn"
            variant="ghost" 
            size="icon"
            onClick={() => setShowSettings(true)}
            className="h-9 w-9"
          >
            <Settings className="w-4 h-4" strokeWidth={1.5} />
          </Button>
          
          <Button 
            data-testid="refresh-btn"
            variant="outline" 
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="h-9"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} strokeWidth={1.5} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Live Mode Warning Banner */}
      {settings.is_live_mode && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-500/10 border border-red-500/30 rounded-sm p-4 flex items-center gap-3"
        >
          <Shield className="w-5 h-5 text-red-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-semibold text-red-400">Live Trading Mode Active</p>
            <p className="text-xs text-red-400/80">
              Real orders will be placed on exchanges. Ensure you have sufficient funds and understand the risks.
            </p>
          </div>
        </motion.div>
      )}

      {/* Stats Grid */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <motion.div variants={itemVariants}>
          <Card className="bg-card border-border hover:border-primary/50 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-sm bg-primary/10">
                  <Coins className="w-5 h-5 text-primary" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">{stats.tokens}</p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Tokens</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="bg-card border-border hover:border-primary/50 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-sm bg-info/10">
                  <Building2 className="w-5 h-5 text-info" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">{stats.exchanges}</p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Exchanges</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="bg-card border-border hover:border-warning/50 transition-colors">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-sm bg-warning/10">
                  <Zap className="w-5 h-5 text-warning" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">{stats.opportunities}</p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Opportunities</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card 
            data-testid="wallet-card"
            className="bg-card border-border hover:border-primary/50 transition-colors cursor-pointer relative z-10"
            onClick={() => setShowWallet(true)}
          >
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-sm bg-primary/10">
                  <Wallet className="w-5 h-5 text-primary" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">
                    {stats.wallet?.balance_usdt?.toFixed(2) || '0.00'}
                  </p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">USDT Balance</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3">
        <Button 
          data-testid="add-token-btn"
          onClick={() => setShowAddToken(true)}
          className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-6 rounded-sm uppercase font-semibold tracking-wide"
        >
          <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Add Token
        </Button>
        <Button 
          data-testid="add-exchange-btn"
          onClick={() => setShowAddExchange(true)}
          variant="outline"
          className="h-10 px-6 rounded-sm uppercase font-semibold tracking-wide"
        >
          <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Add Exchange
        </Button>
        <Button 
          data-testid="manual-selection-btn"
          onClick={() => setShowManualSelection(true)}
          variant="outline"
          className="h-10 px-6 rounded-sm uppercase font-semibold tracking-wide"
        >
          <Zap className="w-4 h-4 mr-2" strokeWidth={1.5} />
          Manual Selection
        </Button>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Arbitrage Opportunities - Takes 2 columns */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-mono font-bold text-lg text-white uppercase tracking-tight">
              Arbitrage Opportunities
            </h2>
            <Badge variant="outline" className="text-warning border-warning/30">
              {opportunities.length} Active
            </Badge>
          </div>
          
          {opportunities.length === 0 ? (
            <Card className="bg-card border-border">
              <CardContent className="p-8 text-center">
                <AlertTriangle className="w-12 h-12 text-muted-foreground mx-auto mb-4" strokeWidth={1.5} />
                <p className="text-muted-foreground">No arbitrage opportunities detected</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Add tokens and exchanges to start monitoring
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {opportunities.slice(0, 5).map((opp, index) => (
                <ArbitrageCard 
                  key={opp.id} 
                  opportunity={opp}
                  index={index}
                  setOpportunities={setOpportunities}
                  fetchData={fetchData}
                  settings={settings}
                />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar - Tokens & Exchanges */}
        <div className="space-y-6">
          {/* Monitored Tokens */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="font-mono text-sm uppercase tracking-wider flex items-center gap-2">
                <Coins className="w-4 h-4 text-primary" strokeWidth={1.5} />
                Monitored Tokens
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {tokens.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No tokens added</p>
              ) : (
                tokens.map((token) => {
                  const tokenPrices = getTokenPrices(token.symbol);
                  const avgPrice = tokenPrices.length > 0 
                    ? tokenPrices.reduce((sum, p) => sum + (p.last || 0), 0) / tokenPrices.length 
                    : 0;
                  
                  return (
                    <div 
                      key={token.id} 
                      data-testid={`token-${token.symbol}`}
                      className="flex items-center justify-between p-3 rounded-sm bg-secondary/50 border border-border hover:border-primary/30 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="font-mono text-xs font-bold text-primary">
                            {token.symbol.slice(0, 2)}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium text-white text-sm">{token.symbol}</p>
                          <p className="text-xs text-muted-foreground">{token.name}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-mono text-sm text-white">
                          ${avgPrice > 0 ? avgPrice.toFixed(4) : '---'}
                        </p>
                        <div className="flex items-center gap-1 text-xs">
                          {tokenPrices.length > 0 ? (
                            <>
                              <CheckCircle className="w-3 h-3 text-success" />
                              <span className="text-success">{tokenPrices.length} CEX</span>
                            </>
                          ) : (
                            <span className="text-muted-foreground">No data</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          {/* Connected Exchanges */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="font-mono text-sm uppercase tracking-wider flex items-center gap-2">
                <Building2 className="w-4 h-4 text-info" strokeWidth={1.5} />
                Connected Exchanges
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {exchanges.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No exchanges connected</p>
              ) : (
                exchanges.map((exchange) => (
                  <div 
                    key={exchange.id} 
                    data-testid={`exchange-${exchange.name}`}
                    className="flex items-center justify-between p-3 rounded-sm bg-secondary/50 border border-border hover:border-info/30 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-info/10 flex items-center justify-center">
                        <Building2 className="w-4 h-4 text-info" strokeWidth={1.5} />
                      </div>
                      <div>
                        <p className="font-medium text-white text-sm">{exchange.name}</p>
                        <p className="text-xs text-muted-foreground">API Connected</p>
                      </div>
                    </div>
                    <Badge variant="outline" className="text-success border-success/30 text-xs">
                      Active
                    </Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Modals */}
      <AddTokenModal 
        open={showAddToken} 
        onOpenChange={setShowAddToken}
        exchanges={exchanges}
        setTokens={setTokens}
        fetchData={fetchData}
      />
      <AddExchangeModal 
        open={showAddExchange} 
        onOpenChange={setShowAddExchange}
        setExchanges={setExchanges}
        fetchData={fetchData}
      />
      <WalletModal 
        open={showWallet} 
        onOpenChange={setShowWallet}
        wallet={stats.wallet}
        fetchData={fetchData}
        settings={settings}
      />
      <ManualSelectionModal
        open={showManualSelection}
        onOpenChange={setShowManualSelection}
        tokens={tokens}
        exchanges={exchanges}
        setOpportunities={setOpportunities}
      />
      <SettingsModal
        open={showSettings}
        onOpenChange={setShowSettings}
        settings={settings}
        updateSettings={updateSettings}
      />
    </div>
  );
}
