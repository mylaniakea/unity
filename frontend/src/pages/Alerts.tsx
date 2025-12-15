import React, { useEffect, useState } from 'react';
import api from '@/api/client';
import { useNotification } from '@/contexts/NotificationContext';
import { useConfirm } from '@/contexts/ConfirmDialogContext'; // Import useConfirm
import { Bell, CheckCircle, XCircle, AlertTriangle, Settings, Mail, MessageCircle, Smartphone, Hash, Server, Link } from 'lucide-react';

interface Alert {
  id: number;
  rule_id: number;
  server_id: number;
  severity: string;
  message: string;
  metric_value: number;
  triggered_at: string;
  acknowledged: boolean;
  acknowledged_at: string | null;
  resolved: boolean;
  resolved_at: string | null;
  snoozed_until: string | null; // New: Time until alert is snoozed
}

interface AlertChannel {
  id?: number;
  name: string;
  channel_type: string;
  enabled: boolean;
  config: Record<string, any>;
  template: string | null; // New: Customizable message template
}

interface ChannelDefinition {
  name: string;
  description: string;
  icon: string;
  category: string;
  config_schema: Record<string, any>;
  setup_instructions?: string;
}

const iconMap: Record<string, any> = {
  Mail,
  MessageCircle,
  Bell,
  MessageSquare: MessageCircle,
  Hash,
  Smartphone,
  Server,
  Link,
};

