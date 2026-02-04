import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import axios from "axios";
import { toast } from "sonner";
import { 
  Activity as ActivityIcon,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle,
  ArrowRight,
  DollarSign,
  Percent
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { API } from "@/App";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0 }
};

export default function Activity() {
  const [activities, setActivities] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchActivity = async () => {
    try {
      const res = await axios.get(`${API}/activity`);
      setActivities(res.data);
    } catch (error) {
      console.error("Error fetching activity:", error);
      toast.error("Failed to fetch activity logs");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchActivity();
  }, []);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchActivity();
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-success" />;
      case "failed":
        return <XCircle className="w-4 h-4 text-destructive" />;
      case "executing":
        return <Loader2 className="w-4 h-4 text-warning animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status) => {
    const variants = {
      completed: "text-success border-success/30 bg-success/10",
      failed: "text-destructive border-destructive/30 bg-destructive/10",
      executing: "text-warning border-warning/30 bg-warning/10",
      detected: "text-info border-info/30 bg-info/10",
      manual: "text-purple-400 border-purple-400/30 bg-purple-400/10"
    };

    return (
      <Badge variant="outline" className={variants[status] || "text-muted-foreground"}>
        {status.toUpperCase()}
      </Badge>
    );
  };

  const getStepStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-3 h-3 text-success" />;
      case "failed":
        return <XCircle className="w-3 h-3 text-destructive" />;
      default:
        return <Clock className="w-3 h-3 text-muted-foreground" />;
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <RefreshCw className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div data-testid="activity-page" className="p-6 md:p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-mono font-bold text-2xl md:text-3xl text-white tracking-tight uppercase">
            Activity Log
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track all arbitrage executions and transaction logs
          </p>
        </div>
        <Button 
          data-testid="refresh-activity-btn"
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

      {/* Activity Stats */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <motion.div variants={itemVariants}>
          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-sm bg-success/10">
                  <CheckCircle className="w-5 h-5 text-success" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">
                    {activities.filter(a => a.status === "completed").length}
                  </p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Completed</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-sm bg-destructive/10">
                  <XCircle className="w-5 h-5 text-destructive" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">
                    {activities.filter(a => a.status === "failed").length}
                  </p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Failed</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-sm bg-warning/10">
                  <Loader2 className="w-5 h-5 text-warning" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">
                    {activities.filter(a => a.status === "executing").length}
                  </p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">In Progress</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Card className="bg-card border-border">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-sm bg-primary/10">
                  <ActivityIcon className="w-5 h-5 text-primary" strokeWidth={1.5} />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">
                    {activities.length}
                  </p>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Total</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>

      {/* Activity List */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="font-mono text-sm uppercase tracking-wider flex items-center gap-2">
            <ActivityIcon className="w-4 h-4 text-primary" strokeWidth={1.5} />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {activities.length === 0 ? (
            <div className="text-center py-12">
              <AlertTriangle className="w-12 h-12 text-muted-foreground mx-auto mb-4" strokeWidth={1.5} />
              <p className="text-muted-foreground">No activity logs found</p>
              <p className="text-sm text-muted-foreground mt-1">
                Execute some arbitrage trades to see activity here
              </p>
            </div>
          ) : (
            <Accordion type="single" collapsible className="space-y-4">
              {activities.map((activity, index) => {
                const profit = activity.logs.find(l => l.step === "completed")?.details?.profit || 0;
                const profitPercent = activity.logs.find(l => l.step === "completed")?.details?.profit_percent || 0;
                const isProfit = profit > 0;

                return (
                  <AccordionItem 
                    key={activity.id} 
                    value={activity.id}
                    className="border border-border rounded-sm overflow-hidden"
                  >
                    <AccordionTrigger className="px-4 py-3 hover:bg-secondary/50 transition-colors [&[data-state=open]]:bg-secondary/50">
                      <div className="flex items-center justify-between w-full pr-4">
                        <div className="flex items-center gap-3">
                          {getStatusIcon(activity.status)}
                          <div className="text-left">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm font-semibold text-white">
                                {activity.token_symbol}
                              </span>
                              {getStatusBadge(activity.status)}
                              {activity.is_manual_selection && (
                                <Badge variant="outline" className="text-purple-400 border-purple-400/30 text-xs">
                                  MANUAL
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                              <span>{activity.buy_exchange}</span>
                              <ArrowRight className="w-3 h-3" />
                              <span>{activity.sell_exchange}</span>
                              <Separator orientation="vertical" className="h-3" />
                              <Clock className="w-3 h-3" />
                              <span>{formatDate(activity.detected_at)}</span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-4">
                          {activity.status === "completed" && (
                            <div className="text-right">
                              <div className={`flex items-center gap-1 font-mono text-sm font-semibold ${
                                isProfit ? 'text-success' : 'text-destructive'
                              }`}>
                                {isProfit ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                ${Math.abs(profit).toFixed(4)}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {profitPercent.toFixed(2)}% {isProfit ? 'profit' : 'loss'}
                              </div>
                            </div>
                          )}
                          
                          <div className="text-right">
                            <div className="text-sm font-mono text-white">
                              {activity.spread_percent?.toFixed(4)}%
                            </div>
                            <div className="text-xs text-muted-foreground">spread</div>
                          </div>
                        </div>
                      </div>
                    </AccordionTrigger>
                    
                    <AccordionContent className="px-4 pb-4 bg-secondary/30">
                      {/* Opportunity Details */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 pt-4">
                        <div className="p-3 rounded-sm bg-card border border-border">
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Buy Price</p>
                          <p className="font-mono text-sm text-white">${activity.buy_price?.toFixed(6)}</p>
                        </div>
                        <div className="p-3 rounded-sm bg-card border border-border">
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Sell Price</p>
                          <p className="font-mono text-sm text-white">${activity.sell_price?.toFixed(6)}</p>
                        </div>
                        <div className="p-3 rounded-sm bg-card border border-border">
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Confidence</p>
                          <p className="font-mono text-sm text-white">{activity.confidence?.toFixed(1)}%</p>
                        </div>
                        <div className="p-3 rounded-sm bg-card border border-border">
                          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Mode</p>
                          <Badge variant="outline" className={
                            activity.logs.some(l => l.is_live) 
                              ? "text-red-400 border-red-400/30" 
                              : "text-yellow-400 border-yellow-400/30"
                          }>
                            {activity.logs.some(l => l.is_live) ? "LIVE" : "TEST"}
                          </Badge>
                        </div>
                      </div>

                      {/* Transaction Logs */}
                      {activity.logs && activity.logs.length > 0 && (
                        <div>
                          <h4 className="text-xs uppercase tracking-wider text-muted-foreground mb-3">
                            Transaction Steps
                          </h4>
                          <div className="space-y-2">
                            {activity.logs.map((log, logIndex) => (
                              <div 
                                key={logIndex}
                                className="flex items-start gap-3 p-3 rounded-sm bg-card border border-border"
                              >
                                {getStepStatusIcon(log.status)}
                                <div className="flex-1">
                                  <div className="flex items-center justify-between">
                                    <span className="text-sm font-medium text-white">
                                      {log.step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                    </span>
                                    <span className="text-xs text-muted-foreground">
                                      {formatDate(log.created_at)}
                                    </span>
                                  </div>
                                  {log.details && Object.keys(log.details).length > 0 && (
                                    <div className="text-xs text-muted-foreground mt-1 font-mono">
                                      {Object.entries(log.details).map(([key, value]) => (
                                        <span key={key} className="mr-3">
                                          {key}: {typeof value === 'number' ? value.toFixed(4) : String(value)}
                                        </span>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </AccordionContent>
                  </AccordionItem>
                );
              })}
            </Accordion>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
