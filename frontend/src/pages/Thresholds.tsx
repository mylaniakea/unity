import React, { useEffect, useState } from 'react';
import api from '@/api/client';
import { useNotification } from '@/contexts/NotificationContext';
import { Plus, Edit2, Trash2, Save, X } from 'lucide-react';

interface ThresholdRule {
  id?: number;
  server_id: number | null;
  name: string;
  metric: string;
  condition: string;
  threshold_value: number;
  severity: string;
  enabled: boolean;
  muted_until: string | null; // New: Time until rule is muted
}

interface ServerProfile {
  id: number;
  name: string;
}

const Thresholds: React.FC = () => {
  const { showNotification } = useNotification();
  const [rules, setRules] = useState<ThresholdRule[]>([]);
  const [servers, setServers] = useState<ServerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingRule, setEditingRule] = useState<ThresholdRule | null>(null);
  const [isCreating, setIsCreating] = useState(false);

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
  }, []);

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

  const handleCreate = () => {
    setEditingRule({
      server_id: null,
      name: '',
      metric: 'cpu_percent',
      condition: 'greater_than',
      threshold_value: 90,
      severity: 'warning',
      enabled: true,
    });
    setIsCreating(true);
  };

  const handleSave = async () => {
    if (!editingRule) return;

    try {
      if (isCreating) {
        await api.post('/thresholds/', editingRule);
        showNotification('Threshold rule created successfully!', 'success');
      } else {
        await api.put(`/thresholds/${editingRule.id}`, editingRule);
        showNotification('Threshold rule updated successfully!', 'success');
      }
      setEditingRule(null);
      setIsCreating(false);
      fetchRules();
    } catch (error) {
      console.error('Failed to save threshold rule', error);
      showNotification('Failed to save threshold rule.', 'error');
    }
  };

  const handleDelete = async (id: number) => {
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
      await api.put(`/thresholds/${rule.id}`, { enabled: !rule.enabled });
      fetchRules();
    } catch (error) {
      console.error('Failed to toggle threshold rule', error);
      showNotification('Failed to toggle threshold rule.', 'error');
    }
  };

  const handleMuteRule = async (ruleId: number, duration: number) => {
    try {
      await api.post(`/thresholds/${ruleId}/mute?mute_duration_minutes=${duration}`);
      showNotification(`Rule muted for ${duration} minutes.`, 'success');
      fetchRules();
    } catch (error) {
      console.error('Failed to mute rule', error);
      showNotification('Failed to mute rule.', 'error');
    }
  };

  if (loading) return <div className="p-10 text-center">Loading Thresholds...</div>;

  return (
    <div className="space-y-8 p-6 bg-background text-foreground min-h-screen">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Threshold Rules</h1>
          <p className="text-muted-foreground">Define monitoring thresholds for your servers.</p>
        </div>
        <button
          onClick={handleCreate}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
        >
          <Plus size={18} />
          Create Rule
        </button>
      </div>

      {/* Create/Edit Form */}
      {editingRule && (
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="text-xl font-semibold mb-4">{isCreating ? 'Create New Rule' : 'Edit Rule'}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Rule Name</label>
              <input
                type="text"
                className="w-full bg-input border border-border rounded-md px-3 py-2"
                value={editingRule.name}
                onChange={(e) => setEditingRule({ ...editingRule, name: e.target.value })}
                placeholder="High CPU Alert"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Server</label>
              <select
                className="w-full bg-input border border-border rounded-md px-3 py-2"
                value={editingRule.server_id || ''}
                onChange={(e) => setEditingRule({ ...editingRule, server_id: e.target.value ? parseInt(e.target.value) : null })}
              >
                <option value="">All Servers</option>
                {servers.map(server => (
                  <option key={server.id} value={server.id}>{server.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Metric</label>
              <select
                className="w-full bg-input border border-border rounded-md px-3 py-2"
                value={editingRule.metric}
                onChange={(e) => setEditingRule({ ...editingRule, metric: e.target.value })}
              >
                {metricOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Condition</label>
              <select
                className="w-full bg-input border border-border rounded-md px-3 py-2"
                value={editingRule.condition}
                onChange={(e) => setEditingRule({ ...editingRule, condition: e.target.value })}
              >
                {conditionOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Threshold Value</label>
              <input
                type="number"
                className="w-full bg-input border border-border rounded-md px-3 py-2"
                value={editingRule.threshold_value}
                onChange={(e) => setEditingRule({ ...editingRule, threshold_value: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Severity</label>
              <select
                className="w-full bg-input border border-border rounded-md px-3 py-2"
                value={editingRule.severity}
                onChange={(e) => setEditingRule({ ...editingRule, severity: e.target.value })}
              >
                {severityOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={handleSave}
              className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90"
            >
              <Save size={18} />
              Save
            </button>
            <button
              onClick={() => { setEditingRule(null); setIsCreating(false); }}
              className="flex items-center gap-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-md hover:bg-secondary/80"
            >
              <X size={18} />
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Rules List */}
      <div className="space-y-4">
        {rules.length === 0 ? (
          <div className="bg-card border border-border rounded-xl p-8 text-center text-muted-foreground">
            No threshold rules defined yet. Create your first rule to start monitoring.
          </div>
        ) : (
          rules.map(rule => (
            <div key={rule.id} className="bg-card border border-border rounded-xl p-6 flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-lg font-semibold">{rule.name}</h3>
                  <span className={`text-sm font-medium ${severityOptions.find(s => s.value === rule.severity)?.color}`}>
                    {rule.severity.toUpperCase()}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded ${rule.enabled ? 'bg-green-500/20 text-green-500' : 'bg-gray-500/20 text-gray-500'}`}>
                    {rule.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                  {rule.muted_until && new Date(rule.muted_until) > new Date() && (
                    <span className="text-xs px-2 py-1 rounded bg-orange-500/20 text-orange-500">
                      Muted until: {new Date(rule.muted_until).toLocaleString()}
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  {metricOptions.find(m => m.value === rule.metric)?.label} {conditionOptions.find(c => c.value === rule.condition)?.label.toLowerCase()} {rule.threshold_value}
                  {rule.server_id ? ` on ${servers.find(s => s.id === rule.server_id)?.name || 'Unknown Server'}` : ' on all servers'}
                </p>
              </div>
              <div className="flex gap-2">
                {rule.muted_until && new Date(rule.muted_until) > new Date() ? (
                  <button
                    onClick={() => handleMuteRule(rule.id!, 0)} // Pass 0 to unmute immediately
                    className="px-3 py-1 rounded-md bg-orange-600 text-white hover:bg-orange-700 text-sm"
                  >
                    Unmute
                  </button>
                ) : (
                  <div className="relative">
                    <button
                      onClick={() => { /* Toggle mute dropdown */ }}
                      className="px-3 py-1 rounded-md bg-yellow-500 text-white hover:bg-yellow-600 text-sm"
                    >
                      Mute
                    </button>
                    {/* Mute Dropdown Placeholder */}
                    {/* This will be replaced with a proper dropdown component */}
                    <div className="absolute right-0 mt-2 w-40 bg-card border border-border rounded-md shadow-lg hidden">
                      <button className="block w-full text-left px-4 py-2 text-sm hover:bg-muted" onClick={() => handleMuteRule(rule.id!, 30)}>30 Minutes</button>
                      <button className="block w-full text-left px-4 py-2 text-sm hover:bg-muted" onClick={() => handleMuteRule(rule.id!, 60)}>1 Hour</button>
                      <button className="block w-full text-left px-4 py-2 text-sm hover:bg-muted" onClick={() => handleMuteRule(rule.id!, 1440)}>24 Hours</button>
                    </div>
                  </div>
                )}
                <button
                  onClick={() => handleToggleEnabled(rule)}
                  className="px-3 py-1 rounded-md bg-secondary text-secondary-foreground hover:bg-secondary/80 text-sm"
                >
                  {rule.enabled ? 'Disable' : 'Enable'}
                </button>
                <button
                  onClick={() => { setEditingRule(rule); setIsCreating(false); }}
                  className="p-2 rounded-md hover:bg-muted"
                >
                  <Edit2 size={18} />
                </button>
                <button
                  onClick={() => handleDelete(rule.id!)}
                  className="p-2 rounded-md hover:bg-destructive/20 text-destructive"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default Thresholds;
