import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import ProtectedRoute from '@/components/ProtectedRoute';
import Dashboard from './pages/Dashboard';
import Profiles from './pages/Profiles';
import Intelligence from './pages/Intelligence';
import Settings from './pages/Settings';
import Reports from './pages/Reports';
import Knowledge from './pages/Knowledge';
import Homelab from './pages/Homelab';
import ServerHardware from './pages/ServerHardware';
import Plugins from './pages/Plugins';
import AlertsAndThresholds from './pages/AlertsAndThresholds';
import Users from './pages/Users';
import LoginPage from './pages/LoginPage';
import Clusters from './pages/Clusters';
import Orchestration from './pages/Orchestration';
import { SidebarProvider } from '@/contexts/SidebarContext';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { ConfirmDialogProvider } from '@/contexts/ConfirmDialogContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { RoleProvider } from '@/contexts/RoleContext';

function App() {
    return (
        <ThemeProvider>
            <SidebarProvider>
                <ConfirmDialogProvider>
                    <NotificationProvider>
                        <RoleProvider>
                            <Router>
                        <Routes>
                            <Route path="/login" element={<LoginPage />} />
                            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                                <Route index element={<Dashboard />} />
                                <Route path="clusters" element={<Clusters />} />
                                <Route path="orchestration" element={<Orchestration />} />
                                <Route path="homelab" element={<Homelab />} />
                                <Route path="profiles" element={<Profiles />} />
                                <Route path="hardware" element={<ServerHardware />} />
                                <Route path="plugins" element={<Plugins />} />
                                <Route path="ai" element={<Intelligence />} />
                                <Route path="reports" element={<Reports />} />
                                <Route path="knowledge" element={<Knowledge />} />
                                <Route path="alerts" element={<AlertsAndThresholds />} />
                                <Route path="users" element={<Users />} />
                                <Route path="settings" element={<Settings />} />
                            </Route>
                        </Routes>
                        </Router>
                        </RoleProvider>
                    </NotificationProvider>
                </ConfirmDialogProvider>
            </SidebarProvider>
        </ThemeProvider>
    );
}

export default App;
