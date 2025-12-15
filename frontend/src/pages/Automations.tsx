import React, { useEffect, useState } from 'react';
import api from '@/api/client';
import { useNotification } from '@/contexts/NotificationContext';
import { Save } from 'lucide-react';

interface CronSettings {
  cron_24hr_report: string;
  cron_7day_report: string;
  cron_monthly_report: string;
  polling_interval: number;
}

const Automations: React.FC = () => {
  const { showNotification } = useNotification();
  const [settings, setSettings] = useState<CronSettings>({
    cron_24hr_report: "0 2 * * *",
    cron_7day_report: "0 3 * * 1",
    cron_monthly_report: "0 4 1 * *",
    polling_interval: 30
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const res = await api.get('/settings/');
      setSettings({
        cron_24hr_report: res.data.cron_24hr_report || "0 2 * * *",
        cron_7day_report: res.data.cron_7day_report || "0 3 * * 1",
        cron_monthly_report: res.data.cron_monthly_report || "0 4 1 * *",
        polling_interval: res.data.polling_interval || 30,
      });
    } catch (error) {
      console.error("Failed to fetch settings", error);
      showNotification("Failed to load automation settings.", "error");
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await api.put('/settings/', settings);
      showNotification("Automation settings saved successfully!", "success");
    } catch (error) {
      console.error("Failed to save settings", error);
      showNotification("Failed to save automation settings.", "error");
    } finally {
      setLoading(false);
    }
  };

  // Generate time options in 30-minute increments
  const timeOptions = Array.from({ length: 48 }, (_, i) => {
    const hour = Math.floor(i / 2);
    const minute = (i % 2) * 30;
    const label = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
    const value = `${minute} ${hour}`;
    return { label, value };
  });

  // Day of week options (Monday=1, Sunday=0 or 7 in cron)
  const dayOfWeekOptions = [
    { label: "Monday", value: "1" },
    { label: "Tuesday", value: "2" },
    { label: "Wednesday", value: "3" },
    { label: "Thursday", value: "4" },
    { label: "Friday", value: "5" },
    { label: "Saturday", value: "6" },
    { label: "Sunday", value: "0" },
  ];

  // Day of month options (1-31)
  const dayOfMonthOptions = Array.from({ length: 31 }, (_, i) => ({
    label: String(i + 1),
    value: String(i + 1),
  }));

  // Polling interval options
  const pollingOptions = [
    { label: "15 seconds", value: 15 },
    { label: "30 seconds", value: 30 },
    { label: "60 seconds", value: 60 },
    { label: "5 minutes", value: 300 },
    { label: "10 minutes", value: 600 },
    { label: "20 minutes", value: 1200 },
    { label: "40 minutes", value: 2400 },
    { label: "60 minutes", value: 3600 },
    { label: "4 hours", value: 14400 },
    { label: "6 hours", value: 21600 },
    { label: "8 hours", value: 28800 },
    { label: "12 hours", value: 43200 },
  ];

  const parseCron = (cron: string) => {
    const parts = cron.split(' ');
    return {
      minute: parts[0],
      hour: parts[1],
      dayOfMonth: parts[2],
      month: parts[3],
      dayOfWeek: parts[4],
    };
  };

  const formatCron = (minute: string, hour: string, dayOfMonth: string, month: string, dayOfWeek: string) => {
    return `${minute} ${hour} ${dayOfMonth} ${month} ${dayOfWeek}`;
  };

  // Handlers for changing cron parts
  const handleCronChange = (reportType: keyof CronSettings, part: 'minute' | 'hour' | 'dayOfMonth' | 'dayOfWeek', value: string) => {
    setSettings(prev => {
      const currentCron = parseCron(prev[reportType]);
      let newMinute = currentCron.minute;
      let newHour = currentCron.hour;
      let newDayOfMonth = currentCron.dayOfMonth;
      let newDayOfWeek = currentCron.dayOfWeek;

      if (part === 'minute' || part === 'hour') {
        const [minutePart, hourPart] = value.split(' ');
        newMinute = minutePart;
        newHour = hourPart;
      } else if (part === 'dayOfMonth') {
        newDayOfMonth = value;
      } else if (part === 'dayOfWeek') {
        newDayOfWeek = value;
      }
      return {
        ...prev,
        [reportType]: formatCron(newMinute, newHour, newDayOfMonth, currentCron.month, newDayOfWeek)
      };
    });
  };

  const reportSettings = {
    daily: {
      label: "24-Hour Report (Daily)",
      cron: settings.cron_24hr_report,
      onCronChange: (part: 'minute' | 'hour', value: string) => handleCronChange("cron_24hr_report", part, value),
      showDayOfWeek: false,
      showDayOfMonth: false,
    },
    weekly: {
      label: "7-Day Report (Weekly)",
      cron: settings.cron_7day_report,
      onCronChange: (part: 'minute' | 'hour' | 'dayOfWeek', value: string) => handleCronChange("cron_7day_report", part, value),
      showDayOfWeek: true,
      showDayOfMonth: false,
    },
    monthly: {
      label: "Monthly Report",
      cron: settings.cron_monthly_report,
      onCronChange: (part: 'minute' | 'hour' | 'dayOfMonth', value: string) => handleCronChange("cron_monthly_report", part, value),
      showDayOfWeek: false,
      showDayOfMonth: true,
    },
  };

  return (
    <div className="space-y-8 p-6 bg-background text-foreground min-h-screen">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Automations</h1>
          <p className="text-muted-foreground">Configure scheduled tasks and reports.</p>
        </div>
        <button
          onClick={handleSave}
          disabled={loading}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
        >
          <Save size={18} className={loading ? "animate-spin" : ""} />
          {loading ? "Saving..." : "Save Settings"}
        </button>
      </div>

      {/* Polling Settings */}
      <div className="bg-card border border-border rounded-xl p-6">
        <h3 className="text-xl font-semibold mb-4">Dashboard Polling</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Configure how frequently the Dashboard refreshes real-time statistics.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
          <label className="block text-sm font-medium text-muted-foreground">Polling Interval:</label>
          <select
            className="bg-input border border-border rounded-md px-3 py-2 focus:ring-1 focus:ring-primary outline-none col-span-2"
            value={settings.polling_interval}
            onChange={(e) => setSettings(prev => ({ ...prev, polling_interval: parseInt(e.target.value) }))}
            disabled={loading}
          >
            {pollingOptions.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="space-y-6">
        {Object.entries(reportSettings).map(([key, report]) => {
          const cronParts = parseCron(report.cron);
          const timeValue = `${cronParts.minute} ${cronParts.hour}`;

          return (
            <div key={key} className="bg-card border border-border rounded-xl p-6">
              <h3 className="text-xl font-semibold mb-4">{report.label}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                <label className="block text-sm font-medium text-muted-foreground">Run Time:</label>
                <select
                  className="bg-input border border-border rounded-md px-3 py-2 focus:ring-1 focus:ring-primary outline-none col-span-2"
                  value={timeValue}
                  onChange={(e) => report.onCronChange('minute', e.target.value)}
                  disabled={loading}
                >
                  {timeOptions.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>

                {report.showDayOfWeek && (
                  <>
                    <label className="block text-sm font-medium text-muted-foreground">Day of Week:</label>
                    <select
                      className="bg-input border border-border rounded-md px-3 py-2 focus:ring-1 focus:ring-primary outline-none col-span-2"
                      value={cronParts.dayOfWeek}
                      onChange={(e) => report.onCronChange('dayOfWeek', e.target.value)}
                      disabled={loading}
                    >
                      {dayOfWeekOptions.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </>
                )}

                {report.showDayOfMonth && (
                  <>
                    <label className="block text-sm font-medium text-muted-foreground">Day of Month:</label>
                    <select
                      className="bg-input border border-border rounded-md px-3 py-2 focus:ring-1 focus:ring-primary outline-none col-span-2"
                      value={cronParts.dayOfMonth}
                      onChange={(e) => report.onCronChange('dayOfMonth', e.target.value)}
                      disabled={loading}
                    >
                      {dayOfMonthOptions.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Automations;
