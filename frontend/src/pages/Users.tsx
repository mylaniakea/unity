import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Users as UsersIcon, Plus, Edit, Trash2, X, Shield, Eye, EyeOff, Search } from 'lucide-react';
import api from '@/api/client';
import { useNotification } from '@/contexts/NotificationContext';
import { useConfirm } from '@/contexts/ConfirmDialogContext';
import { useRole } from '@/contexts/RoleContext';
import { cn } from '@/lib/utils';

interface User {
    id: number;
    username: string;
    email: string | null;
    role: 'admin' | 'user' | 'viewer';
    is_active: boolean;
    created_at: string;
}

export default function Users() {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [showAddModal, setShowAddModal] = useState(false);
    const [showEditModal, setShowEditModal] = useState(false);
    const [selectedUser, setSelectedUser] = useState<User | null>(null);
    const { showNotification } = useNotification();
    const { showConfirm } = useConfirm();
    const { user: currentUser, isAdmin } = useRole();

    useEffect(() => {
        fetchUsers();
    }, []);

    const fetchUsers = async () => {
        try {
            if (isAdmin) {
                // Admins see all users
                const res = await api.get('/users/');
                setUsers(res.data);
            } else {
                // Regular users see only themselves
                if (currentUser) {
                    setUsers([currentUser]);
                }
            }
            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch users', error);
            showNotification('Failed to load users', 'error');
            setLoading(false);
        }
    };

    const handleDeleteUser = async (user: User) => {
        const confirmed = await showConfirm({
            title: `Delete user "${user.username}"?`,
            message: 'This action cannot be undone.'
        });

        if (!confirmed) return;

        try {
            await api.delete(`/users/${user.id}`);
            showNotification(`User ${user.username} deleted successfully`, 'success');
            fetchUsers();
        } catch (error: any) {
            console.error('Failed to delete user', error);
            showNotification(error.response?.data?.detail || 'Failed to delete user', 'error');
        }
    };

    const getRoleBadgeColor = (role: string) => {
        switch (role) {
            case 'admin':
                return 'bg-red-500/20 text-red-600 dark:text-red-400 border-red-500/30';
            case 'user':
                return 'bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30';
            case 'viewer':
                return 'bg-gray-500/20 text-gray-600 dark:text-gray-400 border-gray-500/30';
            default:
                return 'bg-gray-500/20 text-gray-600 dark:text-gray-400 border-gray-500/30';
        }
    };

    const filteredUsers = users.filter(user =>
        user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.email?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        user.role.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (loading) return <div className="p-10 text-center">Loading users...</div>;

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        <UsersIcon />
                        {isAdmin ? 'User Management' : 'My Account'}
                    </h1>
                    <p className="text-muted-foreground">
                        {isAdmin ? 'Manage user accounts and permissions' : 'View and manage your account settings'}
                    </p>
                </div>
                {isAdmin && (
                    <button
                        onClick={() => setShowAddModal(true)}
                        className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors"
                    >
                        <Plus size={18} />
                        Add User
                    </button>
                )}
            </div>

            {/* Search Bar - Only show for admins */}
            {isAdmin && (
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                    <input
                        type="text"
                        placeholder="Search users by username, email, or role..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                </div>
            )}

            {/* Users Table */}
            <div className="bg-card border border-border rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead className="bg-muted/50 border-b border-border">
                            <tr>
                                <th className="text-left p-4 font-semibold">Username</th>
                                <th className="text-left p-4 font-semibold">Email</th>
                                <th className="text-left p-4 font-semibold">Role</th>
                                <th className="text-left p-4 font-semibold">Status</th>
                                <th className="text-left p-4 font-semibold">Created</th>
                                <th className="text-right p-4 font-semibold">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredUsers.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="text-center p-8 text-muted-foreground">
                                        {searchQuery ? 'No users found matching your search' : 'No users yet'}
                                    </td>
                                </tr>
                            ) : (
                                filteredUsers.map((user) => (
                                    <motion.tr
                                        key={user.id}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="border-b border-border hover:bg-muted/30 transition-colors"
                                    >
                                        <td className="p-4">
                                            <div className="flex items-center gap-2">
                                                <Shield size={16} className="text-muted-foreground" />
                                                <span className="font-medium">{user.username}</span>
                                            </div>
                                        </td>
                                        <td className="p-4 text-muted-foreground">{user.email || '—'}</td>
                                        <td className="p-4">
                                            <span
                                                className={cn(
                                                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize',
                                                    getRoleBadgeColor(user.role)
                                                )}
                                            >
                                                {user.role}
                                            </span>
                                        </td>
                                        <td className="p-4">
                                            <span
                                                className={cn(
                                                    'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                                                    user.is_active
                                                        ? 'bg-green-500/20 text-green-600 dark:text-green-400'
                                                        : 'bg-red-500/20 text-red-600 dark:text-red-400'
                                                )}
                                            >
                                                {user.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                        <td className="p-4 text-muted-foreground text-sm">
                                            {new Date(user.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="p-4">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => {
                                                        setSelectedUser(user);
                                                        setShowEditModal(true);
                                                    }}
                                                    className="p-2 hover:bg-muted rounded-md transition-colors"
                                                    title={isAdmin ? "Edit user" : "Change password"}
                                                >
                                                    <Edit size={16} />
                                                </button>
                                                {isAdmin && (
                                                    <button
                                                        onClick={() => handleDeleteUser(user)}
                                                        className="p-2 hover:bg-red-500/20 text-red-600 dark:text-red-400 rounded-md transition-colors"
                                                        title="Delete user"
                                                    >
                                                        <Trash2 size={16} />
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </motion.tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Add User Modal */}
            {showAddModal && (
                <AddUserModal
                    onClose={() => setShowAddModal(false)}
                    onSuccess={() => {
                        setShowAddModal(false);
                        fetchUsers();
                    }}
                />
            )}

            {/* Edit User Modal */}
            {showEditModal && selectedUser && (
                <EditUserModal
                    user={selectedUser}
                    onClose={() => {
                        setShowEditModal(false);
                        setSelectedUser(null);
                    }}
                    onSuccess={() => {
                        setShowEditModal(false);
                        setSelectedUser(null);
                        fetchUsers();
                    }}
                />
            )}
        </div>
    );
}

// Add User Modal Component
function AddUserModal({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) {
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [role, setRole] = useState<'admin' | 'user' | 'viewer'>('user');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const { showNotification } = useNotification();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== confirmPassword) {
            showNotification('Passwords do not match', 'error');
            return;
        }

        if (password.length < 8) {
            showNotification('Password must be at least 8 characters', 'error');
            return;
        }

        setLoading(true);
        try {
            await api.post('/users/', {
                username,
                email: email || null,
                password,
                role
            });
            showNotification(`User ${username} created successfully`, 'success');
            onSuccess();
        } catch (error: any) {
            console.error('Failed to create user', error);
            showNotification(error.response?.data?.detail || 'Failed to create user', 'error');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-card border border-border rounded-xl p-6 w-full max-w-md shadow-xl"
            >
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold">Add New User</h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-muted rounded-md transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Username *</label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="w-full bg-background border border-border rounded-md px-3 py-2"
                            required
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Email</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full bg-background border border-border rounded-md px-3 py-2"
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Password *</label>
                        <div className="relative">
                            <input
                                type={showPassword ? 'text' : 'password'}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-background border border-border rounded-md px-3 py-2 pr-10"
                                required
                                minLength={8}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            >
                                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Confirm Password *</label>
                        <div className="relative">
                            <input
                                type={showConfirmPassword ? 'text' : 'password'}
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                className="w-full bg-background border border-border rounded-md px-3 py-2 pr-10"
                                required
                                minLength={8}
                            />
                            <button
                                type="button"
                                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            >
                                {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                        {confirmPassword && password !== confirmPassword && (
                            <p className="text-xs text-red-500">Passwords do not match</p>
                        )}
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Role *</label>
                        <select
                            value={role}
                            onChange={(e) => setRole(e.target.value as 'admin' | 'user' | 'viewer')}
                            className="w-full bg-background border border-border rounded-md px-3 py-2"
                        >
                            <option value="viewer">Viewer (Read-only)</option>
                            <option value="user">User (Can edit)</option>
                            <option value="admin">Admin (Full access)</option>
                        </select>
                        <p className="text-xs text-muted-foreground">
                            {role === 'admin' && 'Full access to everything including user management'}
                            {role === 'user' && 'Can view and modify data, but cannot manage users'}
                            {role === 'viewer' && 'Read-only access, cannot create/edit/delete'}
                        </p>
                    </div>

                    <div className="flex gap-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2 border border-border rounded-md hover:bg-muted transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !username || !password || password !== confirmPassword}
                            className="flex-1 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {loading ? 'Creating...' : 'Create User'}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
    );
}

// Edit User Modal Component
function EditUserModal({
    user,
    onClose,
    onSuccess
}: {
    user: User;
    onClose: () => void;
    onSuccess: () => void;
}) {
    const [email, setEmail] = useState(user.email || '');
    const [role, setRole] = useState<'admin' | 'user' | 'viewer'>(user.role);
    const [isActive, setIsActive] = useState(user.is_active);
    const [loading, setLoading] = useState(false);
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showCurrentPassword, setShowCurrentPassword] = useState(false);
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [resettingPassword, setResettingPassword] = useState(false);
    const { showNotification } = useNotification();
    const { user: currentUser, isAdmin } = useRole();
    const isEditingSelf = currentUser?.id === user.id && !isAdmin;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        setLoading(true);
        try {
            await api.put(`/users/${user.id}`, {
                email: email || null,
                role,
                is_active: isActive
            });
            showNotification(`User ${user.username} updated successfully`, 'success');
            onSuccess();
        } catch (error: any) {
            console.error('Failed to update user', error);
            showNotification(error.response?.data?.detail || 'Failed to update user', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handlePasswordReset = async () => {
        // Validate passwords
        if (!newPassword || newPassword.length < 8) {
            showNotification('Password must be at least 8 characters long', 'error');
            return;
        }

        if (newPassword !== confirmPassword) {
            showNotification('Passwords do not match', 'error');
            return;
        }

        // If editing self, require current password
        if (isEditingSelf && !currentPassword) {
            showNotification('Current password is required', 'error');
            return;
        }

        setResettingPassword(true);
        try {
            if (isEditingSelf) {
                // Self-service password change
                await api.post('/auth/change-password', {
                    current_password: currentPassword,
                    new_password: newPassword
                });
                showNotification('Password changed successfully', 'success');
            } else {
                // Admin reset password
                await api.post(`/auth/admin/reset-password/${user.id}`, {
                    new_password: newPassword
                });
                showNotification(`Password reset successfully for ${user.username}`, 'success');
            }
            setCurrentPassword('');
            setNewPassword('');
            setConfirmPassword('');
        } catch (error: any) {
            console.error('Failed to change password', error);
            showNotification(error.response?.data?.detail || 'Failed to change password', 'error');
        } finally {
            setResettingPassword(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-card border border-border rounded-xl p-6 w-full max-w-md shadow-xl"
            >
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold">
                        {isEditingSelf ? 'My Account' : `Edit User: ${user.username}`}
                    </h2>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-muted rounded-md transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {!isEditingSelf ? (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-muted-foreground">Username</label>
                            <input
                                type="text"
                                value={user.username}
                                disabled
                                className="w-full bg-muted border border-border rounded-md px-3 py-2 text-muted-foreground cursor-not-allowed"
                            />
                            <p className="text-xs text-muted-foreground">Username cannot be changed</p>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Email</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full bg-background border border-border rounded-md px-3 py-2"
                            />
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Role</label>
                            <select
                                value={role}
                                onChange={(e) => setRole(e.target.value as 'admin' | 'user' | 'viewer')}
                                className="w-full bg-background border border-border rounded-md px-3 py-2"
                            >
                                <option value="viewer">Viewer (Read-only)</option>
                                <option value="user">User (Can edit)</option>
                                <option value="admin">Admin (Full access)</option>
                            </select>
                            <p className="text-xs text-muted-foreground">
                                {role === 'admin' && 'Full access to everything including user management'}
                                {role === 'user' && 'Can view and modify data, but cannot manage users'}
                                {role === 'viewer' && 'Read-only access, cannot create/edit/delete'}
                            </p>
                        </div>

                        <div className="flex items-center justify-between p-3 bg-muted/50 rounded-md">
                            <div>
                                <label htmlFor="isActiveToggle" className="text-sm font-medium">Account Status</label>
                                <p className="text-xs text-muted-foreground">
                                    {isActive ? 'User can log in' : 'User cannot log in'}
                                </p>
                            </div>
                            <input
                                type="checkbox"
                                id="isActiveToggle"
                                checked={isActive}
                                onChange={(e) => setIsActive(e.target.checked)}
                                className="h-4 w-4 accent-primary"
                            />
                        </div>

                        <div className="flex gap-3 pt-4">
                            <button
                                type="button"
                                onClick={onClose}
                                className="flex-1 px-4 py-2 border border-border rounded-md hover:bg-muted transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={loading}
                                className="flex-1 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {loading ? 'Saving...' : 'Save Changes'}
                            </button>
                        </div>
                    </form>
                ) : null}

                {/* Password Reset/Change Section */}
                <div className={cn("space-y-4", !isEditingSelf && "border-t border-border pt-4")}>
                    <h3 className="text-sm font-semibold">
                        {isEditingSelf ? 'Change Password' : 'Reset Password'}
                    </h3>

                    {isEditingSelf && (
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Current Password</label>
                            <div className="relative">
                                <input
                                    type={showCurrentPassword ? 'text' : 'password'}
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 pr-10"
                                    placeholder="Enter current password"
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>
                    )}

                    <div className="space-y-2">
                            <label className="text-sm font-medium">New Password</label>
                            <div className="relative">
                                <input
                                    type={showNewPassword ? 'text' : 'password'}
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 pr-10"
                                    placeholder="Enter new password (min 8 chars)"
                                    minLength={8}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowNewPassword(!showNewPassword)}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <label className="text-sm font-medium">Confirm New Password</label>
                            <div className="relative">
                                <input
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="w-full bg-background border border-border rounded-md px-3 py-2 pr-10"
                                    placeholder="Confirm new password"
                                    minLength={8}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                            {confirmPassword && newPassword !== confirmPassword && (
                                <p className="text-xs text-red-500">Passwords do not match</p>
                            )}
                        </div>

                        <button
                            type="button"
                            onClick={handlePasswordReset}
                            disabled={resettingPassword || !newPassword || !confirmPassword || newPassword !== confirmPassword || (isEditingSelf && !currentPassword)}
                            className="w-full bg-orange-500 text-white px-4 py-2 rounded-md hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {resettingPassword ? (isEditingSelf ? 'Changing Password...' : 'Resetting Password...') : (isEditingSelf ? 'Change Password' : 'Reset Password')}
                        </button>

                        {isEditingSelf && (
                            <button
                                type="button"
                                onClick={onClose}
                                className="w-full px-4 py-2 border border-border rounded-md hover:bg-muted transition-colors"
                            >
                                Close
                            </button>
                        )}
                    </div>
            </motion.div>
        </div>
    );
}
