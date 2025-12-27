import React from 'react';

interface ProtectedRouteProps {
    children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
    // Temporarily bypass authentication for testing
    return <>{children}</>;
}
