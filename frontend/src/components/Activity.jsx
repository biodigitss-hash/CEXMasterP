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
            <div className="space-y-4">
              {activities.map((activity, index) => (
                <div 
                  key={activity.id || index}
                  className="border border-border rounded-sm overflow-hidden bg-card"
                >
                  <div className="px-4 py-3 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getStatusIcon(activity.status)}
                      <div className="text-left">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-semibold text-white">
                            {activity.token_symbol || 'Unknown'}
                          </span>
                          {getStatusBadge(activity.status)}
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                          <span>{activity.buy_exchange || 'N/A'}</span>
                          <ArrowRight className="w-3 h-3" />
                          <span>{activity.sell_exchange || 'N/A'}</span>
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="text-sm font-mono text-white">
                        {activity.spread_percent ? `${activity.spread_percent.toFixed(4)}%` : 'N/A'}
                      </div>
                      <div className="text-xs text-muted-foreground">spread</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
