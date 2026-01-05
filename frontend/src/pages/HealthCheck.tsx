import { useEffect, useState } from 'react';
import { Activity, CheckCircle, XCircle, AlertTriangle, RefreshCw, Server, Database, Wifi, User } from 'lucide-react';
import api from '@/api/client';
import { motion } from 'framer-motion';

interface HealthStatus {
    status: 'healthy' | 'degraded' | 'error';
    message: string;
    details?: any;
}

interface HealthChecks {
    backend: HealthStatus;
    database: HealthStatus;
    redis: HealthStatus;
    user: HealthStatus;
}

export default function HealthCheck() {
    const [health, setHealth] = useState<HealthChecks | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastCheck, setLastCheck] = useState<Date | null>(null);

    const checkHealth = async () => {
        setLoading(true);
        setError(null);

        const checks: HealthChecks = {
            backend: { status: 'error', message: 'Not checked' },
            database: { status: 'error', message: 'Not checked' },
            redis: { status: 'error', message: 'Not checked' },
            user: { status: 'error', message: 'Not checked' },
        };

        try {
            // Check backend health endpoint
            const healthRes = await api.get('/health');
            if (healthRes.status === 200) {
                checks.backend = {
                    status: 'healthy',
                    message: 'Backend is responding',
                    details: healthRes.data,
                };

                // Parse component status if available
                if (healthRes.data.components) {
                    const components = healthRes.data.components;

                    // Database status
                    if (components.database === 'healthy') {
                        checks.database = {
                            status: 'healthy',
                            message: 'Database connection active',
                        };
                    } else {
                        checks.database = {
                            status: 'error',
                            message: 'Database connection failed',
                        };
                    }

                    // Redis status
                    if (components.redis === 'healthy') {
                        checks.redis = {
                            status: 'healthy',
                            message: 'Redis connection active',
                        };
                    } else if (components.redis === 'unavailable') {
                        checks.redis = {
                            status: 'degraded',
                            message: 'Redis unavailable (optional)',
                        };
                    } else {
                        checks.redis = {
                            status: 'error',
                            message: 'Redis connection failed',
                        };
                    }
                }
            }
        } catch (err: any) {
            checks.backend = {
                status: 'error',
                message: err.response?.data?.detail || err.message || 'Backend unreachable',
            };
            setError('Failed to connect to backend. Please check your connection.');
        }

        try {
            // Check current user authentication
            const userRes = await api.get('/auth/me');
            if (userRes.status === 200) {
                checks.user = {
                    status: 'healthy',
                    message: 'Authenticated',
                    details: {
                        email: userRes.data.email,
                        role: userRes.data.role || 'user',
                    },
                };
            }
        } catch (err: any) {
            checks.user = {
                status: 'error',
                message: 'Not authenticated or session expired',
            };
        }

        setHealth(checks);
        setLastCheck(new Date());
        setLoading(false);
    };

    useEffect(() => {
        checkHealth();
    }, []);

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'healthy':
                return <CheckCircle className="text-green-500" size={24} />;
            case 'degraded':
                return <AlertTriangle className="text-yellow-500" size={24} />;
            case 'error':
                return <XCircle className="text-red-500" size={24} />;
            default:
                return <Activity className="text-muted-foreground" size={24} />;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'healthy':
                return 'border-green-500/50 bg-green-500/10';
            case 'degraded':
                return 'border-yellow-500/50 bg-yellow-500/10';
            case 'error':
                return 'border-red-500/50 bg-red-500/10';
            default:
                return 'border-border bg-card';
        }
    };

    const overallStatus = health
        ? Object.values(health).every(check => check.status === 'healthy')
            ? 'healthy'
            : Object.values(health).some(check => check.status === 'error')
            ? 'error'
            : 'degraded'
        : 'error';

    return (
        <div className="space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Health Check</h1>
                    <p className="text-muted-foreground">
                        System status and connectivity diagnostics
                    </p>
                </div>
                <button
                    onClick={checkHealth}
                    disabled={loading}
                    className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                    <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
                    Refresh
                </button>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/50 rounded-xl p-4 flex items-center gap-3">
                    <XCircle className="text-red-500" size={24} />
                    <div>
                        <p className="font-semibold">Connection Error</p>
                        <p className="text-sm text-muted-foreground">{error}</p>
                    </div>
                </div>
            )}

            {/* Overall Status */}
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`p-8 rounded-xl border-2 ${getStatusColor(overallStatus)} transition-colors`}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        {getStatusIcon(overallStatus)}
                        <div>
                            <h2 className="text-2xl font-bold">
                                {overallStatus === 'healthy' && 'All Systems Operational'}
                                {overallStatus === 'degraded' && 'Degraded Performance'}
                                {overallStatus === 'error' && 'System Error'}
                            </h2>
                            <p className="text-sm text-muted-foreground">
                                {lastCheck
                                    ? `Last checked: ${lastCheck.toLocaleTimeString()}`
                                    : 'Checking...'}
                            </p>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Component Status */}
            <div className="grid gap-6 md:grid-cols-2">
                {/* Backend */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className={`p-6 rounded-xl border ${getStatusColor(health?.backend.status || 'error')}`}
                >
                    <div className="flex items-start gap-4">
                        <Server size={24} className="mt-1" />
                        <div className="flex-1">
                            <h3 className="font-semibold mb-1">Backend API</h3>
                            <p className="text-sm text-muted-foreground mb-3">
                                {health?.backend.message || 'Checking...'}
                            </p>
                            {health?.backend.details && (
                                <div className="text-xs font-mono bg-background/50 p-2 rounded">
                                    <div>Status: {health.backend.details.status}</div>
                                    {health.backend.details.version && (
                                        <div>Version: {health.backend.details.version}</div>
                                    )}
                                    {health.backend.details.timestamp && (
                                        <div>Time: {new Date(health.backend.details.timestamp).toLocaleString()}</div>
                                    )}
                                </div>
                            )}
                        </div>
                        {getStatusIcon(health?.backend.status || 'error')}
                    </div>
                </motion.div>

                {/* Database */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className={`p-6 rounded-xl border ${getStatusColor(health?.database.status || 'error')}`}
                >
                    <div className="flex items-start gap-4">
                        <Database size={24} className="mt-1" />
                        <div className="flex-1">
                            <h3 className="font-semibold mb-1">Database</h3>
                            <p className="text-sm text-muted-foreground">
                                {health?.database.message || 'Checking...'}
                            </p>
                        </div>
                        {getStatusIcon(health?.database.status || 'error')}
                    </div>
                </motion.div>

                {/* Redis */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                    className={`p-6 rounded-xl border ${getStatusColor(health?.redis.status || 'error')}`}
                >
                    <div className="flex items-start gap-4">
                        <Wifi size={24} className="mt-1" />
                        <div className="flex-1">
                            <h3 className="font-semibold mb-1">Redis Cache</h3>
                            <p className="text-sm text-muted-foreground">
                                {health?.redis.message || 'Checking...'}
                            </p>
                        </div>
                        {getStatusIcon(health?.redis.status || 'error')}
                    </div>
                </motion.div>

                {/* User Session */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className={`p-6 rounded-xl border ${getStatusColor(health?.user.status || 'error')}`}
                >
                    <div className="flex items-start gap-4">
                        <User size={24} className="mt-1" />
                        <div className="flex-1">
                            <h3 className="font-semibold mb-1">User Session</h3>
                            <p className="text-sm text-muted-foreground mb-3">
                                {health?.user.message || 'Checking...'}
                            </p>
                            {health?.user.details && (
                                <div className="text-xs font-mono bg-background/50 p-2 rounded">
                                    <div>Email: {health.user.details.email}</div>
                                    <div>Role: {health.user.details.role}</div>
                                </div>
                            )}
                        </div>
                        {getStatusIcon(health?.user.status || 'error')}
                    </div>
                </motion.div>
            </div>

            {/* Debug Information */}
            <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="font-semibold mb-4">Debug Information</h3>
                <div className="space-y-2 text-sm font-mono">
                    <div className="flex justify-between">
                        <span className="text-muted-foreground">API Base URL:</span>
                        <span>{api.defaults.baseURL || window.location.origin + '/api'}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-muted-foreground">Current URL:</span>
                        <span>{window.location.href}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-muted-foreground">Auth Token:</span>
                        <span>{localStorage.getItem('access_token') ? 'Present' : 'Missing'}</span>
                    </div>
                    <div className="flex justify-between">
                        <span className="text-muted-foreground">Browser:</span>
                        <span>{navigator.userAgent.split(' ').pop()}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
