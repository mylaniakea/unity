import api from './client';

export interface MarketplacePlugin {
  id: string;
  name: string;
  version: string;
  description: string | null;
  author: string;
  category: string | null;
  tags: string[];
  rating_average: number;
  rating_count: number;
  install_count: number;
  verified: boolean;
  featured: boolean;
}

export interface PluginListResponse {
  plugins: MarketplacePlugin[];
  total: number;
  skip: number;
  limit: number;
}

export interface InstallResponse {
  success: boolean;
  message: string;
  plugin_id: string | null;
}

export const marketplaceApi = {
  /**
   * List plugins in the marketplace
   */
  async listPlugins(params?: {
    category?: string;
    tag?: string;
    search?: string;
    featured?: boolean;
    verified?: boolean;
    min_rating?: number;
    sort_by?: string;
    skip?: number;
    limit?: number;
  }): Promise<{ data: PluginListResponse }> {
    return api.get('/api/v1/marketplace/plugins', { params });
  },

  /**
   * Get plugin details
   */
  async getPlugin(pluginId: string): Promise<{ data: MarketplacePlugin }> {
    return api.get(`/api/v1/marketplace/plugins/${pluginId}`);
  },

  /**
   * Get plugin reviews
   */
  async getReviews(
    pluginId: string,
    params?: {
      skip?: number;
      limit?: number;
      sort_by?: string;
    }
  ): Promise<{ data: any }> {
    return api.get(`/api/v1/marketplace/plugins/${pluginId}/reviews`, { params });
  },

  /**
   * Install a plugin
   */
  async installPlugin(pluginId: string, version?: string): Promise<{ data: InstallResponse }> {
    return api.post(`/api/v1/marketplace/plugins/${pluginId}/install`, { version });
  },

  /**
   * Uninstall a plugin
   */
  async uninstallPlugin(pluginId: string): Promise<{ data: { success: boolean; message: string } }> {
    return api.delete(`/api/v1/marketplace/plugins/${pluginId}/uninstall`);
  },

  /**
   * Get categories
   */
  async getCategories(): Promise<{ data: { categories: string[] } }> {
    return api.get('/api/v1/marketplace/categories');
  },

  /**
   * Get tags
   */
  async getTags(): Promise<{ data: { tags: string[] } }> {
    return api.get('/api/v1/marketplace/tags');
  },
};

export default marketplaceApi;

