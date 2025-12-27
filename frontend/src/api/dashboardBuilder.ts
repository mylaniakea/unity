import api from './client';

export interface Dashboard {
  id: number;
  name: string;
  description: string | null;
  user_id: string | null;
  layout: any;
  widgets: any[];
  is_default: boolean;
  is_shared: boolean;
  refresh_interval: number;
  created_at: string;
  updated_at: string | null;
}

export interface WidgetTemplate {
  type: string;
  name: string;
  description: string;
  default_size: { w: number; h: number };
  config_schema: any;
}

export const dashboardBuilderApi = {
  /**
   * Create a new dashboard
   */
  async createDashboard(data: {
    name: string;
    description?: string;
    is_shared?: boolean;
    refresh_interval?: number;
  }): Promise<{ data: Dashboard }> {
    return api.post('/api/v1/dashboards', data);
  },

  /**
   * List dashboards
   */
  async listDashboards(params?: {
    user_id?: string;
    include_shared?: boolean;
  }): Promise<{ data: Dashboard[] }> {
    return api.get('/api/v1/dashboards', { params });
  },

  /**
   * Get dashboard
   */
  async getDashboard(dashboardId: number): Promise<{ data: Dashboard }> {
    return api.get(`/api/v1/dashboards/${dashboardId}`);
  },

  /**
   * Update dashboard
   */
  async updateDashboard(
    dashboardId: number,
    data: {
      name?: string;
      description?: string;
      layout?: any;
      widgets?: any[];
      refresh_interval?: number;
    }
  ): Promise<{ data: Dashboard }> {
    return api.put(`/api/v1/dashboards/${dashboardId}`, data);
  },

  /**
   * Delete dashboard
   */
  async deleteDashboard(dashboardId: number): Promise<{ data: { success: boolean; message: string } }> {
    return api.delete(`/api/v1/dashboards/${dashboardId}`);
  },

  /**
   * Add widget to dashboard
   */
  async addWidget(
    dashboardId: number,
    data: {
      widget_type: string;
      x: number;
      y: number;
      w: number;
      h: number;
      config?: any;
      title?: string;
    }
  ): Promise<{ data: any }> {
    return api.post(`/api/v1/dashboards/${dashboardId}/widgets`, data);
  },

  /**
   * Update widget
   */
  async updateWidget(
    widgetId: number,
    data: {
      x?: number;
      y?: number;
      w?: number;
      h?: number;
      config?: any;
      title?: string;
    }
  ): Promise<{ data: any }> {
    return api.put(`/api/v1/dashboards/widgets/${widgetId}`, data);
  },

  /**
   * Delete widget
   */
  async deleteWidget(widgetId: number): Promise<{ data: { success: boolean; message: string } }> {
    return api.delete(`/api/v1/dashboards/widgets/${widgetId}`);
  },

  /**
   * Get widget templates
   */
  async getWidgetTemplates(): Promise<{ data: { templates: WidgetTemplate[] } }> {
    return api.get('/api/v1/dashboards/templates/widgets');
  },
};

export default dashboardBuilderApi;

