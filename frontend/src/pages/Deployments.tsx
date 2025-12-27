import { useState, useEffect } from 'react';
import { deploymentsAPI, Stack, StackDetail } from '../api/deployments';

export default function Deployments() {
  const [stacks, setStacks] = useState<Stack[]>([]);
  const [selectedStack, setSelectedStack] = useState<StackDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewStack, setShowNewStack] = useState(false);

  // Load stacks on mount
  useEffect(() => {
    loadStacks();
  }, []);

  const loadStacks = async () => {
    try {
      setLoading(true);
      const data = await deploymentsAPI.listStacks();
      setStacks(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectStack = async (stackName: string) => {
    try {
      const stack = await deploymentsAPI.getStack(stackName);
      setSelectedStack(stack);
      setShowNewStack(false);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleStart = async (stackName: string) => {
    try {
      await deploymentsAPI.startStack(stackName);
      await loadStacks();
      if (selectedStack?.name === stackName) {
        await selectStack(stackName);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleStop = async (stackName: string) => {
    try {
      await deploymentsAPI.stopStack(stackName);
      await loadStacks();
      if (selectedStack?.name === stackName) {
        await selectStack(stackName);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRestart = async (stackName: string) => {
    try {
      await deploymentsAPI.restartStack(stackName);
      await loadStacks();
      if (selectedStack?.name === stackName) {
        await selectStack(stackName);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (stackName: string) => {
    if (!confirm(`Delete stack "${stackName}"?`)) return;
    try {
      await deploymentsAPI.deleteStack(stackName);
      await loadStacks();
      if (selectedStack?.name === stackName) {
        setSelectedStack(null);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="border-b border-border p-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Deployments</h1>
            <p className="text-sm text-muted-foreground">Manage Docker Compose stacks</p>
          </div>
          <button
            onClick={() => {
              setShowNewStack(true);
              setSelectedStack(null);
            }}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            + New Stack
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Main Content - Three Column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Stack List */}
        <div className="w-80 border-r border-border overflow-y-auto">
          <div className="p-4 space-y-2">
            {loading ? (
              <div className="text-center text-muted-foreground py-8">Loading...</div>
            ) : stacks.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <p>No stacks yet</p>
                <p className="text-xs mt-2">Create your first stack to get started</p>
              </div>
            ) : (
              stacks.map((stack) => (
                <StackCard
                  key={stack.name}
                  stack={stack}
                  selected={selectedStack?.name === stack.name}
                  onClick={() => selectStack(stack.name)}
                  onStart={() => handleStart(stack.name)}
                  onStop={() => handleStop(stack.name)}
                  onRestart={() => handleRestart(stack.name)}
                  onDelete={() => handleDelete(stack.name)}
                />
              ))
            )}
          </div>
        </div>

        {/* Center Panel - Stack Details */}
        <div className="flex-1 overflow-y-auto">
          {showNewStack ? (
            <NewStackForm
              onSuccess={() => {
                loadStacks();
                setShowNewStack(false);
              }}
              onCancel={() => setShowNewStack(false)}
            />
          ) : selectedStack ? (
            <StackDetails stack={selectedStack} onUpdate={() => selectStack(selectedStack.name)} />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Select a stack or create a new one
            </div>
          )}
        </div>

        {/* Right Sidebar - Logs (optional, can be added later) */}
      </div>
    </div>
  );
}

// Stack Card Component
function StackCard({ stack, selected, onClick, onStart, onStop, onRestart, onDelete }: any) {
  const statusColor =
    stack.status === 'running' ? 'bg-green-500' :
    stack.status === 'stopped' ? 'bg-gray-500' :
    stack.status === 'partial' ? 'bg-yellow-500' : 'bg-gray-400';

  return (
    <div
      className={`p-3 rounded-lg border cursor-pointer transition-all ${
        selected
          ? 'border-primary bg-primary/5'
          : 'border-border hover:border-primary/50 hover:bg-accent'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${statusColor}`} />
          <h3 className="font-medium text-foreground">{stack.name}</h3>
        </div>
      </div>
      
      <div className="flex items-center gap-3 text-xs text-muted-foreground mb-2">
        <span>{stack.containers} containers</span>
        <span>·</span>
        <span>{stack.running} running</span>
      </div>

      <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
        {stack.status === 'stopped' ? (
          <button
            onClick={onStart}
            className="px-2 py-1 text-xs bg-green-600 hover:bg-green-700 text-white rounded"
          >
            Start
          </button>
        ) : (
          <>
            <button
              onClick={onStop}
              className="px-2 py-1 text-xs bg-orange-600 hover:bg-orange-700 text-white rounded"
            >
              Stop
            </button>
            <button
              onClick={onRestart}
              className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded"
            >
              Restart
            </button>
          </>
        )}
        <button
          onClick={onDelete}
          className="px-2 py-1 text-xs bg-red-600 hover:bg-red-700 text-white rounded ml-auto"
        >
          Delete
        </button>
      </div>
    </div>
  );
}

// New Stack Form
function NewStackForm({ onSuccess, onCancel }: any) {
  const [name, setName] = useState('');
  const [composeContent, setComposeContent] = useState(`version: '3.8'

services:
  app:
    image: nginx:latest
    ports:
      - "8080:80"
    restart: unless-stopped
`);
  const [deploying, setDeploying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setDeploying(true);
    setError(null);

    try {
      await deploymentsAPI.createStack({
        name,
        compose_content: composeContent,
        deploy: true,
      });
      onSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDeploying(false);
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Create New Stack</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-destructive/10 border border-destructive/20 rounded-md text-destructive text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Stack Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="my-stack"
            className="w-full px-3 py-2 border border-border rounded-md bg-background text-foreground"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Docker Compose YAML</label>
          <textarea
            value={composeContent}
            onChange={(e) => setComposeContent(e.target.value)}
            className="w-full h-96 px-3 py-2 border border-border rounded-md bg-background text-foreground font-mono text-sm"
            required
          />
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={deploying}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {deploying ? 'Deploying...' : 'Deploy Stack'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border border-border rounded-md hover:bg-accent"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}

// Stack Details Component
function StackDetails({ stack, onUpdate }: { stack: StackDetail; onUpdate: () => void }) {
  const [editing, setEditing] = useState(false);
  const [composeContent, setComposeContent] = useState(stack.compose_content);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await deploymentsAPI.updateStack(stack.name, {
        compose_content: composeContent,
        redeploy: true,
      });
      setEditing(false);
      onUpdate();
    } catch (err) {
      alert('Failed to update stack');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold">{stack.name}</h2>
          <p className="text-sm text-muted-foreground">
            {stack.containers?.length || 0} containers · Status: {stack.status}
          </p>
        </div>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="px-4 py-2 border border-border rounded-md hover:bg-accent"
          >
            Edit
          </button>
        )}
      </div>

      {editing ? (
        <div className="space-y-4">
          <textarea
            value={composeContent}
            onChange={(e) => setComposeContent(e.target.value)}
            className="w-full h-96 px-3 py-2 border border-border rounded-md bg-background text-foreground font-mono text-sm"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              {saving ? 'Saving...' : 'Save & Redeploy'}
            </button>
            <button
              onClick={() => {
                setEditing(false);
                setComposeContent(stack.compose_content);
              }}
              className="px-4 py-2 border border-border rounded-md hover:bg-accent"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <pre className="p-4 bg-muted rounded-lg text-sm overflow-x-auto">
          {stack.compose_content}
        </pre>
      )}

      {/* Container List */}
      {stack.containers && stack.containers.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Containers</h3>
          <div className="space-y-2">
            {stack.containers.map((container: any) => (
              <div
                key={container.id}
                className="p-3 border border-border rounded-md"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{container.name}</p>
                    <p className="text-sm text-muted-foreground">{container.image}</p>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs rounded ${
                      container.state === 'running'
                        ? 'bg-green-600 text-white'
                        : 'bg-gray-600 text-white'
                    }`}
                  >
                    {container.state}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
