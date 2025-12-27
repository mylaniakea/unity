import { Server, Database, HardDrive } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface InfrastructureHealth {
  servers: {
    total: number;
    healthy: number;
    unhealthy: number;
  };
  storage: {
    total: number;
    devices: number;
    pools: number;
  };
  databases: {
    total: number;
    online: number;
    offline: number;
  };
}

interface InfrastructureOverviewProps {
  infrastructure: InfrastructureHealth | null;
  loading?: boolean;
}

export default function InfrastructureOverview({ infrastructure, loading }: InfrastructureOverviewProps) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-4 animate-pulse"></div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (!infrastructure) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
          Infrastructure
        </h3>
        <p className="text-gray-500 dark:text-gray-400">No infrastructure data available</p>
      </div>
    );
  }

  const { servers, storage, databases } = infrastructure;

  const cards = [
    {
      title: 'Servers',
      icon: Server,
      total: servers.total,
      healthy: servers.healthy,
      unhealthy: servers.unhealthy,
      color: 'blue',
      link: '/infrastructure/servers'
    },
    {
      title: 'Storage',
      icon: HardDrive,
      total: storage.total,
      healthy: storage.devices,
      unhealthy: 0,
      color: 'purple',
      link: '/infrastructure/storage'
    },
    {
      title: 'Databases',
      icon: Database,
      total: databases.total,
      healthy: databases.online,
      unhealthy: databases.offline,
      color: 'green',
      link: '/infrastructure/databases'
    }
  ];

  const colorMap = {
    blue: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800',
      icon: 'text-blue-500'
    },
    purple: {
      bg: 'bg-purple-50 dark:bg-purple-900/20',
      border: 'border-purple-200 dark:border-purple-800',
      icon: 'text-purple-500'
    },
    green: {
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-200 dark:border-green-800',
      icon: 'text-green-500'
    }
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          Infrastructure
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {cards.map((card) => {
          const Icon = card.icon;
          const colors = colorMap[card.color as keyof typeof colorMap];
          
          return (
            <div
              key={card.title}
              className={`${colors.bg} ${colors.border} border rounded-lg p-4 cursor-pointer hover:shadow-md transition-shadow`}
              onClick={() => navigate(card.link)}
            >
              <div className="flex items-center justify-between mb-3">
                <Icon className={`${colors.icon} w-6 h-6`} />
                <span className="text-2xl font-bold text-gray-900 dark:text-white">
                  {card.total}
                </span>
              </div>
              
              <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                {card.title}
              </h4>
              
              <div className="flex justify-between text-sm">
                <span className="text-green-600 dark:text-green-400">
                  ✓ {card.healthy} healthy
                </span>
                {card.unhealthy > 0 && (
                  <span className="text-red-600 dark:text-red-400">
                    ✗ {card.unhealthy} issues
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
