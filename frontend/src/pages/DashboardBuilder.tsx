import React from 'react';
import { useState, useEffect } from 'react';
import { Save, Plus, Trash2, GripVertical, X } from 'lucide-react';
import dashboardBuilderApi from '../api/dashboardBuilder';

interface Widget {
  id: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  config: any;
  title: string;
}

interface Dashboard {
  id: number;
  name: string;
  description: string | null;
  layout: any;
  widgets: Widget[];
  refresh_interval: number;
}

export default function DashboardBuilder() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [showWidgetMenu, setShowWidgetMenu] = useState(false);
  const [widgetTemplates, setWidgetTemplates] = useState<any[]>([]);

  useEffect(() => {
    fetchDashboards();
    fetchWidgetTemplates();
  }, []);

  const fetchDashboards = async () => {
    try {
      const response = await dashboardBuilderApi.listDashboards();
      setDashboards(response.data);
      if (response.data.length > 0 && !dashboard) {
        setDashboard(response.data[0]);
      }
    } catch (err) {
      console.error('Failed to fetch dashboards:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchWidgetTemplates = async () => {
    try {
      const response = await dashboardBuilderApi.getWidgetTemplates();
      setWidgetTemplates(response.data.templates || []);
    } catch (err) {
      console.error('Failed to fetch widget templates:', err);
    }
  };

  const handleCreateDashboard = async () => {
    try {
      const response = await dashboardBuilderApi.createDashboard({
        name: 'New Dashboard',
        description: '',
        is_shared: false,
        refresh_interval: 30,
      });
      setDashboard(response.data);
      await fetchDashboards();
      setEditing(true);
    } catch (err) {
      console.error('Failed to create dashboard:', err);
      alert('Failed to create dashboard');
    }
  };

  const handleAddWidget = async (template: any) => {
    if (!dashboard) return;

    // Find next available position
    const maxY = dashboard.widgets.length > 0
      ? Math.max(...dashboard.widgets.map(w => w.y + w.h))
      : 0;

    try {
      await dashboardBuilderApi.addWidget(dashboard.id, {
        widget_type: template.type,
        x: 0,
        y: maxY,
        w: template.default_size.w,
        h: template.default_size.h,
        config: {},
        title: template.name,
      });
      await fetchDashboards();
      if (dashboard) {
        const updated = dashboards.find(d => d.id === dashboard.id);
        if (updated) setDashboard(updated);
      }
      setShowWidgetMenu(false);
    } catch (err) {
      console.error('Failed to add widget:', err);
      alert('Failed to add widget');
    }
  };

  const handleDeleteWidget = async (widgetId: string) => {
    if (!dashboard) return;

    const widget = dashboard.widgets.find(w => w.id === widgetId);
    if (!widget) return;

    // Find widget in database by matching config
    // For now, we'll need to update the API to support this
    // This is a simplified version
    try {
      const updatedWidgets = dashboard.widgets.filter(w => w.id !== widgetId);
      await dashboardBuilderApi.updateDashboard(dashboard.id, {
        widgets: updatedWidgets,
      });
      await fetchDashboards();
      const updated = dashboards.find(d => d.id === dashboard.id);
      if (updated) setDashboard(updated);
    } catch (err) {
      console.error('Failed to delete widget:', err);
    }
  };

  const handleSave = async () => {
    if (!dashboard) return;

    try {
      await dashboardBuilderApi.updateDashboard(dashboard.id, {
        name: dashboard.name,
        widgets: dashboard.widgets,
      });
      setEditing(false);
      alert('Dashboard saved!');
    } catch (err) {
      console.error('Failed to save dashboard:', err);
      alert('Failed to save dashboard');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
        <div className="h-96 bg-gray-200 dark:bg-gray-700 rounded"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Dashboard Builder
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Create and customize your monitoring dashboards
          </p>
        </div>
        <div className="flex gap-2">
          {editing && dashboard && (
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              Save
            </button>
          )}
          <button
            onClick={() => setEditing(!editing)}
            className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg"
          >
            {editing ? 'View Mode' : 'Edit Mode'}
          </button>
          <button
            onClick={handleCreateDashboard}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            New Dashboard
          </button>
        </div>
      </div>

      {/* Dashboard Selector */}
      {dashboards.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
          <select
            value={dashboard?.id || ''}
            onChange={(e) => {
              const selected = dashboards.find(d => d.id === parseInt(e.target.value));
              if (selected) setDashboard(selected);
            }}
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            {dashboards.map(d => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Widget Menu */}
      {editing && showWidgetMenu && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border-2 border-blue-500">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Add Widget
            </h3>
            <button
              onClick={() => setShowWidgetMenu(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {widgetTemplates.map(template => (
              <button
                key={template.type}
                onClick={() => handleAddWidget(template)}
                className="p-4 border border-gray-300 dark:border-gray-600 rounded-lg hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 text-left"
              >
                <h4 className="font-semibold text-gray-900 dark:text-white">
                  {template.name}
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {template.description}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Dashboard Canvas */}
      {dashboard ? (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <div className="mb-4 flex justify-between items-center">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
              {dashboard.name}
            </h2>
            {editing && (
              <button
                onClick={() => setShowWidgetMenu(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Widget
              </button>
            )}
          </div>

          {/* Simple Grid Layout (can be enhanced with react-grid-layout) */}
          <div className="grid grid-cols-12 gap-4">
            {dashboard.widgets.map(widget => (
              <div
                key={widget.id}
                className={`col-span-${widget.w} bg-gray-50 dark:bg-gray-700 rounded-lg p-4 border-2 ${
                  editing ? 'border-dashed border-gray-300 dark:border-gray-600' : 'border-transparent'
                }`}
                style={{ gridRow: `span ${widget.h}` }}
              >
                <div className="flex justify-between items-center mb-2">
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    {widget.title}
                  </h3>
                  {editing && (
                    <div className="flex gap-2">
                      <GripVertical className="w-4 h-4 text-gray-400 cursor-move" />
                      <button
                        onClick={() => handleDeleteWidget(widget.id)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  )}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Widget: {widget.type}
                </div>
                {/* Widget content would be rendered here based on type */}
              </div>
            ))}
          </div>

          {dashboard.widgets.length === 0 && (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              {editing ? (
                <div>
                  <p>No widgets yet. Click "Add Widget" to get started!</p>
                </div>
              ) : (
                <p>This dashboard is empty.</p>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            No dashboards yet. Create your first dashboard!
          </p>
          <button
            onClick={handleCreateDashboard}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
          >
            Create Dashboard
          </button>
        </div>
      )}
    </div>
  );
}

