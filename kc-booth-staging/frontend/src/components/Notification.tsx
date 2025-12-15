import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, XCircle, Info } from 'lucide-react';
import { cn } from '@/lib/utils'; // Assuming cn utility is available

interface NotificationProps {
  message: string;
  type: 'success' | 'error' | 'info';
  onClose: () => void;
  isVisible: boolean;
}

const Notification: React.FC<NotificationProps> = ({ message, type, onClose, isVisible }) => {
  if (!isVisible) return null;

  const iconMap = {
    success: <CheckCircle2 size={20} />,
    error: <XCircle size={20} />,
    info: <Info size={20} />,
  };

  const colorMap = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -50 }}
          transition={{ duration: 0.3 }}
          className={cn(
            "fixed top-4 right-4 z-50 flex items-center gap-3 p-4 rounded-md text-white shadow-lg",
            colorMap[type]
          )}
          role="alert"
        >
          {iconMap[type]}
          <span>{message}</span>
          <button onClick={onClose} className="ml-auto p-1 rounded-full hover:bg-white/20">
            <XCircle size={16} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default Notification;
