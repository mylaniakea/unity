import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface CustomDropdownProps {
    options: { value: string | number; label: string }[];
    value: string | number;
    onChange: (value: string | number) => void;
    placeholder?: string;
    disabled?: boolean;
}

const CustomDropdown: React.FC<CustomDropdownProps> = ({
    options,
    value,
    onChange,
    placeholder = "Select an option",
    disabled = false,
}) => {
    const [isOpen, setIsOpen] = useState(false);

    const selectedOption = options.find((option) => option.value === value);

    const handleSelect = (optionValue: string | number) => {
        onChange(optionValue);
        setIsOpen(false);
    };

    return (
        <div className="relative w-full md:w-64">
            <button
                type="button"
                className={`flex justify-between items-center w-full px-4 py-2 text-sm font-medium bg-background border border-input rounded-md shadow-sm hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ${disabled ? "opacity-50 cursor-not-allowed" : ""
                    }`}
                onClick={() => !disabled && setIsOpen(!isOpen)}
                disabled={disabled}
            >
                <span className="truncate">{selectedOption?.label || placeholder}</span>
                <ChevronDown className="ml-2 h-4 w-4 opacity-50" />
            </button>

            {isOpen && (
                <div className="absolute z-50 mt-1 w-full rounded-md bg-popover text-popover-foreground shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none animate-in fade-in-0 zoom-in-95">
                    <div className="py-1 max-h-60 overflow-auto">
                        {options.map((option) => (
                            <button
                                key={option.value}
                                onClick={() => handleSelect(option.value)}
                                className="relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 px-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                                role="menuitem"
                            >
                                {option.label}
                            </button>
                        ))}
                        {options.length === 0 && (
                            <div className="px-2 py-1.5 text-sm text-muted-foreground">No options</div>
                        )}
                    </div>
                </div>
            )}

            {/* Backdrop to close */}
            {isOpen && (
                <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            )}
        </div>
    );
};

export default CustomDropdown;
