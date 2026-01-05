import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
        };
    }

    static getDerivedStateFromError(error: Error): State {
        return {
            hasError: true,
            error,
            errorInfo: null,
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({
            error,
            errorInfo,
        });
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
        });
    };

    handleGoHome = () => {
        window.location.href = '/';
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-screen flex items-center justify-center bg-background p-4">
                    <div className="max-w-2xl w-full bg-card border border-border rounded-xl p-8 shadow-lg">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 rounded-full bg-red-500/10">
                                <AlertTriangle size={32} className="text-red-500" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold">Something went wrong</h1>
                                <p className="text-muted-foreground">
                                    The application encountered an unexpected error
                                </p>
                            </div>
                        </div>

                        {this.state.error && (
                            <div className="mb-6 p-4 bg-muted/50 rounded-lg border border-border">
                                <h3 className="font-semibold mb-2 text-sm">Error Details:</h3>
                                <p className="text-sm font-mono text-red-400 mb-2">
                                    {this.state.error.toString()}
                                </p>
                                {this.state.errorInfo && (
                                    <details className="text-xs text-muted-foreground">
                                        <summary className="cursor-pointer hover:text-foreground">
                                            View stack trace
                                        </summary>
                                        <pre className="mt-2 p-2 bg-background rounded overflow-x-auto">
                                            {this.state.errorInfo.componentStack}
                                        </pre>
                                    </details>
                                )}
                            </div>
                        )}

                        <div className="flex gap-3">
                            <button
                                onClick={this.handleReset}
                                className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                            >
                                <RefreshCw size={18} />
                                Try Again
                            </button>
                            <button
                                onClick={this.handleGoHome}
                                className="flex items-center gap-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/90 transition-colors"
                            >
                                <Home size={18} />
                                Go Home
                            </button>
                        </div>

                        <div className="mt-6 p-4 bg-muted/30 rounded-lg text-sm text-muted-foreground">
                            <p className="mb-2">If this error persists:</p>
                            <ul className="list-disc list-inside space-y-1">
                                <li>Try refreshing the page</li>
                                <li>Clear your browser cache</li>
                                <li>Check the browser console for more details</li>
                                <li>Contact support if the issue continues</li>
                            </ul>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
