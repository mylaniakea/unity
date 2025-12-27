import React from 'react';
import Plugins from './pages/Plugins';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from '@/components/LayoutSimple';
import { SidebarProvider } from '@/contexts/SidebarContext';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { RoleProvider } from '@/contexts/RoleContext';
import { UpdatesProvider } from '@/contexts/UpdatesContext';

function SimpleDashboard() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">Dashboard</h1>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <p className="text-gray-700 dark:text-gray-300">
          Dashboard page - API endpoints will be added next
        </p>
      </div>
    </div>
  );
}

function PluginsPage() {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">Plugins</h1>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <p className="text-gray-700 dark:text-gray-300">
          Plugins page - will connect to /api/plugins
        </p>
      </div>
    </div>
  );
}

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">{title}</h1>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <p className="text-gray-700 dark:text-gray-300">
          {title} page - placeholder
        </p>
      </div>
    </div>
  );
}

function App() {
    return (
        <ThemeProvider>
            <SidebarProvider>
                <NotificationProvider>
                    <UpdatesProvider>
                        <RoleProvider>
                            <Router>
                                <Routes>
                                    <Route path="/" element={<Layout />}>
                                        <Route index element={<Dashboard />} />
                                        <Route path="plugins" element={<Plugins />} />
                                        <Route path="homelab" element={<PlaceholderPage title="Homelab" />} />
                                        <Route path="profiles" element={<PlaceholderPage title="Profiles" />} />
                                        <Route path="hardware" element={<PlaceholderPage title="Hardware" />} />
                                        <Route path="ai" element={<PlaceholderPage title="AI Intelligence" />} />
                                        <Route path="reports" element={<PlaceholderPage title="Reports" />} />
                                        <Route path="knowledge" element={<PlaceholderPage title="Knowledge" />} />
                                        <Route path="thresholds" element={<PlaceholderPage title="Thresholds" />} />
                                        <Route path="alerts" element={<PlaceholderPage title="Alerts" />} />
                                        <Route path="automations" element={<PlaceholderPage title="Automations" />} />
                                        <Route path="users" element={<PlaceholderPage title="Users" />} />
                                        <Route path="deployments" element={<PlaceholderPage title="Deployments" />} />
                                        <Route path="settings" element={<Settings />} />
                                    </Route>
                                </Routes>
                            </Router>
                        </RoleProvider>
                    </UpdatesProvider>
                </NotificationProvider>
            </SidebarProvider>
        </ThemeProvider>
    );
}

export default App;