const Alerts: React.FC = () => {
  const { showNotification } = useNotification();
  const { showConfirm } = useConfirm(); // Use the confirm dialog hook
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [channels, setChannels] = useState<AlertChannel[]>([]);
  const [availableChannels, setAvailableChannels] = useState<Record<string, ChannelDefinition>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'alerts' | 'channels'>('alerts');
  const [editingChannel, setEditingChannel] = useState<AlertChannel | null>(null);
  const [isConfiguring, setIsConfiguring] = useState(false);
  const [alertSoundEnabled, setAlertSoundEnabled] = useState(false);
  const [previousAlertIds, setPreviousAlertIds] = useState<Set<number>>(new Set());
  const [showSnoozeDropdownForAlert, setShowSnoozeDropdownForAlert] = useState<number | null>(null); // New state for snooze dropdown

  const criticalSound = typeof Audio !== 'undefined' ? new Audio('https://raw.githubusercontent.com/schmic/sample-data/main/alarm.mp3') : null;

  useEffect(() => {
    fetchSettings();
    fetchAlerts();
    fetchChannels();
    fetchAvailableChannels();

    const interval = setInterval(fetchAlerts, 10000); // Poll for new alerts every 10 seconds

    const handleDocumentClick = () => {
      setShowSnoozeDropdownForAlert(null);
    };
    document.addEventListener('click', handleDocumentClick);

    return () => {
      clearInterval(interval);
      document.removeEventListener('click', handleDocumentClick);
    };
  }, []);

  useEffect(() => {
    if (alertSoundEnabled) {
      const newCriticalAlerts = alerts.filter(alert => 
        alert.severity === 'critical' && !previousAlertIds.has(alert.id)
      );

      if (newCriticalAlerts.length > 0) {
        criticalSound?.play().catch(e => console.error("Error playing sound:", e));
      }
    }
    setPreviousAlertIds(new Set(alerts.map(alert => alert.id)));
  }, [alerts, alertSoundEnabled]);

  const fetchSettings = async () => {
    try {
      const res = await api.get('/settings/');
      setAlertSoundEnabled(res.data.alert_sound_enabled);
    } catch (error) {
      console.error('Failed to fetch settings', error);
    }
  };

  const fetchAlerts = async () => {
    try {
      const res = await api.get('/alerts/?limit=100');
      setAlerts(res.data);

      // No need to set previousAlertIds here, it's handled by the useEffect for sound playback
      // setPreviousAlertIds(new Set(res.data.map((alert: Alert) => alert.id)));
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch alerts', error);
      showNotification('Failed to load alerts.', 'error');
      setLoading(false);
    }
  };

  const fetchChannels = async () => {
    try {
      const res = await api.get('/alerts/channels/');
      setChannels(res.data);
    } catch (error) {
      console.error('Failed to fetch channels', error);
    }
  };

  const fetchAvailableChannels = async () => {
    try {
      const res = await api.get('/alerts/channels/available');
      setAvailableChannels(res.data);
    } catch (error) {
      console.error('Failed to fetch available channels', error);
    }
  };

  const handleAcknowledge = async (alertId: number) => {
    try {
      await api.post(`/alerts/${alertId}/acknowledge`);
      showNotification('Alert acknowledged.', 'success');
      fetchAlerts();
    } catch (error) {
      console.error('Failed to acknowledge alert', error);
      showNotification('Failed to acknowledge alert.', 'error');
    }
  };

  const handleResolve = async (alertId: number) => {
    try {
      await api.post(`/alerts/${alertId}/resolve`);
      showNotification('Alert resolved.', 'success');
      fetchAlerts();
    } catch (error) {
      console.error('Failed to resolve alert', error);
      showNotification('Failed to resolve alert.', 'error');
    }
  };

  const handleSnoozeAlert = async (alertId: number, duration: number) => {
    try {
      await api.post(`/alerts/${alertId}/snooze?snooze_duration_minutes=${duration}`);
      showNotification(`Alert snoozed for ${duration} minutes.`, 'success');
      fetchAlerts();
    } catch (error) {
      console.error('Failed to snooze alert', error);
      showNotification('Failed to snooze alert.', 'error');
    }
  };

  const handleAcknowledgeAll = async () => {
    const confirmed = await showConfirm({
      title: "Acknowledge All Alerts",
      message: `Are you sure you want to acknowledge all ${unresolvedAlerts.length} active alerts?`,
    });
    if (confirmed) {
      try {
        await api.post('/alerts/acknowledge-all');
        showNotification('All active alerts acknowledged.', 'success');
        fetchAlerts();
      } catch (error) {
        console.error('Failed to acknowledge all alerts', error);
        showNotification('Failed to acknowledge all alerts.', 'error');
      }
    }
  };

  const handleResolveAll = async () => {
    const confirmed = await showConfirm({
      title: "Resolve All Alerts",
      message: `Are you sure you want to resolve all ${unresolvedAlerts.length} active alerts? This cannot be undone.`,
    });
    if (confirmed) {
      try {
        await api.post('/alerts/resolve-all');
        showNotification('All active alerts resolved.', 'success');
        fetchAlerts();
      } catch (error) {
        console.error('Failed to resolve all alerts', error);
        showNotification('Failed to resolve all alerts.', 'error');
      }
    }
  };

  const handleConfigureChannel = (channelType: string) => {
    const channelDef = availableChannels[channelType];
    const existingChannel = channels.find(c => c.channel_type === channelType);

    if (existingChannel) {
      setEditingChannel(existingChannel);
    } else {
      setEditingChannel({
        name: channelDef.name,
        channel_type: channelType,
        enabled: false,
        config: {},
        template: null, // Initialize template as null
      });
    }
    setIsConfiguring(true);
  };

  const getPreviewMessage = (template: string | null, alert: Alert | null) => {
    if (!template) return "No custom template. Default message will be used.";
    if (!alert) return "No alert data available for preview. Please trigger an alert first.";

    let preview = template;
    preview = preview.replace(/{server_name}/g, alert.server_id ? `Server-${alert.server_id}` : "Unknown Server");
    preview = preview.replace(/{message}/g, alert.message);
    preview = preview.replace(/{severity}/g, alert.severity.toUpperCase());
    preview = preview.replace(/{metric_value}/g, alert.metric_value.toString());
    preview = preview.replace(/{triggered_at}/g, new Date(alert.triggered_at).toLocaleString());
    // Add more replacements as needed based on alert_data structure
    return preview;
  };

  const handleSaveChannel = async () => {
    if (!editingChannel) return;

    try {
      if (editingChannel.id) {
        await api.put(`/alerts/channels/${editingChannel.id}`, {
          enabled: editingChannel.enabled,
          config: editingChannel.config,
          template: editingChannel.template, // Include template here
        });
        showNotification('Channel updated successfully!', 'success');
      } else {
        await api.post('/alerts/channels/', editingChannel);
        showNotification('Channel configured successfully!', 'success');
      }
      setEditingChannel(null);
      setIsConfiguring(false);
      fetchChannels();
    } catch (error) {
      console.error('Failed to save channel', error);
      showNotification('Failed to save channel.', 'error');
    }
  };

  const handleToggleChannel = async (channel: AlertChannel) => {
    try {
      await api.put(`/alerts/channels/${channel.id}`, { enabled: !channel.enabled });
      fetchChannels();
    } catch (error) {
      console.error('Failed to toggle channel', error);
      showNotification('Failed to toggle channel.', 'error');
    }
  };

  const handleTestChannel = async (channelId: number) => {
    try {
      await api.post(`/alerts/channels/${channelId}/test`);
      showNotification('Test alert sent!', 'success');
    } catch (error) {
      console.error('Failed to send test alert', error);
      showNotification('Failed to send test alert.', 'error');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-500 bg-red-500/20';
      case 'warning': return 'text-yellow-500 bg-yellow-500/20';
      case 'info': return 'text-blue-500 bg-blue-500/20';
      default: return 'text-gray-500 bg-gray-500/20';
    }
  };

  const unresolvedAlerts = alerts.filter(a => !a.resolved);
  const criticalCount = unresolvedAlerts.filter(a => a.severity === 'critical').length;
  const warningCount = unresolvedAlerts.filter(a => a.severity === 'warning').length;

  if (loading) return <div className="p-10 text-center">Loading Alerts...</div>;

  return (
    <div className="space-y-8 p-6 bg-background text-foreground min-h-screen">
      {/* Header with Stats */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Alerts & Notifications</h1>
          <p className="text-muted-foreground">Monitor alerts and configure notification channels.</p>
        </div>
        <div className="flex gap-4">
          <div className="bg-card border border-border rounded-lg px-4 py-2">
            <div className="text-sm text-muted-foreground">Critical</div>
            <div className="text-2xl font-bold text-red-500">{criticalCount}</div>
          </div>
          <div className="bg-card border border-border rounded-lg px-4 py-2">
            <div className="text-sm text-muted-foreground">Warning</div>
            <div className="text-2xl font-bold text-yellow-500">{warningCount}</div>
          </div>
          <div className="bg-card border border-border rounded-lg px-4 py-2">
            <div className="text-sm text-muted-foreground">Total</div>
            <div className="text-2xl font-bold">{unresolvedAlerts.length}</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setActiveTab('alerts')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'alerts' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Active Alerts ({unresolvedAlerts.length})
        </button>
        <button
          onClick={() => setActiveTab('channels')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'channels' ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          Notification Channels
        </button>
      </div>

      {/* Bulk Action Buttons */}
      {activeTab === 'alerts' && unresolvedAlerts.length > 0 && (
        <div className="flex justify-end gap-3">
          {!unresolvedAlerts.every(a => a.acknowledged) && (
            <button
              onClick={handleAcknowledgeAll}
              className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 text-sm font-medium"
            >
              Acknowledge All ({unresolvedAlerts.filter(a => !a.acknowledged).length})
            </button>
          )}
          <button
            onClick={handleResolveAll}
            className="px-4 py-2 rounded-md bg-green-600 text-white hover:bg-green-700 text-sm font-medium"
          >
            Resolve All ({unresolvedAlerts.length})
          </button>
        </div>
      )}

      {/* Alerts Tab */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          {unresolvedAlerts.length === 0 ? (
            <div className="bg-card border border-border rounded-xl p-8 text-center text-muted-foreground">
              <CheckCircle size={48} className="mx-auto mb-4 text-green-500" />
              <p className="text-lg font-medium">All Clear!</p>
              <p>No active alerts at the moment.</p>
            </div>
          ) : (
            unresolvedAlerts.map(alert => (
              <div key={alert.id} className={`bg-card border-2 rounded-xl p-6 ${getSeverityColor(alert.severity).replace('text-', 'border-')}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <AlertTriangle className={getSeverityColor(alert.severity).split(' ')[0]} />
                      <span className={`text-sm font-bold px-2 py-1 rounded ${getSeverityColor(alert.severity)}`}>
                        {alert.severity.toUpperCase()}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        {new Date(alert.triggered_at).toLocaleString()}
                      </span>
                    </div>
                    <p className="text-lg font-medium mb-1">{alert.message}</p>
                    <p className="text-sm text-muted-foreground">Value: {alert.metric_value}</p>
                    {alert.snoozed_until && new Date(alert.snoozed_until) > new Date() && (
                      <p className="text-xs text-blue-500 mt-1">Snoozed until: {new Date(alert.snoozed_until).toLocaleString()}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    {alert.snoozed_until && new Date(alert.snoozed_until) > new Date() ? (
                      <button
                        onClick={() => handleSnoozeAlert(alert.id, 0)} // Pass 0 to unsnooze immediately
                        className="px-3 py-1 rounded-md bg-orange-500 text-white hover:bg-orange-600 text-sm"
                      >
                        Unsnooze
                      </button>
                    ) : (
                      <>
                        {!alert.acknowledged && (
                          <button
                            onClick={() => handleAcknowledge(alert.id)}
                            className="px-3 py-1 rounded-md bg-blue-500 text-white hover:bg-blue-600 text-sm"
                          >
                            Acknowledge
                          </button>
                        )}
                        <div className="relative">
                          <button
                            onClick={(e) => { e.stopPropagation(); setShowSnoozeDropdownForAlert(alert.id); }}
                            className="px-3 py-1 rounded-md bg-yellow-500 text-white hover:bg-yellow-600 text-sm"
                          >
                            Snooze
                          </button>
                          {showSnoozeDropdownForAlert === alert.id && (
                            <div className="absolute right-0 mt-2 w-40 bg-card border border-border rounded-md shadow-lg z-10">
                              <button className="block w-full text-left px-4 py-2 text-sm hover:bg-muted" onClick={() => { handleSnoozeAlert(alert.id, 5); setShowSnoozeDropdownForAlert(null); }}>5 Minutes</button>
                              <button className="block w-full text-left px-4 py-2 text-sm hover:bg-muted" onClick={() => { handleSnoozeAlert(alert.id, 30); setShowSnoozeDropdownForAlert(null); }}>30 Minutes</button>
                              <button className="block w-full text-left px-4 py-2 text-sm hover:bg-muted" onClick={() => { handleSnoozeAlert(alert.id, 60); setShowSnoozeDropdownForAlert(null); }}>1 Hour</button>
                              <button className="block w-full text-left px-4 py-2 text-sm hover:bg-muted" onClick={() => { handleSnoozeAlert(alert.id, 1440); setShowSnoozeDropdownForAlert(null); }}>24 Hours</button>
                            </div>
                          )}
                        </div>
                      </>
                    )}
                    <button
                      onClick={() => handleResolve(alert.id)}
                      className="px-3 py-1 rounded-md bg-green-500 text-white hover:bg-green-600 text-sm"
                    >
                      Resolve
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Channels Tab (Plugin-like UI) */}
      {activeTab === 'channels' && (
        <div className="space-y-6">
          {isConfiguring && editingChannel && (
            <div className="bg-card border border-border rounded-xl p-6 mb-6">
              <h3 className="text-xl font-semibold mb-4">Configure {editingChannel.name}</h3>
              {availableChannels[editingChannel.channel_type]?.setup_instructions && (
                <div className="bg-muted rounded-lg p-4 mb-4 text-sm whitespace-pre-line">
                  {availableChannels[editingChannel.channel_type].setup_instructions}
                </div>
              )}
              <div className="space-y-4">
                {Object.entries(availableChannels[editingChannel.channel_type]?.config_schema || {}).map(([key, schema]: [string, any]) => (
                  <div key={key}>
                    <label className="block text-sm font-medium mb-2">{schema.label}</label>
                    {schema.type === 'boolean' ? (
                      <input
                        type="checkbox"
                        checked={editingChannel.config[key] !== undefined ? editingChannel.config[key] : schema.default}
                        onChange={(e) => setEditingChannel({
                          ...editingChannel,
                          config: { ...editingChannel.config, [key]: e.target.checked }
                        })}
                        className="w-4 h-4"
                      />
                    ) : schema.type === 'textarea' ? (
                      <textarea
                        className="w-full bg-input border border-border rounded-md px-3 py-2"
                        value={editingChannel.config[key] || ''}
                        onChange={(e) => setEditingChannel({
                          ...editingChannel,
                          config: { ...editingChannel.config, [key]: e.target.value }
                        })}
                        placeholder={schema.placeholder}
                        rows={4}
                      />
                    ) : (
                      <input
                        type={schema.type === 'password' ? 'password' : schema.type === 'number' ? 'number' : 'text'}
                        className="w-full bg-input border border-border rounded-md px-3 py-2"
                        value={editingChannel.config[key] || schema.default || ''}
                        onChange={(e) => setEditingChannel({
                          ...editingChannel,
                          config: { ...editingChannel.config, [key]: e.target.value }
                        })}
                        placeholder={schema.placeholder}
                      />
                    )}
                  </div>
                ))}

                {/* Template Field */}
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium mb-2">Custom Template (Optional)</label>
                  <textarea
                    className="w-full bg-input border border-border rounded-md px-3 py-2 min-h-[100px] font-mono text-sm"
                    value={editingChannel.template || ''}
                    onChange={(e) => setEditingChannel({
                      ...editingChannel,
                      template: e.target.value
                    })}
                    placeholder="Example: {severity} alert on {server_name}: {message}"
                    rows={4}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Available variables: <code>{`{server_name}, {message}, {severity}, {metric_value}, {triggered_at}`}</code>
                  </p>
                  {editingChannel.template && (
                    <div className="mt-4 p-3 bg-muted rounded-md text-sm">
                      <p className="font-medium mb-2">Preview:</p>
                      <p className="whitespace-pre-line">{getPreviewMessage(editingChannel.template, unresolvedAlerts[0] || null)}</p>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button
                  onClick={handleSaveChannel}
                  className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
                >
                  Save Configuration
                </button>
                <button
                  onClick={() => { setEditingChannel(null); setIsConfiguring(false); }}
                  className="px-4 py-2 rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(availableChannels).map(([type, channelDef]) => {
              const configuredChannel = channels.find(c => c.channel_type === type);
              const IconComponent = iconMap[channelDef.icon] || Bell;

              return (
                <div key={type} className="bg-card border border-border rounded-xl p-6 hover:shadow-lg transition-shadow">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        <IconComponent size={24} className="text-primary" />
                      </div>
                      <div>
                        <h3 className="font-semibold">{channelDef.name}</h3>
                        <span className="text-xs text-muted-foreground">{channelDef.category}</span>
                      </div>
                    </div>
                    {configuredChannel && (
                      <span className={`text-xs px-2 py-1 rounded ${configuredChannel.enabled ? 'bg-green-500/20 text-green-500' : 'bg-gray-500/20 text-gray-500'}`}>
                        {configuredChannel.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mb-4">{channelDef.description}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleConfigureChannel(type)}
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80 text-sm"
                    >
                      <Settings size={16} />
                      {configuredChannel ? 'Configure' : 'Setup'}
                    </button>
                    {configuredChannel && (
                      <>
                        <button
                          onClick={() => handleToggleChannel(configuredChannel)}
                          className={`px-3 py-2 rounded-md text-sm ${
                            configuredChannel.enabled
                              ? 'bg-yellow-500/20 text-yellow-500 hover:bg-yellow-500/30'
                              : 'bg-green-500/20 text-green-500 hover:bg-green-500/30'
                          }`}
                        >
                          {configuredChannel.enabled ? 'Disable' : 'Enable'}
                        </button>
                        {configuredChannel.enabled && (
                          <button
                            onClick={() => handleTestChannel(configuredChannel.id!)}
                            className="px-3 py-2 rounded-md bg-blue-500/20 text-blue-500 hover:bg-blue-500/30 text-sm"
                          >
                            Test
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default Alerts;
