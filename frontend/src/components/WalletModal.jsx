import { useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Wallet, Loader2, Eye, EyeOff, Save, Copy, CheckCircle, RefreshCw } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { API } from "@/App";

export default function WalletModal({ open, onOpenChange, wallet, fetchData, settings }) {
  const [privateKey, setPrivateKey] = useState("");
  const [address, setAddress] = useState("");
  const [showPrivateKey, setShowPrivateKey] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRefreshingBalance, setIsRefreshingBalance] = useState(false);
  const [copied, setCopied] = useState(false);
  const [balanceData, setBalanceData] = useState(null);

  const isLiveMode = settings?.is_live_mode || false;

  const handleCopyAddress = () => {
    if (wallet?.address) {
      navigator.clipboard.writeText(wallet.address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      toast.success("Address copied to clipboard");
    }
  };

  const handleRefreshBalance = async () => {
    if (!wallet?.address) {
      toast.error("No wallet configured");
      return;
    }

    setIsRefreshingBalance(true);
    try {
      const response = await axios.get(`${API}/wallet/balance`);
      setBalanceData(response.data);
      toast.success(`Balance refreshed from ${response.data.network}`);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to fetch balance");
    } finally {
      setIsRefreshingBalance(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!privateKey) {
      toast.error("Please enter your private key");
      return;
    }

    setIsSubmitting(true);
    try {
      await axios.post(`${API}/wallet`, {
        private_key: privateKey,
        address: address || undefined
      });
      
      toast.success("Wallet configured successfully");
      setPrivateKey("");
      setAddress("");
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to configure wallet");
    } finally {
      setIsSubmitting(false);
    }
  };

  const displayBalanceBNB = balanceData?.balance_bnb ?? wallet?.balance_bnb ?? 0;
  const displayBalanceUSDT = balanceData?.balance_usdt ?? wallet?.balance_usdt ?? 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-card border-border sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="font-mono text-lg uppercase tracking-tight flex items-center gap-2">
            <Wallet className="w-5 h-5 text-primary" />
            Wallet Configuration
            <Badge 
              variant="outline" 
              className={`ml-2 ${isLiveMode ? 'text-red-400 border-red-400/30' : 'text-yellow-400 border-yellow-400/30'}`}
            >
              {isLiveMode ? 'Mainnet' : 'Testnet'}
            </Badge>
          </DialogTitle>
          <DialogDescription className="text-muted-foreground">
            Configure your BSC wallet for arbitrage execution
          </DialogDescription>
        </DialogHeader>

        {/* Current Wallet Info */}
        {wallet && (
          <div className="space-y-3 p-4 rounded-sm bg-secondary/50 border border-border">
            <div className="flex items-center justify-between">
              <h3 className="text-xs uppercase tracking-wider text-muted-foreground">Current Wallet</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefreshBalance}
                disabled={isRefreshingBalance}
                className="h-7 px-2 text-xs"
              >
                <RefreshCw className={`w-3 h-3 mr-1 ${isRefreshingBalance ? 'animate-spin' : ''}`} />
                Refresh Balance
              </Button>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Address</span>
                <div className="flex items-center gap-2">
                  <code className="text-xs font-mono text-white truncate max-w-[200px]">
                    {wallet.address}
                  </code>
                  <button
                    onClick={handleCopyAddress}
                    className="text-muted-foreground hover:text-white transition-colors"
                  >
                    {copied ? (
                      <CheckCircle className="w-4 h-4 text-success" />
                    ) : (
                      <Copy className="w-4 h-4" strokeWidth={1.5} />
                    )}
                  </button>
                </div>
              </div>

              {balanceData?.network && (
                <div className="flex items-center gap-2 py-1">
                  <span className="text-xs text-muted-foreground">Network:</span>
                  <Badge variant="outline" className={`text-xs ${
                    balanceData.network.includes('Mainnet') 
                      ? 'text-red-400 border-red-400/30' 
                      : 'text-yellow-400 border-yellow-400/30'
                  }`}>
                    {balanceData.network}
                  </Badge>
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4 pt-2">
                <div className="p-3 rounded-sm bg-card border border-border">
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">BNB Balance</p>
                  <p className="font-mono text-lg font-bold text-white">
                    {displayBalanceBNB.toFixed(4)}
                  </p>
                </div>
                <div className="p-3 rounded-sm bg-card border border-border">
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">USDT Balance</p>
                  <p className="font-mono text-lg font-bold text-primary">
                    {displayBalanceUSDT.toFixed(2)}
                  </p>
                </div>
              </div>

              {balanceData?.updated_at && (
                <p className="text-xs text-muted-foreground text-center pt-1">
                  Last updated: {new Date(balanceData.updated_at).toLocaleString()}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Configure Wallet Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="wallet-address" className="text-xs uppercase tracking-wider text-muted-foreground">
              Wallet Address (Optional)
            </Label>
            <Input
              id="wallet-address"
              data-testid="wallet-address-input"
              placeholder="0x... (auto-derived if empty)"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="bg-input border-border focus:border-primary font-mono text-sm"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="private-key" className="text-xs uppercase tracking-wider text-muted-foreground">
              Private Key
            </Label>
            <div className="relative">
              <Input
                id="private-key"
                data-testid="private-key-input"
                type={showPrivateKey ? "text" : "password"}
                placeholder="Enter your private key"
                value={privateKey}
                onChange={(e) => setPrivateKey(e.target.value)}
                className="bg-input border-border focus:border-primary font-mono text-sm pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPrivateKey(!showPrivateKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white"
              >
                {showPrivateKey ? (
                  <EyeOff className="w-4 h-4" strokeWidth={1.5} />
                ) : (
                  <Eye className="w-4 h-4" strokeWidth={1.5} />
                )}
              </button>
            </div>
            <p className="text-xs text-muted-foreground">
              Your private key is encrypted and stored securely
            </p>
          </div>

          <div className="bg-destructive/10 border border-destructive/30 rounded-sm p-3">
            <p className="text-xs text-destructive">
              <strong>Warning:</strong> Never share your private key. Ensure you trust this application before entering sensitive information.
            </p>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="h-10 px-6 rounded-sm"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              data-testid="save-wallet-btn"
              disabled={isSubmitting || !privateKey}
              className="bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-6 rounded-sm uppercase font-semibold"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Save Wallet
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
