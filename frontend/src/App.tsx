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
import Automations from './pages/Automations';
import Plugins from './pages/Plugins';
import PluginMetrics from './pages/PluginMetrics';
import Thresholds from './pages/Thresholds';
import Alerts from './pages/Alerts';
import Users from './pages/Users';
import LoginPage from './pages/LoginPage';
import Deployments from './pages/Deployments';
import PluginMarketplace from './pages/PluginMarketplace';
import DashboardBuilder from './pages/DashboardBuilder';
import { SidebarProvider } from '@/contexts/SidebarContext';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { ConfirmDialogProvider } from '@/contexts/ConfirmDialogContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { RoleProvider } from '@/contexts/RoleContext';
import { UpdatesProvider } from '@/contexts/UpdatesContext';

function App() {
    return (
        <ThemeProvider>
            <SidebarProvider>
                <ConfirmDialogProvider>
                    <NotificationProvider>
                        <UpdatesProvider>
                            <RoleProvider>
                            <Router>
                        <Routes>
                            <Route path="/login" element={<LoginPage />} />
                            <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                                <Route index element={<Dashboard />} />
                                <Route path="homelab" element={<Homelab />} />
                                <Route path="profiles" element={<Profiles />} />
                                <Route path="hardware" element={<ServerHardware />} />
                                <Route path="plugins" element={<Plugins />} />
                                <Route path="plugins/:pluginId/metrics" element={<PluginMetrics />} />
                                <Route path="marketplace" element={<PluginMarketplace />} />
                                <Route path="dashboards" element={<DashboardBuilder />} />
                                <Route path="ai" element={<Intelligence />} />
                                <Route path="reports" element={<Reports />} />
                                <Route path="knowledge" element={<Knowledge />} />
                                <Route path="thresholds" element={<Thresholds />} />
                                <Route path="alerts" element={<Alerts />} />
                                <Route path="automations" element={<Automations />} />
                                <Route path="users" element={<Users />} />
                                <Route path="deployments" element={<Deployments />} />
                                <Route path="settings" element={<Settings />} />
                            </Route>
                        </Routes>
                        </Router>
                            </RoleProvider>
                        </UpdatesProvider>
                    </NotificationProvider>
                </ConfirmDialogProvider>
            </SidebarProvider>
        </ThemeProvider>
    );
}

export default App;