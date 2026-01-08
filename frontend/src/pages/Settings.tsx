import React, { useEffect, useState } from 'react';
import api from '@/api/client';
import { useNotification } from '@/contexts/NotificationContext';
import { Save, Eye, EyeOff, Settings as SettingsIcon, Key, Cog, Lock } from 'lucide-react';

// Type definitions
interface ProviderConfig {
  url: string;
  api_key: string;
  enabled: boolean;
  models: string[];
  active_model?: string;
}

interface SettingsData {
  id?: number;
  providers: {
    ollama: ProviderConfig;
    google: ProviderConfig;
    openai: ProviderConfig;
    anthropic: ProviderConfig;
  };
  active_model: string;
  primary_provider: string;
  fallback_provider: string;
  system_prompt: string;
  alert_sound_enabled: boolean;
  push_notifications_enabled: boolean;
  maintenance_mode_until: string | null;
  cron_24hr_report?: string;
  cron_7day_report?: string;
  cron_monthly_report?: string;
  polling_interval?: number;
}

const Settings: React.FC = () => {
  const { showNotification } = useNotification();
  const [activeTab, setActiveTab] = useState<'ai' | 'password' | 'automations'>('ai');
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  
  // Push notifications state
  const [vapidPublicKey, setVapidPublicKey] = useState<string>('');
  const [pushNotificationStatus, setPushNotificationStatus] = useState<'default' | 'granted' | 'denied'>('default');

  useEffect(() => {
    fetchSettings();
    fetchVapidKey();
    checkPushPermission();
  }, []);

  const checkPushPermission = () => {
    if ('Notification' in window) {
      setPushNotificationStatus(Notification.permission);
    }
  };

  const fetchVapidKey = async () => {
    try {
      const res = await api.get('/push/vapid-public-key');
      setVapidPublicKey(res.data.public_key);
    } catch (error) {
      console.error('Failed to fetch VAPID key', error);
    }
  };

  const fetchSettings = async () => {
    try {
      const res = await api.get('/settings/');
      const modelsRes = await api.get('/ai/models');
      const settingsObj = res.data; // Backend returns object directly, not array

      const providers = typeof settingsObj.providers === 'string' 
        ? JSON.parse(settingsObj.providers) 
        : settingsObj.providers || {};
      
      // Ensure all providers have models array and merge models into provider configs
      ['ollama', 'google', 'openai', 'anthropic'].forEach((providerName) => {
        if (!providers[providerName]) {
          providers[providerName] = { url: '', api_key: '', enabled: false, models: [] };
        }
        if (!providers[providerName].models) {
          providers[providerName].models = [];
        }
        if (modelsRes.data[providerName]) {
          providers[providerName].models = modelsRes.data[providerName];
        }
      });

      const settingsData: SettingsData = {
        providers,
        active_model: settingsObj.active_model || '',
        primary_provider: settingsObj.primary_provider || 'ollama',
        fallback_provider: settingsObj.fallback_provider || 'openai',
        system_prompt: settingsObj.system_prompt || '',
        alert_sound_enabled: settingsObj.alert_sound_enabled === true || settingsObj.alert_sound_enabled === 'true',
        push_notifications_enabled: settingsObj.push_notifications_enabled === true || settingsObj.push_notifications_enabled === 'true' || false,
        maintenance_mode_until: settingsObj.maintenance_mode_until || null,
        cron_24hr_report: settingsObj.cron_24hr_report || '0 2 * * *',
        cron_7day_report: settingsObj.cron_7day_report || '0 3 * * 1',
        cron_monthly_report: settingsObj.cron_monthly_report || '0 4 1 * *',
        polling_interval: typeof settingsObj.polling_interval === 'number' 
          ? settingsObj.polling_interval 
          : parseInt(settingsObj.polling_interval || '30'),
      };

      setSettings(settingsData);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch settings', error);
      showNotification('Failed to load settings.', 'error');
      setLoading(false);
    }
  };

  const updateProvider = (provider: keyof SettingsData['providers'], key: string, value: any) => {
    if (!settings) return;
    setSettings({
      ...settings,
      providers: {
        ...settings.providers,
        [provider]: {
          ...settings.providers[provider],
          [key]: value,
        },
      },
    });
  };

  const updateSetting = (key: keyof SettingsData, value: any) => {
    if (!settings) return;
    setSettings({
      ...settings,
      [key]: value,
    });
  };

  const handleSave = async () => {
    if (!settings) return;

    try {
      await api.put('/settings/', {
        providers: settings.providers, // Send as object, not stringified
        active_model: settings.active_model,
        primary_provider: settings.primary_provider,
        fallback_provider: settings.fallback_provider,
        system_prompt: settings.system_prompt,
        alert_sound_enabled: settings.alert_sound_enabled,
        push_notifications_enabled: settings.push_notifications_enabled,
        maintenance_mode_until: settings.maintenance_mode_until,
        cron_24hr_report: settings.cron_24hr_report,
        cron_7day_report: settings.cron_7day_report,
        cron_monthly_report: settings.cron_monthly_report,
        polling_interval: settings.polling_interval,
      });
      showNotification('Settings saved successfully!', 'success');
    } catch (error) {
      console.error('Failed to save settings', error);
      showNotification('Failed to save settings.', 'error');
    }
  };

  const handlePasswordChange = async () => {
    if (newPassword.length < 8) {
      showNotification('New password must be at least 8 characters long.', 'error');
      return;
    }
    if (newPassword !== confirmPassword) {
      showNotification('New passwords do not match.', 'error');
      return;
    }

    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      showNotification('Password changed successfully!', 'success');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: any) {
      console.error('Failed to change password', error);
      showNotification(error.response?.data?.detail || 'Failed to change password.', 'error');
    }
  };

  const handlePushNotificationToggle = async (enabled: boolean) => {
    if (enabled) {
      if (!('Notification' in window)) {
        showNotification('Browser does not support push notifications.', 'error');
        return;
      }

      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        showNotification('Push notification permission denied.', 'error');
        return;
      }

      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: vapidPublicKey,
        });

        await api.post('/push/subscribe', subscription.toJSON());
        updateSetting('push_notifications_enabled', true);
        showNotification('Push notifications enabled!', 'success');
        setPushNotificationStatus('granted');
      } catch (error) {
        console.error('Failed to enable push notifications', error);
        showNotification('Failed to enable push notifications.', 'error');
      }
    } else {
      try {
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        if (subscription) {
          await subscription.unsubscribe();
          await api.post('/push/unsubscribe', subscription.toJSON());
        }
        updateSetting('push_notifications_enabled', false);
        showNotification('Push notifications disabled.', 'success');
      } catch (error) {
        console.error('Failed to disable push notifications', error);
        showNotification('Failed to disable push notifications.', 'error');
      }
    }
  };

  const handleMaintenanceModeToggle = async (enabled: boolean) => {
    const until = enabled ? new Date(Date.now() + 60 * 60 * 1000).toISOString() : null;
    updateSetting('maintenance_mode_until', until);
    
    try {
      await api.put('/settings/', {
        maintenance_mode_until: until,
      });
      showNotification(
        enabled ? 'Maintenance mode enabled for 1 hour.' : 'Maintenance mode disabled.',
        'success'
      );
    } catch (error) {
      console.error('Failed to update maintenance mode', error);
      showNotification('Failed to update maintenance mode.', 'error');
    }
  };

  const getPasswordStrength = (password: string): { strength: number; label: string; color: string } => {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.length >= 12) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z\d]/.test(password)) strength++;

    if (strength <= 1) return { strength: 1, label: 'Weak', color: 'bg-red-500' };
    if (strength <= 3) return { strength: 2, label: 'Medium', color: 'bg-yellow-500' };
    return { strength: 3, label: 'Strong', color: 'bg-green-500' };
  };

  const passwordStrength = getPasswordStrength(newPassword);

  // Automation helpers
  const generateTimeOptions = () => {
    const options = [];
    for (let h = 0; h < 24; h++) {
      for (let m = 0; m < 60; m += 30) {
        const hour = h.toString().padStart(2, '0');
        const minute = m.toString().padStart(2, '0');
        options.push({
          label: `${hour}:${minute}`,
          value: `${m} ${h}`,
        });
      }
    }
    return options;
  };

  const parseCronTime = (cron: string): string => {
    const parts = cron.split(' ');
    return `${parts[1]} ${parts[0]}`;
  };

  const updateCronTime = (cronKey: 'cron_24hr_report' | 'cron_7day_report' | 'cron_monthly_report', timeValue: string) => {
    if (!settings) return;
    const [minute, hour] = timeValue.split(' ');
    const currentCron = settings[cronKey] || '0 0 * * *';
    const parts = currentCron.split(' ');
    parts[0] = minute;
    parts[1] = hour;
    updateSetting(cronKey, parts.join(' '));
  };

  const updateCronDayOfWeek = (cronKey: 'cron_7day_report', day: string) => {
    if (!settings) return;
    const currentCron = settings[cronKey] || '0 0 * * 1';
    const parts = currentCron.split(' ');
    parts[4] = day;
    updateSetting(cronKey, parts.join(' '));
  };

  const updateCronDayOfMonth = (cronKey: 'cron_monthly_report', day: string) => {
    if (!settings) return;
    const currentCron = settings[cronKey] || '0 0 1 * *';
    const parts = currentCron.split(' ');
    parts[2] = day;
    updateSetting(cronKey, parts.join(' '));
  };

  if (loading) {
    return (
      <div className="p-6">
        <p>Loading...</p>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="p-6">
        <p>Failed to load settings.</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-foreground mb-2">Settings</h1>
        <p className="text-muted-foreground">Manage system configuration, security, and automation settings.</p>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 mb-6 bg-card/50 p-1 rounded-xl backdrop-blur-sm">
        <button
          onClick={() => setActiveTab('ai')}
          className={`flex-1 px-4 py-2 rounded-md transition-colors ${
            activeTab === 'ai'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
        >
          <SettingsIcon className="inline-block w-4 h-4 mr-2 text-blue-500" />
          AI & System
        </button>
        <button
          onClick={() => setActiveTab('password')}
          className={`flex-1 px-4 py-2 rounded-md transition-colors ${
            activeTab === 'password'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
        >
          <Lock className="inline-block w-4 h-4 mr-2 text-green-500" />
          Security
        </button>
        <button
          onClick={() => setActiveTab('automations')}
          className={`flex-1 px-4 py-2 rounded-md transition-colors ${
            activeTab === 'automations'
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
        >
          <Cog className="inline-block w-4 h-4 mr-2 text-purple-500" />
          Automations
        </button>
      </div>

      {/* AI & System Settings Tab */}
      {activeTab === 'ai' && (
        <div className="space-y-6">
          {/* Orchestration */}
          <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
            <h2 className="text-xl font-semibold text-foreground mb-4">AI Orchestration</h2>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm text-muted-foreground mb-2">Primary Provider</label>
                <select
                  value={settings.primary_provider}
                  onChange={(e) => updateSetting('primary_provider', e.target.value)}
                  className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
                >
                  <option value="ollama">Ollama</option>
                  <option value="google">Google</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-2">Fallback Provider</label>
                <select
                  value={settings.fallback_provider}
                  onChange={(e) => updateSetting('fallback_provider', e.target.value)}
                  className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
                >
                  <option value="ollama">Ollama</option>
                  <option value="google">Google</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-2">Active Model</label>
                <input
                  type="text"
                  value={settings.active_model}
                  onChange={(e) => updateSetting('active_model', e.target.value)}
                  className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
                  placeholder="e.g., llama2"
                />
              </div>
            </div>
          </div>

          {/* System Prompt */}
          <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
            <h2 className="text-xl font-semibold text-foreground mb-4">System Prompt</h2>
            <textarea
              value={settings.system_prompt}
              onChange={(e) => updateSetting('system_prompt', e.target.value)}
              className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
              rows={4}
              placeholder="Enter system prompt for AI agent..."
            />
          </div>

          {/* Notification Settings */}
          <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
            <h2 className="text-xl font-semibold text-foreground mb-4">Alert Notifications</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-foreground">Enable Alert Sounds</p>
                  <p className="text-sm text-muted-foreground">Play audio notification when alerts trigger</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.alert_sound_enabled}
                    onChange={(e) => updateSetting('alert_sound_enabled', e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-foreground">Enable Push Notifications</p>
                  <p className="text-sm text-muted-foreground">
                    Receive browser notifications (Status: {pushNotificationStatus})
                  </p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.push_notifications_enabled}
                    onChange={(e) => handlePushNotificationToggle(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Maintenance Mode */}
          <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
            <h2 className="text-xl font-semibold text-foreground mb-4">Maintenance Mode</h2>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-foreground">Enable Maintenance Mode</p>
                <p className="text-sm text-muted-foreground">
                  {settings.maintenance_mode_until
                    ? `Active until: ${new Date(settings.maintenance_mode_until).toLocaleString()}`
                    : 'System will be accessible to admins only'}
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={!!settings.maintenance_mode_until}
                  onChange={(e) => handleMaintenanceModeToggle(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>

          {/* Provider Configurations */}
          <div className="grid grid-cols-2 gap-4">
            {/* Ollama */}
            <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
              <h3 className="text-lg font-semibold text-foreground mb-4">Ollama</h3>
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.providers.ollama.enabled}
                    onChange={(e) => updateProvider('ollama', 'enabled', e.target.checked)}
                    className="mr-2"
                  />
                  <label className="text-sm text-muted-foreground">Enabled</label>
                </div>
                <div>
                  <label className="block text-sm text-muted-foreground mb-1">Base URL</label>
                  <input
                    type="text"
                    value={settings.providers.ollama.url}
                    onChange={(e) => updateProvider('ollama', 'url', e.target.value)}
                    className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md text-sm"
                    placeholder="http://localhost:11434"
                  />
                </div>
                {settings.providers.ollama.models.length > 0 && (
                  <div>
                    <label className="block text-sm text-muted-foreground mb-1">Active Model</label>
                    <select
                      value={settings.providers.ollama.active_model || ''}
                      onChange={(e) => updateProvider('ollama', 'active_model', e.target.value)}
                      className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md text-sm"
                    >
                      <option value="">Select model</option>
                      {settings.providers.ollama.models.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            </div>

            {/* OpenAI */}
            <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
              <h3 className="text-lg font-semibold text-foreground mb-4">OpenAI</h3>
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.providers.openai.enabled}
                    onChange={(e) => updateProvider('openai', 'enabled', e.target.checked)}
                    className="mr-2"
                  />
                  <label className="text-sm text-muted-foreground">Enabled</label>
                </div>
                <div>
                  <label className="block text-sm text-muted-foreground mb-1">API Key</label>
                  <input
                    type="password"
                    value={settings.providers.openai.api_key}
                    onChange={(e) => updateProvider('openai', 'api_key', e.target.value)}
                    className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md text-sm"
                    placeholder="sk-..."
                  />
                </div>
              </div>
            </div>

            {/* Google */}
            <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
              <h3 className="text-lg font-semibold text-foreground mb-4">Google AI</h3>
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.providers.google.enabled}
                    onChange={(e) => updateProvider('google', 'enabled', e.target.checked)}
                    className="mr-2"
                  />
                  <label className="text-sm text-muted-foreground">Enabled</label>
                </div>
                <div>
                  <label className="block text-sm text-muted-foreground mb-1">API Key</label>
                  <input
                    type="password"
                    value={settings.providers.google.api_key}
                    onChange={(e) => updateProvider('google', 'api_key', e.target.value)}
                    className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md text-sm"
                    placeholder="AI..."
                  />
                </div>
              </div>
            </div>

            {/* Anthropic */}
            <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
              <h3 className="text-lg font-semibold text-foreground mb-4">Anthropic</h3>
              <div className="space-y-4">
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    checked={settings.providers.anthropic.enabled}
                    onChange={(e) => updateProvider('anthropic', 'enabled', e.target.checked)}
                    className="mr-2"
                  />
                  <label className="text-sm text-muted-foreground">Enabled</label>
                </div>
                <div>
                  <label className="block text-sm text-muted-foreground mb-1">API Key</label>
                  <input
                    type="password"
                    value={settings.providers.anthropic.api_key}
                    onChange={(e) => updateProvider('anthropic', 'api_key', e.target.value)}
                    className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md text-sm"
                    placeholder="sk-ant-..."
                  />
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleSave}
            className="w-full px-4 py-2 bg-primary text-primary-foreground shadow-sm rounded-md hover:bg-blue-700"
          >
            <Save className="inline-block w-4 h-4 mr-2" />
            Save AI Settings
          </button>
        </div>
      )}

      {/* Security Tab */}
      {activeTab === 'password' && (
        <div className="space-y-6">
          <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
            <h2 className="text-xl font-semibold text-foreground mb-4">Change Password</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-muted-foreground mb-2">Current Password</label>
                <div className="relative">
                  <input
                    type={showCurrentPassword ? 'text' : 'password'}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                    className="absolute right-2 top-2 text-muted-foreground hover:text-foreground"
                  >
                    {showCurrentPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-2">New Password</label>
                <div className="relative">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    className="absolute right-2 top-2 text-muted-foreground hover:text-foreground"
                  >
                    {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {newPassword && (
                  <div className="mt-2">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-gray-700 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${passwordStrength.color} transition-all`}
                          style={{ width: `${(passwordStrength.strength / 3) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm text-muted-foreground">{passwordStrength.label}</span>
                    </div>
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-2">Confirm New Password</label>
                <div className="relative">
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-2 top-2 text-muted-foreground hover:text-foreground"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>
              <button
                onClick={handlePasswordChange}
                className="w-full px-4 py-2 bg-primary text-primary-foreground shadow-sm rounded-md hover:bg-blue-700"
              >
                <Key className="inline-block w-4 h-4 mr-2" />
                Change Password
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Automations Tab */}
      {activeTab === 'automations' && (
        <div className="space-y-6">
          <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
            <h2 className="text-xl font-semibold text-foreground mb-4">Report Automation</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-muted-foreground mb-2">24-Hour Report</label>
                <select
                  value={parseCronTime(settings.cron_24hr_report || '0 2 * * *')}
                  onChange={(e) => updateCronTime('cron_24hr_report', e.target.value)}
                  className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
                >
                  {generateTimeOptions().map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">Daily report generation time</p>
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-2">7-Day Report</label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <select
                      value={parseCronTime(settings.cron_7day_report || '0 3 * * 1')}
                      onChange={(e) => updateCronTime('cron_7day_report', e.target.value)}
                      className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
                    >
                      {generateTimeOptions().map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <select
                      value={settings.cron_7day_report?.split(' ')[4] || '1'}
                      onChange={(e) => updateCronDayOfWeek('cron_7day_report', e.target.value)}
                      className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
                    >
                      <option value="1">Monday</option>
                      <option value="2">Tuesday</option>
                      <option value="3">Wednesday</option>
                      <option value="4">Thursday</option>
                      <option value="5">Friday</option>
                      <option value="6">Saturday</option>
                      <option value="0">Sunday</option>
                    </select>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">Weekly report generation schedule</p>
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-2">Monthly Report</label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <select
                      value={parseCronTime(settings.cron_monthly_report || '0 4 1 * *')}
                      onChange={(e) => updateCronTime('cron_monthly_report', e.target.value)}
                      className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
                    >
                      {generateTimeOptions().map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <select
                      value={settings.cron_monthly_report?.split(' ')[2] || '1'}
                      onChange={(e) => updateCronDayOfMonth('cron_monthly_report', e.target.value)}
                      className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
                    >
                      {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
                        <option key={day} value={day}>
                          Day {day}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1">Monthly report generation schedule</p>
              </div>
            </div>
          </div>

          <div className="bg-card border border-border p-6 rounded-xl shadow-sm">
            <h2 className="text-xl font-semibold text-foreground mb-4">Data Polling</h2>
            <div>
              <label className="block text-sm text-muted-foreground mb-2">Polling Interval</label>
              <select
                value={settings.polling_interval || 30}
                onChange={(e) => updateSetting('polling_interval', parseInt(e.target.value))}
                className="w-full px-3 py-2 bg-input text-foreground border border-border rounded-md"
              >
                <option value="15">15 seconds</option>
                <option value="30">30 seconds</option>
                <option value="60">1 minute</option>
                <option value="300">5 minutes</option>
                <option value="600">10 minutes</option>
                <option value="900">15 minutes</option>
                <option value="1800">30 minutes</option>
                <option value="3600">1 hour</option>
              </select>
              <p className="text-xs text-gray-500 mt-1">How often to collect system metrics</p>
            </div>
          </div>

          <button
            onClick={handleSave}
            className="w-full px-4 py-2 bg-primary text-primary-foreground shadow-sm rounded-md hover:bg-blue-700"
          >
            <Save className="inline-block w-4 h-4 mr-2" />
            Save Automation Settings
          </button>
        </div>
      )}
    </div>
  );
};

export default Settings;
