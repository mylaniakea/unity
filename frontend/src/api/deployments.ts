/**
 * Deployments API Client
 * 
 * Client for interacting with Unity's deployment management API.
 */

const API_BASE = '';  // Relative to same origin

export interface Stack {
  name: string;
  path: string;
  compose_file: string;
  status?: string;
  containers: number;
  running: number;
  created_at: string;
  updated_at: string;
}

export interface StackDetail extends Stack {
  compose_content: string;
  compose_data: any;
  containers: ContainerInfo[];
}

export interface ContainerInfo {
  id: string;
  name: string;
  image: string;
  state: string;
  created: string;
}

export interface StackMetrics {
  stack: string;
  containers: ContainerMetrics[];
}

export interface ContainerMetrics {
  container: string;
  cpu_percent: number;
  memory_usage: number;
  memory_limit: number;
  memory_percent: number;
}

export interface CreateStackRequest {
  name: string;
  compose_content: string;
  deploy?: boolean;
}

export interface UpdateStackRequest {
  compose_content: string;
  redeploy?: boolean;
}

class DeploymentsAPI {
  /**
   * List all stacks
   */
  async listStacks(): Promise<Stack[]> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/stacks`);
    if (!response.ok) {
      throw new Error(`Failed to list stacks: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get stack details
   */
  async getStack(name: string): Promise<StackDetail> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/stacks/${name}`);
    if (!response.ok) {
      throw new Error(`Failed to get stack: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Create a new stack
   */
  async createStack(data: CreateStackRequest): Promise<StackDetail> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/stacks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create stack');
    }
    return response.json();
  }

  /**
   * Update an existing stack
   */
  async updateStack(name: string, data: UpdateStackRequest): Promise<StackDetail> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/stacks/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update stack');
    }
    return response.json();
  }

  /**
   * Delete a stack
   */
  async deleteStack(name: string, stopContainers = true): Promise<void> {
    const response = await fetch(
      `${API_BASE}/api/v1/deployments/stacks/${name}?stop_containers=${stopContainers}`,
      { method: 'DELETE' }
    );
    if (!response.ok) {
      throw new Error(`Failed to delete stack: ${response.statusText}`);
    }
  }

  /**
   * Start a stack
   */
  async startStack(name: string): Promise<StackDetail> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/stacks/${name}/start`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to start stack: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Stop a stack
   */
  async stopStack(name: string): Promise<StackDetail> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/stacks/${name}/stop`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to stop stack: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Restart a stack
   */
  async restartStack(name: string): Promise<StackDetail> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/stacks/${name}/restart`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to restart stack: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Get stack logs (non-streaming)
   */
  async getStackLogs(name: string, tail = 100): Promise<string[]> {
    const response = await fetch(
      `${API_BASE}/api/v1/deployments/stacks/${name}/logs?follow=false&tail=${tail}`
    );
    if (!response.ok) {
      throw new Error(`Failed to get logs: ${response.statusText}`);
    }
    const data = await response.json();
    return data.logs;
  }

  /**
   * Stream stack logs using EventSource (Server-Sent Events)
   */
  streamStackLogs(
    name: string,
    onLog: (log: string) => void,
    onError?: (error: Error) => void
  ): EventSource {
    const eventSource = new EventSource(
      `${API_BASE}/api/v1/deployments/stacks/${name}/logs?follow=true&tail=100`
    );

    eventSource.onmessage = (event) => {
      onLog(event.data);
    };

    eventSource.onerror = (error) => {
      eventSource.close();
      if (onError) {
        onError(new Error('Log stream error'));
      }
    };

    return eventSource;
  }

  /**
   * Get stack metrics
   */
  async getStackMetrics(name: string): Promise<StackMetrics> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/stacks/${name}/metrics`);
    if (!response.ok) {
      throw new Error(`Failed to get metrics: ${response.statusText}`);
    }
    return response.json();
  }

  /**
   * Convert docker run command to compose
   */
  async convertDockerRun(dockerRunCommand: string): Promise<string> {
    const response = await fetch(`${API_BASE}/api/v1/deployments/convert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ docker_run_command: dockerRunCommand }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to convert command');
    }
    const data = await response.json();
    return data.compose_content;
  }
}

export const deploymentsAPI = new DeploymentsAPI();
