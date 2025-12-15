import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';

export default function ThemeToggle() {
    const { theme, toggleTheme } = useTheme();

    return (
        <button
            onClick={toggleTheme}
            className={cn(
                "p-2 rounded-lg transition-colors",
                "hover:bg-muted",
                "focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            )}
            title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            aria-label="Toggle theme"
        >
            {theme === 'light' ? (
                <Moon size={20} className="text-muted-foreground hover:text-foreground transition-colors" />
            ) : (
                <Sun size={20} className="text-muted-foreground hover:text-foreground transition-colors" />
            )}
        </button>
    );
}
