import { useLocation } from 'react-router-dom';

export default function PlaceholderPage() {
    const location = useLocation();
    const pageName = location.pathname.split('/').pop() || 'Dashboard';
    const title = pageName.charAt(0).toUpperCase() + pageName.slice(1);

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold tracking-tight text-foreground">{title}</h1>
            </div>
            <div className="p-12 border-2 border-dashed border-border rounded-lg flex flex-col items-center justify-center text-muted-foreground bg-card/50">
                <p className="text-lg font-medium">Coming Soon</p>
                <p className="text-sm">This page has not been ported yet.</p>
                <p className="text-xs mt-4 font-mono">{location.pathname}</p>
            </div>
        </div>
    );
}
