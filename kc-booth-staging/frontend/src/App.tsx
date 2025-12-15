import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from '@/components/Layout';
import { SidebarProvider } from '@/contexts/SidebarContext';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { ConfirmDialogProvider } from '@/contexts/ConfirmDialogContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { RoleProvider } from '@/contexts/RoleContext';
import Servers from './pages/Servers';

function App() {
    return (
        <ThemeProvider>
            <SidebarProvider>
                <ConfirmDialogProvider>
                    <NotificationProvider>
                        <RoleProvider>
                            <Router>
                                <Layout>
                                    <Routes>
                                        <Route path="/servers" element={<Servers />} />
                                        <Route index element={<Servers />} />
                                    </Routes>
                                </Layout>
                            </Router>
                        </RoleProvider>
                    </NotificationProvider>
                </ConfirmDialogProvider>
            </SidebarProvider>
        </ThemeProvider>
    );
}

export default App;