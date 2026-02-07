import { useState } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { toast } from "sonner";
import { 
  TrendingUp, 
  ArrowRight, 
  Zap, 
  DollarSign,
  Loader2,
  X,
  CheckCircle,
  AlertTriangle,
  Shield
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { API } from "@/App";

export default function ArbitrageCard({ opportunity, index, setOpportunities, fetchData, settings }) {
  const [showExecuteModal, setShowExecuteModal] = useState(false);
  const [usdtAmount, setUsdtAmount] = useState(opportunity.recommended_usdt_amount?.toString() || "100");
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [confirmed, setConfirmed] = useState(false);

  const isLiveMode = settings?.is_live_mode || false;
  const isProfitable = opportunity.spread_percent > 0;
  const confidenceColor = opportunity.confidence >= 90 ? "text-success" : 
                         opportunity.confidence >= 70 ? "text-warning" : "text-muted-foreground";

  const handleExecute = async () => {
    const amount = parseFloat(usdtAmount);
    if (isNaN(amount) || amount <= 0) {
      toast.error("Please enter a valid USDT amount");
      return;
    }

    // Require confirmation for live mode
    if (isLiveMode && !confirmed) {
      toast.error("Please confirm that you understand the risks of live trading");
      return;
    }

    setIsExecuting(true);
    try {
      const response = await axios.post(`${API}/arbitrage/execute`, {
        opportunity_id: opportunity.id,
        usdt_amount: amount,
        confirmed: isLiveMode ? confirmed : true
      });
      
      setExecutionResult(response.data);
      const modeLabel = response.data.is_live ? "🔴 LIVE" : "🟡 TEST";
      toast.success(`${modeLabel} Arbitrage executed! Profit: $${response.data.profit.toFixed(4)}`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Execution failed");
    } finally {
      setIsExecuting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await axios.delete(`${API}/arbitrage/opportunities/${opportunity.id}`);
      setOpportunities(prev => prev.filter(o => o.id !== opportunity.id));
      toast.success("Opportunity removed");
    } catch (error) {
      toast.error("Failed to remove opportunity");
    }
  };

  const resetModal = () => {
    setShowExecuteModal(false);
    setExecutionResult(null);
    setConfirmed(false);
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: index * 0.1 }}
        data-testid={`opportunity-card-${opportunity.id}`}
        className={`
          relative p-4 rounded-sm border transition-all duration-300
          ${isProfitable 
            ? 'bg-gradient-to-r from-primary/5 to-transparent border-primary/30 hover:border-primary/50' 
            : 'bg-card border-border hover:border-primary/30'
          }
        `}
      >
        {/* Delete button */}
        <button
          onClick={handleDelete}
          className="absolute top-3 right-3 text-muted-foreground hover:text-destructive transition-colors"
        >
          <X className="w-4 h-4" strokeWidth={1.5} />
        </button>

        <div className="flex items-start justify-between gap-4">
          {/* Token Info */}
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-sm bg-primary/10 flex items-center justify-center">
              <span className="font-mono font-bold text-primary">
                {opportunity.token_symbol?.slice(0, 3) || 'TKN'}
              </span>
            </div>
            <div>
              <h3 className="font-mono font-bold text-white text-lg">
                {opportunity.token_symbol}/USDT
              </h3>
              <div className="flex items-center gap-2 mt-1">
                {opportunity.is_manual_selection && (
                  <Badge variant="outline" className="text-info border-info/30 text-xs">
                    Manual
                  </Badge>
                )}
                <span className={`text-xs ${confidenceColor}`}>
                  {opportunity.confidence}% confidence
                </span>
              </div>
            </div>
          </div>

          {/* Spread & Execute */}
          <div className="text-right">
            <div className="flex items-center gap-2 justify-end">
              <TrendingUp className={`w-5 h-5 ${isProfitable ? 'text-success' : 'text-destructive'}`} />
              <span className={`font-mono text-2xl font-bold ${isProfitable ? 'text-success' : 'text-destructive'}`}>
                {opportunity.spread_percent > 0 ? '+' : ''}{opportunity.spread_percent.toFixed(2)}%
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Est. ${opportunity.recommended_usdt_amount?.toFixed(0) || '100'} USDT
            </p>
          </div>
        </div>

        {/* Exchange Flow */}
        <div className="mt-4 flex items-center gap-3 p-3 rounded-sm bg-secondary/50">
          <div className="flex-1 text-center">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Buy on</p>
            <p className="font-mono font-semibold text-white">{opportunity.buy_exchange}</p>
            <p className="font-mono text-sm text-muted-foreground">${opportunity.buy_price?.toFixed(4)}</p>
          </div>
          
          <ArrowRight className="w-6 h-6 text-primary flex-shrink-0" strokeWidth={1.5} />
          
          <div className="flex-1 text-center">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Sell on</p>
            <p className="font-mono font-semibold text-white">{opportunity.sell_exchange}</p>
            <p className="font-mono text-sm text-muted-foreground">${opportunity.sell_price?.toFixed(4)}</p>
          </div>
        </div>

        {/* Execute Button */}
        <div className="mt-4 flex justify-end">
          <Button
            data-testid={`execute-btn-${opportunity.id}`}
            onClick={() => setShowExecuteModal(true)}
            disabled={opportunity.status === 'executing' || opportunity.status === 'completed'}
            className={`
              h-10 px-6 rounded-sm uppercase font-semibold
              ${opportunity.status === 'completed' 
                ? 'bg-success/20 text-success border border-success/30' 
                : isLiveMode
                  ? 'bg-red-500 text-white hover:bg-red-600 hover:shadow-[0_0_15px_rgba(239,68,68,0.4)]'
                  : 'bg-primary text-primary-foreground hover:bg-primary/90 hover:shadow-[0_0_15px_rgba(0,229,153,0.4)]'
              }
            `}
          >
            {opportunity.status === 'executing' ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
                Executing...
              </>
            ) : opportunity.status === 'completed' ? (
              <>
                <CheckCircle className="w-4 h-4 mr-2" />
                Completed
              </>
            ) : (
              <>
                <Zap className="w-4 h-4 mr-2" strokeWidth={1.5} />
                {isLiveMode ? 'START ARBITRAGE' : 'EXECUTE TEST'}
              </>
            )}
          </Button>
        </div>
      </motion.div>

      {/* Execute Modal */}
      <Dialog open={showExecuteModal} onOpenChange={resetModal}>
        <DialogContent className="bg-card border-border sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-mono text-lg uppercase tracking-tight flex items-center gap-2">
              <Zap className={`w-5 h-5 ${isLiveMode ? 'text-red-400' : 'text-primary'}`} />
              Execute Arbitrage
              {isLiveMode && (
                <Badge className="bg-red-500/20 text-red-400 border-red-500/30 ml-2">
                  LIVE
                </Badge>
              )}
            </DialogTitle>
            <DialogDescription className="text-muted-foreground">
              {isLiveMode 
                ? 'Complete arbitrage flow: Wallet → Buy Exchange → Sell Exchange → Back to Wallet. Takes 5-15 minutes.' 
                : 'Simulated execution - no real orders or transfers'}
            </DialogDescription>
          </DialogHeader>

          {executionResult ? (
            <div className="space-y-4">
              <div className={`p-4 rounded-sm border ${
                executionResult.is_live 
                  ? 'bg-red-500/10 border-red-500/30' 
                  : 'bg-success/10 border-success/30'
              }`}>
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle className={`w-5 h-5 ${executionResult.is_live ? 'text-red-400' : 'text-success'}`} />
                  <span className={`font-semibold ${executionResult.is_live ? 'text-red-400' : 'text-success'}`}>
                    {executionResult.is_live ? 'Live Trade Completed!' : 'Test Execution Successful!'}
                  </span>
                </div>
                <div className="space-y-2 font-mono text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">USDT Invested:</span>
                    <span className="text-white">${executionResult.usdt_invested.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Tokens Bought:</span>
                    <span className="text-white">{executionResult.tokens_bought.toFixed(8)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Sell Value:</span>
                    <span className="text-white">${executionResult.sell_value.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between border-t border-border pt-2 mt-2">
                    <span className="text-muted-foreground">Profit:</span>
                    <span className="text-success font-bold">
                      ${executionResult.profit.toFixed(4)} ({executionResult.profit_percent.toFixed(2)}%)
                    </span>
                  </div>
                  {executionResult.buy_order_id && (
                    <div className="flex justify-between pt-2 border-t border-border">
                      <span className="text-muted-foreground">Buy Order ID:</span>
                      <span className="text-white text-xs">{executionResult.buy_order_id}</span>
                    </div>
                  )}
                  {executionResult.sell_order_id && (
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Sell Order ID:</span>
                      <span className="text-white text-xs">{executionResult.sell_order_id}</span>
                    </div>
                  )}
                </div>
              </div>
              <Button
                onClick={resetModal}
                className="w-full h-10 rounded-sm"
              >
                Close
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Live Mode Warning */}
              {isLiveMode && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-sm bg-red-500/10 border border-red-500/30 flex items-start gap-2"
                >
                  <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="text-xs text-red-400">
                    <p className="font-semibold mb-1">⚡ Full Arbitrage Execution</p>
                    <p className="mb-2">Automated flow will execute in ~5-15 minutes:</p>
                    <ol className="list-decimal list-inside space-y-1 ml-2">
                      <li>Send USDT from your wallet to buy exchange</li>
                      <li>Buy {opportunity.token_symbol} tokens</li>
                      <li>Withdraw tokens to your wallet</li>
                      <li>Deposit tokens to sell exchange</li>
                      <li>Sell tokens for USDT</li>
                      <li>Withdraw profit back to your wallet</li>
                    </ol>
                    <p className="mt-2 font-semibold">Ensure your wallet has sufficient USDT + gas fees (BNB).</p>
                  </div>
                </motion.div>
              )}

              {/* Opportunity Summary */}
              <div className="p-3 rounded-sm bg-secondary/50 border border-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">{opportunity.token_symbol}/USDT</span>
                  <span className="font-mono text-success font-bold">
                    +{opportunity.spread_percent.toFixed(2)}%
                  </span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {opportunity.buy_exchange} → {opportunity.sell_exchange}
                </div>
              </div>

              {/* Amount Input */}
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-muted-foreground">
                  USDT Amount
                </Label>
                <div className="relative">
                  <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    data-testid="usdt-amount-input"
                    type="number"
                    value={usdtAmount}
                    onChange={(e) => setUsdtAmount(e.target.value)}
                    className="bg-input border-border focus:border-primary font-mono pl-9"
                    placeholder="100"
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Recommended: ${opportunity.recommended_usdt_amount?.toFixed(0) || '100'}
                </p>
              </div>

              {/* Expected Profit */}
              <div className="p-3 rounded-sm bg-primary/5 border border-primary/20">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Expected Profit:</span>
                  <span className="font-mono text-success font-bold">
                    ~${((parseFloat(usdtAmount) || 0) * opportunity.spread_percent / 100).toFixed(4)}
                  </span>
                </div>
              </div>

              {/* Live Mode Confirmation */}
              {isLiveMode && (
                <div className="flex items-start gap-3 p-3 rounded-sm bg-red-500/5 border border-red-500/20">
                  <Checkbox
                    id="confirm-live"
                    checked={confirmed}
                    onCheckedChange={(checked) => setConfirmed(checked)}
                    className="mt-0.5"
                  />
                  <label htmlFor="confirm-live" className="text-xs text-red-400 cursor-pointer">
                    I understand this is <strong>LIVE ARBITRAGE</strong> with real funds that will be transferred between my wallet and exchanges. 
                    I have verified my wallet has sufficient USDT + BNB for gas, and accept full responsibility.
                  </label>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <Button
                  variant="outline"
                  onClick={resetModal}
                  className="h-10 px-6 rounded-sm"
                >
                  Cancel
                </Button>
                <Button
                  data-testid="confirm-execute-btn"
                  onClick={handleExecute}
                  disabled={isExecuting || (isLiveMode && !confirmed)}
                  className={`h-10 px-6 rounded-sm uppercase font-semibold ${
                    isLiveMode 
                      ? 'bg-red-500 text-white hover:bg-red-600' 
                      : 'bg-primary text-primary-foreground hover:bg-primary/90'
                  }`}
                >
                  {isExecuting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Executing...
                    </>
                  ) : (
                    <>
                      {isLiveMode ? (
                        <Shield className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      ) : (
                        <Zap className="w-4 h-4 mr-2" strokeWidth={1.5} />
                      )}
                      {isLiveMode ? 'Execute LIVE Trade' : 'Execute Test'}
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
