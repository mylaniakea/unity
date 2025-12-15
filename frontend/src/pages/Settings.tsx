
import { useEffect, useState } from 'react';
import { Save, Shield, Cpu, CircuitBoard, Brain, Bell, Clock, Lock, Eye, EyeOff } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '@/api/client';
import { cn } from '@/lib/utils';
import { useNotification } from '@/contexts/NotificationContext';

interface ProviderConfig {
    url?: string;
    api_key?: string;
    enabled: boolean;
    models?: string[]; // Add models array
    active_model?: string; // Add active_model
}

interface SettingsData {
    id: number;
    providers: {
        [key: string]: ProviderConfig; // Allow dynamic provider keys
    };
    active_model: string;
    primary_provider: string;
    fallback_provider: string;
    system_prompt?: string; // Make system_prompt optional
    alert_sound_enabled: boolean; // New: Enable sound notifications for critical alerts
    push_notifications_enabled: boolean; // New: Enable browser push notifications
    maintenance_mode_until: string | null; // New: Time until maintenance mode is active
}

// Utility function to convert VAPID public key to Uint8Array
function urlBase64ToUint8Array(base64String: string) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

export default function Settings() {
    const [settings, setSettings] = useState<SettingsData | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const { showNotification } = useNotification();
    const [vapidPublicKey, setVapidPublicKey] = useState<string | null>(null);
    const [notificationPermission, setNotificationPermission] = useState<NotificationPermission>('default');
    const [isSubscribed, setIsSubscribed] = useState(false);

    // Password change state
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [changingPassword, setChangingPassword] = useState(false);
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    useEffect(() => {
        fetchSettings();
        checkPushSubscription();
        // Fetch VAPID public key
        api.get('/push/vapid-public-key').then(res => {
            setVapidPublicKey(res.data.publicKey);
        }).catch(error => {
            console.error("Failed to fetch VAPID public key", error);
            showNotification("Failed to load push notification settings.", "error");
        });

        if ('Notification' in window) {
            setNotificationPermission(Notification.permission);
        }
    }, []);

    const checkPushSubscription = async () => {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
            setIsSubscribed(false);
            return;
        }

        try {
            const registration = await navigator.serviceWorker.ready;
            const subscription = await registration.pushManager.getSubscription();
            setIsSubscribed(!!subscription);
        } catch (error) {
            console.error("Error checking push subscription:", error);
            setIsSubscribed(false);
        }
    };

    const fetchSettings = async () => {
        try {
            const settingsRes = await api.get('/settings/');
            const modelsRes = await api.get('/ai/models');
            
            const fetchedSettings = settingsRes.data;
            const availableModels = modelsRes.data.models;

            // Merge available models into provider configs
            for (const providerName in availableModels) {
                if (fetchedSettings.providers[providerName]) {
                    fetchedSettings.providers[providerName].models = availableModels[providerName];
                }
            }
            // Ensure push_notifications_enabled is always present, default to false
            if (fetchedSettings.push_notifications_enabled === undefined) {
                fetchedSettings.push_notifications_enabled = false;
            }
            setSettings(fetchedSettings);
            setLoading(false);
        } catch (error) {
            console.error("Failed to fetch settings or models", error);
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!settings) return;
        setSaving(true);
        try {
            await api.put('/settings/', settings);
            showNotification("Settings saved successfully", "success");
        } catch (error) {
            console.error("Failed to save settings", error);
            showNotification("Failed to save settings", "error");
        } finally {
            setSaving(false);
        }
    };

    const updateProvider = (provider: string, field: string, value: any) => {
        if (!settings) return;
        setSettings({
            ...settings,
            providers: {
                ...settings.providers,
                [provider]: {
                    ...settings.providers[provider as keyof typeof settings.providers],
                    [field]: value
                }
            }
        });
    };

    const updateSetting = (field: string, value: any) => {
        if (!settings) return;
        setSettings({ ...settings, [field]: value });
    };

    const handlePushNotificationToggle = async (enabled: boolean) => {
        if (!settings) return;

        if (enabled) {
            // Enable push notifications
            if (notificationPermission === 'denied') {
                showNotification("Notification permission denied. Please enable it in browser settings.", "error");
                return;
            }
            if (!vapidPublicKey) {
                showNotification("VAPID public key not loaded. Cannot subscribe to push notifications.", "error");
                return;
            }
            if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
                showNotification("Push notifications not supported by your browser.", "error");
                return;
            }

            try {
                const permissionResult = await Notification.requestPermission();
                setNotificationPermission(permissionResult);

                if (permissionResult === 'granted') {
                    const registration = await navigator.serviceWorker.ready;
                    const subscribeOptions = {
                        userVisibleOnly: true,
                        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey!)
                    };
                    const subscription = await registration.pushManager.subscribe(subscribeOptions);
                    
                    // Send subscription to backend
                    await api.post('/push/subscribe', {
                        endpoint: subscription.endpoint,
                        p256dh: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('p256dh')) as any)),
                        auth: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('auth')) as any))
                    });
                    setSettings({ ...settings, push_notifications_enabled: true });
                    setIsSubscribed(true);
                    showNotification("Push notifications enabled!", "success");
                } else {
                    setSettings({ ...settings, push_notifications_enabled: false });
                    setIsSubscribed(false);
                    showNotification("Notification permission denied.", "error");
                }
            } catch (error) {
                console.error("Error enabling push notifications:", error);
                showNotification("Failed to enable push notifications.", "error");
                setSettings({ ...settings, push_notifications_enabled: false });
                setIsSubscribed(false);
            }
        } else {
            // Disable push notifications
            if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
                showNotification("Push notifications not supported by your browser.", "error");
                return;
            }

            try {
                const registration = await navigator.serviceWorker.ready;
                const subscription = await registration.pushManager.getSubscription();

                if (subscription) {
                    await subscription.unsubscribe();
                    // Also tell backend to remove subscription
                    await api.post('/push/unsubscribe', {
                        endpoint: subscription.endpoint,
                        p256dh: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('p256dh')) as any)),
                        auth: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('auth')) as any))
                    });
                    setSettings({ ...settings, push_notifications_enabled: false });
                    setIsSubscribed(false);
                    showNotification("Push notifications disabled.", "info");
                } else {
                    setSettings({ ...settings, push_notifications_enabled: false });
                    setIsSubscribed(false);
                    showNotification("You are not subscribed to push notifications.", "info");
                }
            } catch (error) {
                console.error("Error disabling push notifications:", error);
                showNotification("Failed to disable push notifications.", "error");
                setSettings({ ...settings, push_notifications_enabled: true });
            }
        }
    };

    const handleMaintenanceModeToggle = async (enabled: boolean) => {
        if (!settings) return;

        try {
            let newMaintenanceModeUntil: string | null = null;
            if (enabled) {
                // Set for 1 hour initially, user can extend later
                const now = new Date();
                now.setHours(now.getHours() + 1);
                newMaintenanceModeUntil = now.toISOString();
                showNotification("Maintenance mode enabled for 1 hour.", "info");
            } else {
                showNotification("Maintenance mode disabled.", "info");
            }

            const updatedSettings = {
                ...settings,
                maintenance_mode_until: newMaintenanceModeUntil,
            };
            await api.put('/settings/', updatedSettings);
            setSettings(updatedSettings);
        } catch (error) {
            console.error("Failed to toggle maintenance mode:", error);
            showNotification("Failed to toggle maintenance mode.", "error");
        }
    };

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault();

        // Validate passwords
        if (newPassword.length < 8) {
            showNotification("New password must be at least 8 characters long.", "error");
            return;
        }

        if (newPassword !== confirmPassword) {
            showNotification("New passwords do not match.", "error");
            return;
        }

        setChangingPassword(true);
        try {
            await api.post('/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            });
            showNotification("Password changed successfully!", "success");
            // Clear form
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (error: any) {
            console.error("Failed to change password:", error);
            showNotification(error.response?.data?.detail || "Failed to change password", "error");
        } finally {
            setChangingPassword(false);
        }
    };

    const getPasswordStrength = (password: string): { strength: string; color: string; width: string } => {
        if (password.length === 0) return { strength: '', color: '', width: '0%' };
        if (password.length < 8) return { strength: 'Too short', color: 'bg-red-500', width: '25%' };

        let strength = 0;
        if (password.length >= 8) strength++;
        if (password.length >= 12) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/\d/.test(password)) strength++;
        if (/[^a-zA-Z\d]/.test(password)) strength++;

        if (strength <= 2) return { strength: 'Weak', color: 'bg-orange-500', width: '50%' };
        if (strength <= 4) return { strength: 'Good', color: 'bg-yellow-500', width: '75%' };
        return { strength: 'Strong', color: 'bg-green-500', width: '100%' };
    };

    const passwordStrength = getPasswordStrength(newPassword);

    if (loading) return <div className="p-8">Loading settings...</div>;
    if (!settings) return <div className="p-8">Error loading settings.</div>;

    const providers = ['ollama', 'google', 'openai', 'anthropic'];

    return (
        <div className="space-y-8 max-w-4xl">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Intelligence Settings</h1>
                    <p className="text-muted-foreground">Configure AI providers and orchestration logic</p>
                </div>
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-2 bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                    <Save size={18} />
                    {saving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
                {/* Global Config */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="md:col-span-2 bg-card border border-border p-6 rounded-xl space-y-4"
                >
                    <div className="flex items-center gap-3 border-b border-border pb-4 mb-4">
                        <CircuitBoard className="text-primary" />
                        <h2 className="text-xl font-semibold">Orchestration</h2>
                    </div>

                    <div className="grid md:grid-cols-2 gap-4">
                        {/* Left Column: Primary and Fallback Providers */}
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Primary Provider</label>
                                <select
                                    value={settings.primary_provider}
                                    onChange={(e) => setSettings({ ...settings, primary_provider: e.target.value })}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2"
                                >
                                    {providers.map(p => <option key={p} value={p}>{p.toUpperCase()}</option>)}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-sm font-medium">Fallback Provider</label>
                                <select
                                    value={settings.fallback_provider}
                                    onChange={(e) => updateSetting('fallback_provider', e.target.value)}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2"
                                >
                                    {providers.map(p => <option key={p} value={p}>{p.toUpperCase()}</option>)}
                                </select>
                            </div>
                        </div>
                        {/* Right Column: Active Model */}
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Active Model</label>
                            <select
                                value={settings.active_model || ''}
                                onChange={(e) => updateSetting('active_model', e.target.value)}
                                className="w-full bg-background border border-border rounded-md px-3 py-2"
                            >
                                <option value="">Default (Provider specific)</option>
                                {Object.values(settings.providers).flatMap(p => p.enabled && p.models ? p.models.map(model => ({
                                    provider: Object.keys(settings.providers).find(key => settings.providers[key] === p),
                                    model: model
                                })) : []).map((item, index) => (
                                    <option key={index} value={item.model}>
                                        {item.provider.toUpperCase()}: {item.model}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </motion.div>

                {/* System Prompt (Agent Brain) */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="md:col-span-2 bg-card border border-border p-6 rounded-xl space-y-4"
                >
                    <div className="flex items-center gap-3 border-b border-border pb-4 mb-4">
                        <Brain className="text-primary" />
                        <h2 className="text-xl font-semibold">Agent Personality & Context</h2>
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-1">System Prompt</label>
                        <textarea
                            value={(settings as any).system_prompt || ""}
                            onChange={(e) => updateSetting('system_prompt', e.target.value)}
                            className="w-full bg-background border border-border rounded-md px-3 py-2 min-h-[150px] font-mono text-sm"
                            placeholder="You are a helpful assistant..."
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                            The core instructions for your Agent. It will also receive Server Profiles and Knowledge Base items dynamically.
                        </p>
                    </div>
                </motion.div>

                {/* Alert Sound Settings */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="md:col-span-2 bg-card border border-border p-6 rounded-xl space-y-4"
                >
                    <div className="flex items-center gap-3 border-b border-border pb-4 mb-4">
                        <Bell className="text-primary" />
                        <h2 className="text-xl font-semibold">Alert Notifications</h2>
                    </div>
                    <div className="flex items-center justify-between">
                        <div>
                            <label htmlFor="alertSoundToggle" className="block text-sm font-medium">Enable Alert Sounds</label>
                            <p className="text-xs text-muted-foreground">Play a sound for critical alerts.</p>
                        </div>
                        <input
                            type="checkbox"
                            id="alertSoundToggle"
                            checked={settings.alert_sound_enabled}
                            onChange={(e) => updateSetting('alert_sound_enabled', e.target.checked)}
                            className="h-4 w-4 accent-primary"
                        />
                    </div>
                </motion.div>

                {/* Maintenance Mode Settings */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="md:col-span-2 bg-card border border-border p-6 rounded-xl space-y-4"
                >
                    <div className="flex items-center gap-3 border-b border-border pb-4 mb-4">
                        <Clock className="text-primary" />
                        <h2 className="text-xl font-semibold">Maintenance Mode</h2>
                    </div>
                    <div className="flex items-center justify-between">
                        <div>
                            <label htmlFor="maintenanceModeToggle" className="block text-sm font-medium">Enable Maintenance Mode</label>
                            <p className="text-xs text-muted-foreground">Suppresses all new alerts during maintenance window.</p>
                        </div>
                        <input
                            type="checkbox"
                            id="maintenanceModeToggle"
                            checked={!!settings.maintenance_mode_until}
                            onChange={(e) => handleMaintenanceModeToggle(e.target.checked)}
                            className="h-4 w-4 accent-primary"
                        />
                    </div>
                    {settings.maintenance_mode_until && (
                        <div className="text-sm text-muted-foreground mt-2">
                            Active until: {new Date(settings.maintenance_mode_until).toLocaleString()}
                        </div>
                    )}
                </motion.div>

                {/* Security - Change Password */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="md:col-span-2 bg-card border border-border p-6 rounded-xl space-y-4"
                >
                    <div className="flex items-center gap-3 border-b border-border pb-4 mb-4">
                        <Lock className="text-primary" />
                        <h2 className="text-xl font-semibold">Security</h2>
                    </div>
                    <form onSubmit={handlePasswordChange} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Current Password</label>
                            <div className="relative">
                                <input
                                    type={showCurrentPassword ? "text" : "password"}
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 pr-10"
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">New Password</label>
                            <div className="relative">
                                <input
                                    type={showNewPassword ? "text" : "password"}
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 pr-10"
                                    required
                                    minLength={8}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNewPassword(!showNewPassword)}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                            {newPassword && (
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                                            <div
                                                className={cn("h-full transition-all", passwordStrength.color)}
                                                style={{ width: passwordStrength.width }}
                                            />
                                        </div>
                                        <span className="text-xs text-muted-foreground">{passwordStrength.strength}</span>
                                    </div>
                                    <p className="text-xs text-muted-foreground">
                                        Requirements: Minimum 8 characters. Strong passwords include uppercase, lowercase, numbers, and special characters.
                                    </p>
                                </div>
                            )}
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Confirm New Password</label>
                            <div className="relative">
                                <input
                                    type={showConfirmPassword ? "text" : "password"}
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 pr-10"
                                    required
                                    minLength={8}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                            {confirmPassword && newPassword !== confirmPassword && (
                                <p className="text-xs text-red-500">Passwords do not match</p>
                            )}
                        </div>

                        <button
                            type="submit"
                            disabled={changingPassword || !currentPassword || !newPassword || !confirmPassword || newPassword !== confirmPassword}
                            className="bg-primary text-primary-foreground px-6 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {changingPassword ? 'Changing Password...' : 'Change Password'}
                        </button>
                    </form>
                </motion.div>

                {/* Browser Push Notifications */}
                <motion.div
                    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className="md:col-span-2 bg-card border border-border p-6 rounded-xl space-y-4"
                >
                    <div className="flex items-center gap-3 border-b border-border pb-4 mb-4">
                        <Bell className="text-primary" />
                        <h2 className="text-xl font-semibold">Browser Push Notifications</h2>
                    </div>
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div>
                                <label htmlFor="pushNotificationToggle" className="block text-sm font-medium">Enable Push Notifications</label>
                                <p className="text-xs text-muted-foreground">Receive desktop notifications even when the tab is in the background.</p>
                            </div>
                            <input
                                type="checkbox"
                                id="pushNotificationToggle"
                                checked={settings.push_notifications_enabled}
                                onChange={(e) => handlePushNotificationToggle(e.target.checked)}
                                className="h-4 w-4 accent-primary"
                                disabled={notificationPermission === 'denied' || !vapidPublicKey}
                            />
                        </div>
                        <div className="text-sm text-muted-foreground">
                            Current permission status: <span className="font-semibold capitalize">{notificationPermission}</span>
                            {(notificationPermission === 'denied') && (
                                <p className="text-red-500 text-xs mt-1">Please enable notifications in your browser settings to receive push alerts.</p>
                            )}
                        </div>
                    </div>
                </motion.div>

                {/* Provider Cards */}
                {providers.map((provider, i) => {
                    const config = settings.providers[provider as keyof typeof settings.providers];
                    return (
                        <motion.div
                            key={provider}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.1 }}
                            className={cn(
                                "bg-card border p-6 rounded-xl space-y-4 transition-colors",
                                config.enabled ? "border-primary/50" : "border-border opacity-75"
                            )}
                        >
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Shield size={20} className={config.enabled ? "text-primary" : "text-muted-foreground"} />
                                    <h3 className="font-bold capitalize">{provider}</h3>
                                </div>
                                <div className="flex items-center gap-2">
                                    <label className="text-xs text-muted-foreground">Enabled</label>
                                    <input
                                        type="checkbox"
                                        checked={config.enabled}
                                        onChange={(e) => updateProvider(provider, 'enabled', e.target.checked)}
                                        className="h-4 w-4 accent-primary"
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                {provider === 'ollama' ? (
                                    <div className="space-y-2">
                                        <label className="text-xs uppercase tracking-wider text-muted-foreground">Base URL</label>
                                        <input
                                            type="text"
                                            value={config.url}
                                            onChange={(e) => updateProvider(provider, 'url', e.target.value)}
                                            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm font-mono"
                                            disabled={!config.enabled}
                                        />
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        <label className="text-xs uppercase tracking-wider text-muted-foreground">API Key</label>
                                        <input
                                            type="password"
                                            value={config.api_key}
                                            onChange={(e) => updateProvider(provider, 'api_key', e.target.value)}
                                            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm font-mono"
                                            placeholder="sk-..."
                                            disabled={!config.enabled}
                                        />
                                    </div>
                                )}
                                {config.enabled && config.models && config.models.length > 0 && (
                                    <div className="space-y-2">
                                        <label className="text-xs uppercase tracking-wider text-muted-foreground">Active Model</label>
                                        <select
                                            value={config.active_model || ''}
                                            onChange={(e) => updateProvider(provider, 'active_model', e.target.value)}
                                            className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm font-mono"
                                        >
                                            {config.models.map(model => (
                                                <option key={model} value={model}>
                                                    {model}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    );
                })}


            </div>
        </div>
    );
}
