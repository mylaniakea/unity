import api from './client';

export interface BlueprintTemplate {
  name: string;
  description?: string;
  type?: string;
  image?: string;
  port?: number;
  replicas?: number;
  service_type?: string | null;
  health_check?: boolean | null;
  resources?: Record<string, any> | null;
  ingress?: Record<string, any> | null;
  storage?: Record<string, any> | null;
  secrets?: Record<string, any> | null;
  env?: Record<string, any> | null;
  config?: Record<string, any> | null;
}

export interface TemplatesResponse {
  templates: BlueprintTemplate[];
  template_names: string[];
  count: number;
}

export async function listTemplates(): Promise<TemplatesResponse> {
  const res = await api.get('/api/v1/orchestrate/templates');
  return res.data;
}
