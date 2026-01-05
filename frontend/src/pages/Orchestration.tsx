import { useState } from 'react';
import { Rocket, Send, Loader2, CheckCircle, XCircle, Terminal } from 'lucide-react';
import api from '@/api/client';
import { useNotification } from '@/contexts/NotificationContext';

interface DeploymentResult {
    success: boolean;
    message: string;
    deployment_id?: number;
    resources_created?: string[];
    namespace?: string;
    error?: string;
}

export default function Orchestration() {
    const [command, setCommand] = useState('');
    const [deploying, setDeploying] = useState(false);
    const [result, setResult] = useState<DeploymentResult | null>(null);
    const { showNotification } = useNotification();

    const handleDeploy = async () => {
        if (!command.trim()) return;

        setDeploying(true);
        setResult(null);

        try {
            const res = await api.post('/api/orchestration/deploy', {
                command: command.trim(),
                cluster_id: 1, // Default cluster
                namespace: 'default'
            });

            setResult(res.data);

            if (res.data.success) {
                showNotification('Deployment initiated successfully', 'success');
            } else {
                showNotification('Deployment failed', 'error');
            }
        } catch (error: any) {
            console.error('Deployment failed:', error);
            setResult({
                success: false,
                message: error.response?.data?.detail || error.message || 'Deployment failed',
                error: error.response?.data?.detail || error.message
            });
            showNotification('Deployment failed', 'error');
        } finally {
            setDeploying(false);
        }
    };

    const exampleCommands = [
        'install postgresql with 10GB storage',
        'deploy redis cache',
        'install nginx ingress controller',
        'deploy authentik with postgres backend',
        'install grafana and prometheus'
    ];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                    <Rocket className="text-primary" />
                    AI Orchestration
                </h1>
                <p className="text-muted-foreground mt-1">
                    Deploy applications using natural language commands
                </p>
            </div>

            {/* Command Input */}
            <div className="bg-card border border-border rounded-xl p-6">
                <label className="block text-sm font-medium mb-2">
                    Deployment Command
                </label>
                <div className="flex gap-2">
                    <input
                        type="text"
                        value={command}
                        onChange={(e) => setCommand(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleDeploy()}
                        placeholder="e.g., install postgresql with 10GB storage"
                        disabled={deploying}
                        className="flex-1 bg-background border border-border rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                    <button
                        onClick={handleDeploy}
                        disabled={deploying || !command.trim()}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                    >
                        {deploying ? (
                            <>
                                <Loader2 size={18} className="animate-spin" />
                                Deploying...
                            </>
                        ) : (
                            <>
                                <Send size={18} />
                                Deploy
                            </>
                        )}
                    </button>
                </div>
            </div>

            {/* Example Commands */}
            <div className="bg-card border border-border rounded-xl p-6">
                <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Terminal size={16} />
                    Example Commands
                </h3>
                <div className="space-y-2">
                    {exampleCommands.map((example, idx) => (
                        <button
                            key={idx}
                            onClick={() => setCommand(example)}
                            className="block w-full text-left text-sm text-muted-foreground hover:text-foreground bg-muted/50 hover:bg-muted px-3 py-2 rounded-md transition-colors"
                        >
                            <code>{example}</code>
                        </button>
                    ))}
                </div>
            </div>

            {/* Result */}
            {result && (
                <div className={`border rounded-xl p-6 ${
                    result.success
                        ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800'
                        : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                }`}>
                    <div className="flex items-start gap-3">
                        {result.success ? (
                            <CheckCircle className="text-green-600 dark:text-green-400 mt-0.5" size={20} />
                        ) : (
                            <XCircle className="text-red-600 dark:text-red-400 mt-0.5" size={20} />
                        )}
                        <div className="flex-1">
                            <h3 className={`font-semibold mb-2 ${
                                result.success
                                    ? 'text-green-900 dark:text-green-100'
                                    : 'text-red-900 dark:text-red-100'
                            }`}>
                                {result.success ? 'Deployment Successful' : 'Deployment Failed'}
                            </h3>
                            <p className={`text-sm mb-3 ${
                                result.success
                                    ? 'text-green-700 dark:text-green-300'
                                    : 'text-red-700 dark:text-red-300'
                            }`}>
                                {result.message}
                            </p>

                            {result.namespace && (
                                <div className="text-sm mb-2">
                                    <span className="font-medium">Namespace:</span>{' '}
                                    <code className="bg-black/10 dark:bg-white/10 px-2 py-0.5 rounded">
                                        {result.namespace}
                                    </code>
                                </div>
                            )}

                            {result.resources_created && result.resources_created.length > 0 && (
                                <div className="text-sm">
                                    <span className="font-medium">Resources Created:</span>
                                    <ul className="list-disc list-inside mt-1 space-y-1">
                                        {result.resources_created.map((resource, idx) => (
                                            <li key={idx}>
                                                <code className="bg-black/10 dark:bg-white/10 px-2 py-0.5 rounded text-xs">
                                                    {resource}
                                                </code>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {result.error && (
                                <div className="mt-3 text-xs">
                                    <details>
                                        <summary className="cursor-pointer font-medium">Error Details</summary>
                                        <pre className="mt-2 bg-black/10 dark:bg-white/10 p-3 rounded overflow-auto max-h-48">
                                            {result.error}
                                        </pre>
                                    </details>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Info Box */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
                <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                    How It Works
                </h3>
                <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-2">
                    <li>• AI parses your natural language command</li>
                    <li>• Selects appropriate application blueprint</li>
                    <li>• Auto-configures storage, networking, and dependencies</li>
                    <li>• Deploys to Kubernetes with proper isolation</li>
                    <li>• All resources are tracked and managed</li>
                </ul>
            </div>
        </div>
    );
}
