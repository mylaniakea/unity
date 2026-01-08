import React, { useEffect, useState } from 'react';
import api from '@/api/client';
import { useNotification } from '@/contexts/NotificationContext';
import { Plus, Edit2, Trash2, Save, X, AlertTriangle, Bell, CheckCircle, Clock, Volume2, VolumeX } from 'lucide-react';

// Thresholds types
interface ThresholdRule {
  id?: number;
  server_id: number | null;
  name: string;
  metric: string;
  condition: string;
  threshold_value: number;
  severity: string;
  enabled: boolean;
  muted_until: string | null;
}

interface ServerProfile {
  id: number;
  name: string;
}

// Alerts types
interface Alert {
  id: number;
  server_id: number | null;
  server_name: string | null;
  message: string;
  severity: string;
  triggered_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  threshold_rule_id: number | null;
  snoozed_until: string | null;
  metric_value?: number;
}

interface AlertChannel {
  id: number;
  channel_type: string;
  name: string;
  config: Record<string, any>;
  template: string;
  enabled: boolean;
}

interface ChannelDefinition {
  type: string;
  name: string;
  config_schema: Record<string, any>;
  description: string;
}

const AlertsAndThresholds: React.FC = () => {
  const { showNotification } = useNotification();
  const [activeTab, setActiveTab] = useState<'thresholds' | 'alerts' | 'channels'>('thresholds');
  
  // Thresholds state
  const [rules, setRules] = useState<ThresholdRule[]>([]);
  const [servers, setServers] = useState<ServerProfile[]>([]);
  const [editingRule, setEditingRule] = useState<ThresholdRule | null>(null);
  const [isCreatingRule, setIsCreatingRule] = useState(false);
  
  // Alerts state
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [channels, setChannels] = useState<AlertChannel[]>([]);
  const [availableChannels, setAvailableChannels] = useState<ChannelDefinition[]>([]);
  const [editingChannel, setEditingChannel] = useState<AlertChannel | null>(null);
  const [isConfiguringChannel, setIsConfiguringChannel] = useState(false);
  const [showSnoozeDropdownForAlert, setShowSnoozeDropdownForAlert] = useState<number | null>(null);
  const [alertSoundEnabled, setAlertSoundEnabled] = useState(true);
  
  const [loading, setLoading] = useState(true);

  const metricOptions = [
    { value: 'cpu_percent', label: 'CPU Usage (%)' },
    { value: 'memory_percent', label: 'Memory Usage (%)' },
    { value: 'disk_percent', label: 'Disk Usage (%)' },
    { value: 'disk_io_read', label: 'Disk I/O Read (MB/s)' },
    { value: 'disk_io_write', label: 'Disk I/O Write (MB/s)' },
    { value: 'network_sent', label: 'Network Sent (MB/s)' },
    { value: 'network_recv', label: 'Network Received (MB/s)' },
    { value: 'temperature', label: 'Temperature (°C)' },
  ];

  const conditionOptions = [
    { value: 'greater_than', label: 'Greater than' },
    { value: 'less_than', label: 'Less than' },
    { value: 'equal_to', label: 'Equal to' },
  ];

  const severityOptions = [
    { value: 'info', label: 'Info', color: 'text-blue-500' },
    { value: 'warning', label: 'Warning', color: 'text-yellow-500' },
    { value: 'critical', label: 'Critical', color: 'text-red-500' },
  ];

  useEffect(() => {
    fetchRules();
    fetchServers();
    fetchAlerts();
    fetchChannels();
    fetchAvailableChannels();
    fetchSettings();
    const interval = setInterval(() => {
      fetchAlerts();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  // Thresholds functions
  const fetchRules = async () => {
    try {
      const res = await api.get('/thresholds/');
      setRules(res.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch threshold rules', error);
      showNotification('Failed to load threshold rules.', 'error');
      setLoading(false);
    }
  };

  const fetchServers = async () => {
    try {
      const res = await api.get('/profiles/');
      setServers(res.data);
    } catch (error) {
      console.error('Failed to fetch servers', error);
    }
  };

  const handleCreateRule = () => {
    setEditingRule({
      server_id: null,
      name: '',
      metric: 'cpu_percent',
      condition: 'greater_than',
      threshold_value: 90,
      severity: 'warning',
      enabled: true,
      muted_until: null,
    });
    setIsCreatingRule(true);
  };

  const handleSaveRule = async () => {
    if (!editingRule) return;

    try {
      if (isCreatingRule) {
        await api.post('/thresholds/', editingRule);
        showNotification('Threshold rule created successfully!', 'success');
      } else {
        await api.put(`/thresholds/${editingRule.id}`, editingRule);
        showNotification('Threshold rule updated successfully!', 'success');
      }
      fetchRules();
      setEditingRule(null);
      setIsCreatingRule(false);
    } catch (error) {
      console.error('Failed to save threshold rule', error);
      showNotification('Failed to save threshold rule.', 'error');
    }
  };

  const handleDeleteRule = async (id: number) => {
    if (!confirm('Are you sure you want to delete this threshold rule?')) return;

    try {
      await api.delete(`/thresholds/${id}`);
      showNotification('Threshold rule deleted successfully!', 'success');
      fetchRules();
    } catch (error) {
      console.error('Failed to delete threshold rule', error);
      showNotification('Failed to delete threshold rule.', 'error');
    }
  };

  const handleToggleEnabled = async (rule: ThresholdRule) => {
    try {
      await api.put(`/thresholds/${rule.id}`, { ...rule, enabled: !rule.enabled });
      showNotification(`Threshold rule ${!rule.enabled ? 'enabled' : 'disabled'} successfully!`, 'success');
      fetchRules();
    } catch (error) {
      console.error('Failed to toggle threshold rule', error);
      showNotification('Failed to toggle threshold rule.', 'error');
    }
  };

  const handleMuteRule = async (ruleId: number, muteDurationMinutes: number) => {
    try {
      await api.post(`/thresholds/${ruleId}/mute?mute_duration_minutes=${muteDurationMinutes}`);
      showNotification(`Threshold rule muted for ${muteDurationMinutes} minutes.`, 'success');
      fetchRules();
    } catch (error) {
      console.error('Failed to mute threshold rule', error);
      showNotification('Failed to mute threshold rule.', 'error');
    }
  };

  // Alerts functions
  const fetchAlerts = async () => {
    try {
      const res = await api.get('/alerts/?limit=100');
      setAlerts(res.data);
    } catch (error) {
      console.error('Failed to fetch alerts', error);
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

  const fetchSettings = async () => {
    try {
      const res = await api.get('/settings/');
      const soundSetting = res.data.find((s: any) => s.key === 'alert_sound_enabled');
      if (soundSetting) {
        setAlertSoundEnabled(soundSetting.value === 'true');
      }
    } catch (error) {
      console.error('Failed to fetch settings', error);
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

  const handleSnooze = async (alertId: number, snoozeDurationMinutes: number) => {
    try {
      await api.post(`/alerts/${alertId}/snooze?snooze_duration_minutes=${snoozeDurationMinutes}`);
      showNotification(`Alert snoozed for ${snoozeDurationMinutes} minutes.`, 'success');
      fetchAlerts();
      setShowSnoozeDropdownForAlert(null);
    } catch (error) {
      console.error('Failed to snooze alert', error);
      showNotification('Failed to snooze alert.', 'error');
    }
  };

  const handleAcknowledgeAll = async () => {
    try {
      await api.post('/alerts/acknowledge-all');
      showNotification('All alerts acknowledged.', 'success');
      fetchAlerts();
    } catch (error) {
      console.error('Failed to acknowledge all alerts', error);
      showNotification('Failed to acknowledge all alerts.', 'error');
    }
  };

  const handleResolveAll = async () => {
    try {
      await api.post('/alerts/resolve-all');
      showNotification('All alerts resolved.', 'success');
      fetchAlerts();
    } catch (error) {
      console.error('Failed to resolve all alerts', error);
      showNotification('Failed to resolve all alerts.', 'error');
    }
  };

  const handleTestChannel = async (channelId: number) => {
    try {
      await api.post(`/alerts/channels/${channelId}/test`);
      showNotification('Test notification sent!', 'success');
    } catch (error) {
      console.error('Failed to test channel', error);
      showNotification('Failed to send test notification.', 'error');
    }
  };

  const handleSaveChannel = async () => {
    if (!editingChannel) return;

    try {
      if (editingChannel.id) {
        await api.put(`/alerts/channels/${editingChannel.id}`, editingChannel);
        showNotification('Channel updated successfully!', 'success');
      } else {
        await api.post('/alerts/channels/', editingChannel);
        showNotification('Channel created successfully!', 'success');
      }
      fetchChannels();
      setEditingChannel(null);
      setIsConfiguringChannel(false);
    } catch (error) {
      console.error('Failed to save channel', error);
      showNotification('Failed to save channel.', 'error');
    }
  };

  const handleDeleteChannel = async (id: number) => {
    if (!confirm('Are you sure you want to delete this channel?')) return;

    try {
      await api.delete(`/alerts/channels/${id}`);
      showNotification('Channel deleted successfully!', 'success');
      fetchChannels();
    } catch (error) {
      console.error('Failed to delete channel', error);
      showNotification('Failed to delete channel.', 'error');
    }
  };

  const unresolvedAlerts = alerts.filter(a => !a.resolved_at);
  const criticalCount = unresolvedAlerts.filter(a => a.severity === 'critical').length;
  const warningCount = unresolvedAlerts.filter(a => a.severity === 'warning').length;

  const generatePreview = (template: string): string => {
    const sampleAlert = unresolvedAlerts[0] || {
      server_name: 'Server-01',
      message: 'CPU usage exceeded threshold',
      severity: 'warning',
      metric_value: 95.5,
      triggered_at: new Date().toISOString(),
    };
    
    return template
      .replace('{server_name}', sampleAlert.server_name || 'N/A')
      .replace('{message}', sampleAlert.message)
      .replace('{severity}', sampleAlert.severity)
      .replace('{metric_value}', String(sampleAlert.metric_value || 'N/A'))
      .replace('{triggered_at}', new Date(sampleAlert.triggered_at).toLocaleString());
  };

  if (loading) {
    return (
      <div className="p-6">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white mb-2">Alerts & Thresholds</h1>
        <p className="text-gray-400">Configure monitoring thresholds, view alerts, and manage notification channels.</p>
      </div>

      {/* Tabs */}
      <div className="flex space-x-1 mb-6 bg-gray-800 p-1 rounded-lg">
        <button
          onClick={() => setActiveTab('thresholds')}
          className={`flex-1 px-4 py-2 rounded-md transition-colors ${
            activeTab === 'thresholds'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          <AlertTriangle className="inline-block w-4 h-4 mr-2" />
          Threshold Rules ({rules.length})
        </button>
        <button
          onClick={() => setActiveTab('alerts')}
          className={`flex-1 px-4 py-2 rounded-md transition-colors ${
            activeTab === 'alerts'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          <Bell className="inline-block w-4 h-4 mr-2" />
          Active Alerts ({unresolvedAlerts.length})
        </button>
        <button
          onClick={() => setActiveTab('channels')}
          className={`flex-1 px-4 py-2 rounded-md transition-colors ${
            activeTab === 'channels'
              ? 'bg-blue-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          <Volume2 className="inline-block w-4 h-4 mr-2" />
          Notification Channels ({channels.length})
        </button>
      </div>

      {/* Threshold Rules Tab */}
      {activeTab === 'thresholds' && (
        <div>
          <div className="mb-4 flex justify-between items-center">
            <div className="text-sm text-gray-400">
              {rules.filter(r => r.enabled).length} active rules
            </div>
            <button
              onClick={handleCreateRule}
              className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create Rule
            </button>
          </div>

          {/* Create/Edit Form */}
          {(editingRule || isCreatingRule) && (
            <div className="mb-6 bg-gray-800 p-4 rounded-lg border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">
                {isCreatingRule ? 'Create New Rule' : 'Edit Rule'}
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Rule Name</label>
                  <input
                    type="text"
                    value={editingRule?.name || ''}
                    onChange={(e) => setEditingRule({ ...editingRule!, name: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                    placeholder="High CPU Usage Alert"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Server (Optional)</label>
                  <select
                    value={editingRule?.server_id || ''}
                    onChange={(e) => setEditingRule({ ...editingRule!, server_id: e.target.value ? Number(e.target.value) : null })}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                  >
                    <option value="">All Servers</option>
                    {servers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Metric</label>
                  <select
                    value={editingRule?.metric || 'cpu_percent'}
                    onChange={(e) => setEditingRule({ ...editingRule!, metric: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                  >
                    {metricOptions.map((m) => (
                      <option key={m.value} value={m.value}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Condition</label>
                  <select
                    value={editingRule?.condition || 'greater_than'}
                    onChange={(e) => setEditingRule({ ...editingRule!, condition: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                  >
                    {conditionOptions.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Threshold Value</label>
                  <input
                    type="number"
                    value={editingRule?.threshold_value || 0}
                    onChange={(e) => setEditingRule({ ...editingRule!, threshold_value: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Severity</label>
                  <select
                    value={editingRule?.severity || 'warning'}
                    onChange={(e) => setEditingRule({ ...editingRule!, severity: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                  >
                    {severityOptions.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex items-center mt-4">
                <input
                  type="checkbox"
                  checked={editingRule?.enabled || false}
                  onChange={(e) => setEditingRule({ ...editingRule!, enabled: e.target.checked })}
                  className="mr-2"
                />
                <label className="text-sm text-gray-400">Enabled</label>
              </div>
              <div className="flex space-x-2 mt-4">
                <button
                  onClick={handleSaveRule}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                >
                  <Save className="inline-block w-4 h-4 mr-2" />
                  Save
                </button>
                <button
                  onClick={() => {
                    setEditingRule(null);
                    setIsCreatingRule(false);
                  }}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                >
                  <X className="inline-block w-4 h-4 mr-2" />
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Rules List */}
          {rules.length === 0 ? (
            <div className="bg-gray-800 p-8 rounded-lg text-center text-gray-400">
              No threshold rules defined yet. Create your first rule to start monitoring.
            </div>
          ) : (
            <div className="space-y-2">
              {rules.map((rule) => (
                <div key={rule.id} className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="text-lg font-semibold text-white">{rule.name}</h3>
                        <span
                          className={`px-2 py-1 rounded text-xs font-semibold ${
                            severityOptions.find((s) => s.value === rule.severity)?.color
                          }`}
                        >
                          {rule.severity.toUpperCase()}
                        </span>
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            rule.enabled ? 'bg-green-600 text-white' : 'bg-gray-600 text-gray-300'
                          }`}
                        >
                          {rule.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        {rule.muted_until && (
                          <span className="px-2 py-1 rounded text-xs bg-yellow-600 text-white">
                            Muted until {new Date(rule.muted_until).toLocaleString()}
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-400">
                        {metricOptions.find((m) => m.value === rule.metric)?.label}{' '}
                        {conditionOptions.find((c) => c.value === rule.condition)?.label}{' '}
                        {rule.threshold_value}
                        {rule.server_id
                          ? ` (Server: ${servers.find((s) => s.id === rule.server_id)?.name || 'Unknown'})`
                          : ' (All Servers)'}
                      </p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleToggleEnabled(rule)}
                        className="p-2 text-gray-400 hover:text-white transition-colors"
                        title={rule.enabled ? 'Disable' : 'Enable'}
                      >
                        {rule.enabled ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                      </button>
                      {rule.enabled && (
                        <button
                          onClick={() => handleMuteRule(rule.id!, 60)}
                          className="p-2 text-gray-400 hover:text-white transition-colors"
                          title="Mute for 1 hour"
                        >
                          <Clock className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => {
                          setEditingRule(rule);
                          setIsCreatingRule(false);
                        }}
                        className="p-2 text-gray-400 hover:text-white transition-colors"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteRule(rule.id!)}
                        className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Active Alerts Tab */}
      {activeTab === 'alerts' && (
        <div>
          <div className="mb-4 flex justify-between items-center">
            <div className="flex space-x-4 text-sm">
              <span className="text-red-500 font-semibold">Critical: {criticalCount}</span>
              <span className="text-yellow-500 font-semibold">Warning: {warningCount}</span>
              <span className="text-gray-400">Total Unresolved: {unresolvedAlerts.length}</span>
            </div>
            {unresolvedAlerts.length > 0 && (
              <div className="flex space-x-2">
                <button
                  onClick={handleAcknowledgeAll}
                  className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700"
                >
                  Acknowledge All
                </button>
                <button
                  onClick={handleResolveAll}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                >
                  Resolve All
                </button>
              </div>
            )}
          </div>

          {unresolvedAlerts.length === 0 ? (
            <div className="bg-gray-800 p-8 rounded-lg text-center text-gray-400">
              <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
              <p className="text-lg">All clear! No active alerts.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {unresolvedAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`bg-gray-800 p-4 rounded-lg border ${
                    alert.severity === 'critical'
                      ? 'border-red-500'
                      : alert.severity === 'warning'
                      ? 'border-yellow-500'
                      : 'border-blue-500'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <span
                          className={`px-2 py-1 rounded text-xs font-semibold ${
                            alert.severity === 'critical'
                              ? 'bg-red-600 text-white'
                              : alert.severity === 'warning'
                              ? 'bg-yellow-600 text-white'
                              : 'bg-blue-600 text-white'
                          }`}
                        >
                          {alert.severity.toUpperCase()}
                        </span>
                        {alert.server_name && (
                          <span className="text-sm text-gray-400">{alert.server_name}</span>
                        )}
                        {alert.acknowledged_at && (
                          <span className="px-2 py-1 rounded text-xs bg-gray-600 text-white">
                            Acknowledged
                          </span>
                        )}
                        {alert.snoozed_until && (
                          <span className="px-2 py-1 rounded text-xs bg-purple-600 text-white">
                            Snoozed until {new Date(alert.snoozed_until).toLocaleString()}
                          </span>
                        )}
                      </div>
                      <p className="text-white mb-1">{alert.message}</p>
                      <p className="text-sm text-gray-400">
                        Triggered: {new Date(alert.triggered_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="flex space-x-2 relative">
                      {!alert.acknowledged_at && (
                        <button
                          onClick={() => handleAcknowledge(alert.id)}
                          className="px-3 py-1 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 text-sm"
                        >
                          Acknowledge
                        </button>
                      )}
                      {!alert.snoozed_until ? (
                        <div className="relative">
                          <button
                            onClick={() =>
                              setShowSnoozeDropdownForAlert(
                                showSnoozeDropdownForAlert === alert.id ? null : alert.id
                              )
                            }
                            className="px-3 py-1 bg-purple-600 text-white rounded-md hover:bg-purple-700 text-sm"
                          >
                            Snooze
                          </button>
                          {showSnoozeDropdownForAlert === alert.id && (
                            <div className="absolute right-0 mt-1 w-40 bg-gray-700 rounded-md shadow-lg z-10">
                              <button
                                onClick={() => handleSnooze(alert.id, 5)}
                                className="block w-full text-left px-4 py-2 text-sm text-white hover:bg-gray-600"
                              >
                                5 Minutes
                              </button>
                              <button
                                onClick={() => handleSnooze(alert.id, 30)}
                                className="block w-full text-left px-4 py-2 text-sm text-white hover:bg-gray-600"
                              >
                                30 Minutes
                              </button>
                              <button
                                onClick={() => handleSnooze(alert.id, 60)}
                                className="block w-full text-left px-4 py-2 text-sm text-white hover:bg-gray-600"
                              >
                                1 Hour
                              </button>
                              <button
                                onClick={() => handleSnooze(alert.id, 1440)}
                                className="block w-full text-left px-4 py-2 text-sm text-white hover:bg-gray-600"
                              >
                                24 Hours
                              </button>
                            </div>
                          )}
                        </div>
                      ) : (
                        <button
                          onClick={() => handleSnooze(alert.id, 0)}
                          className="px-3 py-1 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
                        >
                          Unsnooze
                        </button>
                      )}
                      <button
                        onClick={() => handleResolve(alert.id)}
                        className="px-3 py-1 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
                      >
                        Resolve
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Notification Channels Tab */}
      {activeTab === 'channels' && (
        <div>
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-white mb-2">Configure Notification Channels</h2>
            <p className="text-sm text-gray-400">
              Set up how you want to be notified when alerts are triggered.
            </p>
          </div>

          {/* Channel Configuration Form */}
          {(editingChannel || isConfiguringChannel) && (
            <div className="mb-6 bg-gray-800 p-4 rounded-lg border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">
                {editingChannel?.id ? 'Edit Channel' : 'Create Channel'}
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Channel Type</label>
                  <select
                    value={editingChannel?.channel_type || ''}
                    onChange={(e) => {
                      const channelDef = availableChannels.find((c) => c.type === e.target.value);
                      setEditingChannel({
                        ...editingChannel!,
                        channel_type: e.target.value,
                        name: channelDef?.name || '',
                        config: {},
                        template: channelDef ? '{server_name} - {message} (Severity: {severity})' : '',
                      });
                    }}
                    className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                    disabled={!!editingChannel?.id}
                  >
                    <option value="">Select a channel type</option>
                    {availableChannels.map((ch) => (
                      <option key={ch.type} value={ch.type}>
                        {ch.name}
                      </option>
                    ))}
                  </select>
                </div>
                {editingChannel?.channel_type && (
                  <>
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">Channel Name</label>
                      <input
                        type="text"
                        value={editingChannel?.name || ''}
                        onChange={(e) => setEditingChannel({ ...editingChannel!, name: e.target.value })}
                        className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                      />
                    </div>
                    {availableChannels
                      .find((c) => c.type === editingChannel.channel_type)
                      ?.config_schema &&
                      Object.entries(
                        availableChannels.find((c) => c.type === editingChannel.channel_type)!
                          .config_schema
                      ).map(([key, schema]: [string, any]) => (
                        <div key={key}>
                          <label className="block text-sm text-gray-400 mb-1">
                            {schema.title || key}
                          </label>
                          {schema.type === 'string' && schema.enum ? (
                            <select
                              value={editingChannel.config[key] || ''}
                              onChange={(e) =>
                                setEditingChannel({
                                  ...editingChannel!,
                                  config: { ...editingChannel.config, [key]: e.target.value },
                                })
                              }
                              className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                            >
                              {schema.enum.map((opt: string) => (
                                <option key={opt} value={opt}>
                                  {opt}
                                </option>
                              ))}
                            </select>
                          ) : schema.type === 'string' ? (
                            <input
                              type="text"
                              value={editingChannel.config[key] || ''}
                              onChange={(e) =>
                                setEditingChannel({
                                  ...editingChannel!,
                                  config: { ...editingChannel.config, [key]: e.target.value },
                                })
                              }
                              className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                              placeholder={schema.description}
                            />
                          ) : schema.type === 'boolean' ? (
                            <input
                              type="checkbox"
                              checked={editingChannel.config[key] || false}
                              onChange={(e) =>
                                setEditingChannel({
                                  ...editingChannel!,
                                  config: { ...editingChannel.config, [key]: e.target.checked },
                                })
                              }
                              className="mr-2"
                            />
                          ) : null}
                          {schema.description && (
                            <p className="text-xs text-gray-500 mt-1">{schema.description}</p>
                          )}
                        </div>
                      ))}
                    <div>
                      <label className="block text-sm text-gray-400 mb-1">
                        Message Template
                      </label>
                      <textarea
                        value={editingChannel?.template || ''}
                        onChange={(e) =>
                          setEditingChannel({ ...editingChannel!, template: e.target.value })
                        }
                        className="w-full px-3 py-2 bg-gray-700 text-white rounded-md"
                        rows={3}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Available variables: {'{server_name}'}, {'{message}'}, {'{severity}'},{' '}
                        {'{metric_value}'}, {'{triggered_at}'}
                      </p>
                      {editingChannel?.template && (
                        <div className="mt-2 p-2 bg-gray-900 rounded text-sm text-gray-300">
                          <strong>Preview:</strong> {generatePreview(editingChannel.template)}
                        </div>
                      )}
                    </div>
                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        checked={editingChannel?.enabled || false}
                        onChange={(e) =>
                          setEditingChannel({ ...editingChannel!, enabled: e.target.checked })
                        }
                        className="mr-2"
                      />
                      <label className="text-sm text-gray-400">Enabled</label>
                    </div>
                  </>
                )}
              </div>
              <div className="flex space-x-2 mt-4">
                <button
                  onClick={handleSaveChannel}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
                  disabled={!editingChannel?.channel_type}
                >
                  <Save className="inline-block w-4 h-4 mr-2" />
                  Save
                </button>
                <button
                  onClick={() => {
                    setEditingChannel(null);
                    setIsConfiguringChannel(false);
                  }}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
                >
                  <X className="inline-block w-4 h-4 mr-2" />
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Available Channels to Configure */}
          {!editingChannel && !isConfiguringChannel && (
            <div className="grid grid-cols-2 gap-4 mb-6">
              {availableChannels.map((channelDef) => {
                const configured = channels.find((c) => c.channel_type === channelDef.type);
                return (
                  <div
                    key={channelDef.type}
                    className="bg-gray-800 p-4 rounded-lg border border-gray-700"
                  >
                    <h3 className="text-lg font-semibold text-white mb-2">{channelDef.name}</h3>
                    <p className="text-sm text-gray-400 mb-4">{channelDef.description}</p>
                    {configured ? (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setEditingChannel(configured)}
                          className="flex-1 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
                        >
                          <Edit2 className="inline-block w-4 h-4 mr-1" />
                          Edit
                        </button>
                        <button
                          onClick={() => handleTestChannel(configured.id)}
                          className="flex-1 px-3 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm"
                          disabled={!configured.enabled}
                        >
                          Test
                        </button>
                        <button
                          onClick={() => handleDeleteChannel(configured.id)}
                          className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm"
                        >
                          <Trash2 className="inline-block w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => {
                          setEditingChannel({
                            id: 0,
                            channel_type: channelDef.type,
                            name: channelDef.name,
                            config: {},
                            template: '{server_name} - {message} (Severity: {severity})',
                            enabled: true,
                          });
                          setIsConfiguringChannel(true);
                        }}
                        className="w-full px-3 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm"
                      >
                        <Plus className="inline-block w-4 h-4 mr-1" />
                        Configure
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AlertsAndThresholds;
