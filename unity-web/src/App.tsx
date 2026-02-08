import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from '@/components/layout';
import PlaceholderPage from '@/pages/placeholder-page';
import Dashboard from '@/pages/dashboard';
import Clusters from '@/pages/clusters';
import Orchestration from '@/pages/orchestration';
import Homelab from '@/pages/homelab';
import Profiles from '@/pages/profiles';
import Hardware from '@/pages/hardware';
import Plugins from '@/pages/plugins';
import Intelligence from '@/pages/intelligence';
import Reports from '@/pages/reports';
import Knowledge from '@/pages/knowledge';
import Alerts from '@/pages/alerts';
import Users from '@/pages/users';
import Settings from '@/pages/settings';
import { SidebarProvider } from '@/contexts/sidebar-context';
import { RoleProvider } from '@/contexts/role-context';
import { NotificationProvider } from '@/contexts/notification-context';
import { ConfirmDialogProvider } from '@/contexts/confirm-dialog-context';
import { ThemeProvider } from '@/components/theme-provider';
import { UpdatesProvider } from '@/contexts/updates-context';

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="vite-ui-theme">
      <ConfirmDialogProvider>
        <NotificationProvider>
          <UpdatesProvider>
            <RoleProvider>
              <SidebarProvider>
                <Router>
                  <Routes>
                    <Route path="/login" element={<PlaceholderPage />} />
                    <Route path="/" element={<Layout />}>
                      <Route index element={<Dashboard />} />
                      <Route path="clusters" element={<Clusters />} />
                      <Route path="orchestration" element={<Orchestration />} />
                      <Route path="homelab" element={<Homelab />} />
                      <Route path="profiles" element={<Profiles />} />
                      <Route path="hardware" element={<Hardware />} />
                      <Route path="plugins" element={<Plugins />} />
                      <Route path="ai" element={<Intelligence />} />
                      <Route path="reports" element={<Reports />} />
                      <Route path="knowledge" element={<Knowledge />} />
                      <Route path="alerts" element={<Alerts />} />
                      <Route path="users" element={<Users />} />
                      <Route path="settings" element={<Settings />} />
                      {/* Catch all - redirect to dashboard for now */}
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Route>
                  </Routes>
                </Router>
              </SidebarProvider>
            </RoleProvider>
          </UpdatesProvider>
        </NotificationProvider>
      </ConfirmDialogProvider>
    </ThemeProvider >
  );
}

export default App;
