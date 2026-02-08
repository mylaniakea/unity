import React from 'react';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler,
    type ChartOptions
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';
import { useTheme } from '@/components/theme-provider';
import { cn } from '@/lib/utils';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    Title,
    Tooltip,
    Legend,
    Filler
);

interface DataPoint {
    timestamp: string;
    value: number;
}

interface MetricChartProps {
    title: string;
    data: DataPoint[];
    labels?: string[];
    color?: string;
    unit?: string;
    chartType?: 'bar' | 'line';
    height?: number;
    className?: string;
}

export default function MetricChart({
    title,
    data,
    labels: customLabels,
    color = "hsl(var(--primary))",
    unit = '',
    chartType = 'line',
    height = 300,
    className
}: MetricChartProps) {
    const { theme } = useTheme();
    const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

    // Prepare chart data
    const labels = customLabels || data.map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleTimeString();
    });

    const chartData = {
        labels,
        datasets: [
            {
                label: title,
                data: data.map(d => d.value),
                borderColor: color,
                backgroundColor: chartType === 'line'
                    ? `${color}33` // 20% opacity for area fill
                    : color,
                fill: chartType === 'line',
                tension: 0.4,
                pointRadius: data.length > 50 ? 0 : 3,
                pointHoverRadius: 5
            }
        ]
    };

    const options: ChartOptions<'line' | 'bar'> = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: false
            },
            tooltip: {
                mode: 'index',
                intersect: false,
                callbacks: {
                    label: (context) => {
                        let label = context.dataset.label || '';
                        if (label) {
                            label += ': ';
                        }
                        if (context.parsed.y !== null) {
                            label += context.parsed.y.toFixed(2) + unit;
                        }
                        return label;
                    }
                }
            }
        },
        scales: {
            x: {
                grid: {
                    color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
                },
                ticks: {
                    color: isDark ? '#9ca3af' : '#6b7280',
                    maxTicksLimit: 8
                }
            },
            y: {
                grid: {
                    color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
                },
                ticks: {
                    color: isDark ? '#9ca3af' : '#6b7280',
                    callback: function (value) {
                        if (typeof value === 'number') {
                            return value + unit;
                        }
                        return value;
                    }
                },
                beginAtZero: true
            }
        },
        interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
        }
    };

    return (
        <div className={cn("p-6 bg-card border border-border rounded-xl shadow-sm", className)}>
            <h3 className="text-lg font-semibold mb-4 text-card-foreground">
                {title}
            </h3>
            <div style={{ height: `${height}px` }}>
                {data.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                        No data available
                    </div>
                ) : chartType === 'line' ? (
                    <Line data={chartData} options={options as any} />
                ) : (
                    <Bar data={chartData} options={options as any} />
                )}
            </div>
        </div>
    );
}
