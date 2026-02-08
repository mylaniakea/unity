import { Moon, Sun } from "lucide-react"
import { useTheme } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

export function ModeToggle() {
    const { theme, setTheme } = useTheme()

    return (
        <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className={cn(
                "p-2 rounded-md transition-colors",
                "hover:bg-accent hover:text-accent-foreground",
                "border border-input bg-background shadow-sm"
            )}
            title="Toggle theme"
        >
            {theme === "dark" ? (
                <Moon className="h-5 w-5" />
            ) : (
                <Sun className="h-5 w-5" />
            )}
            <span className="sr-only">Toggle theme</span>
        </button>
    )
}
