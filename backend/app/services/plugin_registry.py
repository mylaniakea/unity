"""
Plugin Registry - Central definition of all available data collection plugins.

Each plugin defines:
- id: Unique identifier
- name: Human-readable name
- description: What data this plugin collects
- check_cmd: Command to verify tool is installed
- collect_cmd: Command to gather data
- parser: Output format (json, csv, text)
- install_script: Commands to install the tool (for supported OS)
- os: List of supported operating systems
- category: Plugin category for grouping
- requires_sudo: Whether commands need root/sudo
"""

PLUGINS = {
    # ===================
    # THERMAL MONITORING
    # ===================
    "lm-sensors": {
        "id": "lm-sensors",
        "name": "LM Sensors",
        "description": "CPU, GPU, and chipset temperatures via lm-sensors",
        "check_cmd": "which sensors",
        "collect_cmd": "sensors -j",
        "parser": "json",
        "install_script": {
            "debian": "apt-get update && apt-get install -y lm-sensors && yes '' | sensors-detect",
            "rhel": "yum install -y lm_sensors && yes '' | sensors-detect",
            "arch": "pacman -S --noconfirm lm_sensors && yes '' | sensors-detect"
        },
        "os": ["linux"],
        "category": "thermal",
        "requires_sudo": False
    },
    "ipmitool": {
        "id": "ipmitool",
        "name": "IPMI Sensors",
        "description": "Server BMC sensors - temps, fans, voltages via IPMI",
        "check_cmd": "which ipmitool",
        "collect_cmd": "ipmitool sensor list",
        "parser": "text",
        "install_script": {
            "debian": "apt-get update && apt-get install -y ipmitool",
            "rhel": "yum install -y ipmitool",
            "arch": "pacman -S --noconfirm ipmitool"
        },
        "os": ["linux"],
        "category": "thermal",
        "requires_sudo": True
    },

    # ===================
    # STORAGE & DISKS
    # ===================
    "smartctl": {
        "id": "smartctl",
        "name": "SMART Disk Health",
        "description": "Disk health, SMART data, power-on hours, and bad sectors",
        "check_cmd": "which smartctl",
        "collect_cmd": "smartctl -a -j /dev/sda",
        "parser": "json",
        "install_script": {
            "debian": "apt-get update && apt-get install -y smartmontools",
            "rhel": "yum install -y smartmontools",
            "arch": "pacman -S --noconfirm smartmontools"
        },
        "os": ["linux"],
        "category": "storage",
        "requires_sudo": True,
        "device_discovery_cmd": "lsblk -d -o NAME,TYPE -n | grep disk | awk '{print \"/dev/\" $1}'"
    },
    "zpool-status": {
        "id": "zpool-status",
        "name": "ZFS Pool Status",
        "description": "ZFS pool health, capacity, and scrub status",
        "check_cmd": "which zpool",
        "collect_cmd": "zpool status -v && zpool list -H -o name,size,alloc,free,health",
        "parser": "text",
        "install_script": {
            "debian": "apt-get update && apt-get install -y zfsutils-linux",
            "rhel": "# ZFS on RHEL requires additional repos",
            "arch": "# Install zfs-dkms from AUR"
        },
        "os": ["linux"],
        "category": "storage",
        "requires_sudo": False
    },
    "mdadm": {
        "id": "mdadm",
        "name": "Software RAID Status",
        "description": "Linux software RAID (md) array status",
        "check_cmd": "test -f /proc/mdstat",
        "collect_cmd": "cat /proc/mdstat",
        "parser": "text",
        "install_script": {
            "debian": "apt-get update && apt-get install -y mdadm",
            "rhel": "yum install -y mdadm",
            "arch": "pacman -S --noconfirm mdadm"
        },
        "os": ["linux"],
        "category": "storage",
        "requires_sudo": False
    },
    "iostat": {
        "id": "iostat",
        "name": "Disk I/O Stats",
        "description": "Disk I/O statistics per device - reads, writes, utilization",
        "check_cmd": "which iostat",
        "collect_cmd": "iostat -x -o JSON 1 1",
        "parser": "json",
        "install_script": {
            "debian": "apt-get update && apt-get install -y sysstat",
            "rhel": "yum install -y sysstat",
            "arch": "pacman -S --noconfirm sysstat"
        },
        "os": ["linux"],
        "category": "storage",
        "requires_sudo": False
    },
    "lsblk": {
        "id": "lsblk",
        "name": "Block Devices",
        "description": "Block device info - partitions, sizes, mount points",
        "check_cmd": "which lsblk",
        "collect_cmd": "lsblk -J -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,UUID",
        "parser": "json",
        "install_script": {
            "debian": "# Usually pre-installed (util-linux)",
            "rhel": "# Usually pre-installed (util-linux)",
            "arch": "# Usually pre-installed (util-linux)"
        },
        "os": ["linux"],
        "category": "storage",
        "requires_sudo": False
    },

    # ===================
    # GPU
    # ===================
    "nvidia-smi": {
        "id": "nvidia-smi",
        "name": "NVIDIA GPU Stats",
        "description": "GPU temperature, utilization, and VRAM usage",
        "check_cmd": "which nvidia-smi",
        "collect_cmd": "nvidia-smi --query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw --format=csv,noheader,nounits",
        "parser": "csv",
        "install_script": {
            "debian": "# NVIDIA drivers must be installed separately for your GPU model",
            "rhel": "# NVIDIA drivers must be installed separately for your GPU model",
            "arch": "# NVIDIA drivers must be installed separately for your GPU model"
        },
        "os": ["linux"],
        "category": "gpu",
        "requires_sudo": False
    },

    # ===================
    # CONTAINERS
    # ===================
    "docker-stats": {
        "id": "docker-stats",
        "name": "Docker Container Stats",
        "description": "Container CPU, memory usage, and network I/O",
        "check_cmd": "which docker",
        "collect_cmd": "docker stats --no-stream --format '{{json .}}'",
        "parser": "jsonl",
        "install_script": {
            "debian": "curl -fsSL https://get.docker.com | sh",
            "rhel": "curl -fsSL https://get.docker.com | sh",
            "arch": "pacman -S --noconfirm docker && systemctl enable --now docker"
        },
        "os": ["linux"],
        "category": "containers",
        "requires_sudo": False
    },
    "lxc-list": {
        "id": "lxc-list",
        "name": "LXD Containers",
        "description": "LXD/LXC container list and status",
        "check_cmd": "which lxc",
        "collect_cmd": "lxc list --format json",
        "parser": "json",
        "install_script": {
            "debian": "apt-get update && apt-get install -y lxd",
            "rhel": "# LXD requires snap on RHEL",
            "arch": "pacman -S --noconfirm lxd"
        },
        "os": ["linux"],
        "category": "containers",
        "requires_sudo": False
    },

    # ===================
    # VIRTUALIZATION
    # ===================
    "virsh": {
        "id": "virsh",
        "name": "KVM/libvirt VMs",
        "description": "libvirt/KVM virtual machine list and status",
        "check_cmd": "which virsh",
        "collect_cmd": "virsh list --all",
        "parser": "text",
        "install_script": {
            "debian": "apt-get update && apt-get install -y libvirt-clients",
            "rhel": "yum install -y libvirt-client",
            "arch": "pacman -S --noconfirm libvirt"
        },
        "os": ["linux"],
        "category": "virtualization",
        "requires_sudo": True
    },

    # ===================
    # NETWORK
    # ===================
    "ss": {
        "id": "ss",
        "name": "Socket Statistics",
        "description": "Open ports and listening services",
        "check_cmd": "which ss",
        "collect_cmd": "ss -tuln",
        "parser": "text",
        "install_script": {
            "debian": "# Usually pre-installed (iproute2)",
            "rhel": "# Usually pre-installed (iproute2)",
            "arch": "# Usually pre-installed (iproute2)"
        },
        "os": ["linux"],
        "category": "network",
        "requires_sudo": False
    },
    "fail2ban": {
        "id": "fail2ban",
        "name": "Fail2Ban Status",
        "description": "Banned IPs and jail status for intrusion prevention",
        "check_cmd": "which fail2ban-client",
        "collect_cmd": "fail2ban-client status",
        "parser": "text",
        "install_script": {
            "debian": "apt-get update && apt-get install -y fail2ban",
            "rhel": "yum install -y fail2ban",
            "arch": "pacman -S --noconfirm fail2ban"
        },
        "os": ["linux"],
        "category": "network",
        "requires_sudo": True
    },
    "iperf3": {
        "id": "iperf3",
        "name": "Network Bandwidth",
        "description": "Network bandwidth testing (requires iperf3 server)",
        "check_cmd": "which iperf3",
        "collect_cmd": "# Requires target server: iperf3 -c <server> -J",
        "parser": "json",
        "install_script": {
            "debian": "apt-get update && apt-get install -y iperf3",
            "rhel": "yum install -y iperf3",
            "arch": "pacman -S --noconfirm iperf3"
        },
        "os": ["linux"],
        "category": "network",
        "requires_sudo": False
    },

    # ===================
    # SERVICES & SYSTEM
    # ===================
    "systemctl": {
        "id": "systemctl",
        "name": "Running Services",
        "description": "List of running systemd services",
        "check_cmd": "which systemctl",
        "collect_cmd": "systemctl list-units --type=service --state=running --no-pager --output=json",
        "parser": "json",
        "install_script": {
            "debian": "# Pre-installed on systemd systems",
            "rhel": "# Pre-installed on systemd systems",
            "arch": "# Pre-installed on systemd systems"
        },
        "os": ["linux"],
        "category": "services",
        "requires_sudo": False
    },
    "journalctl": {
        "id": "journalctl",
        "name": "System Logs (Errors)",
        "description": "Recent error-level system log entries",
        "check_cmd": "which journalctl",
        "collect_cmd": "journalctl -p err -n 50 --no-pager -o json",
        "parser": "jsonl",
        "install_script": {
            "debian": "# Pre-installed on systemd systems",
            "rhel": "# Pre-installed on systemd systems",
            "arch": "# Pre-installed on systemd systems"
        },
        "os": ["linux"],
        "category": "services",
        "requires_sudo": True
    },

    # ===================
    # UPS / POWER
    # ===================
    "upsc": {
        "id": "upsc",
        "name": "UPS Status (NUT)",
        "description": "UPS battery level, load, and runtime via NUT",
        "check_cmd": "which upsc",
        "collect_cmd": "upsc $(upsc -l 2>/dev/null | head -1) 2>/dev/null || echo 'No UPS found'",
        "parser": "text",
        "install_script": {
            "debian": "apt-get update && apt-get install -y nut",
            "rhel": "yum install -y nut",
            "arch": "pacman -S --noconfirm nut"
        },
        "os": ["linux"],
        "category": "power",
        "requires_sudo": False
    }
}

# Plugin categories for UI grouping
PLUGIN_CATEGORIES = {
    "thermal": {"name": "Thermal Monitoring", "icon": "thermometer"},
    "storage": {"name": "Storage & Disks", "icon": "hard-drive"},
    "gpu": {"name": "GPU", "icon": "cpu"},
    "containers": {"name": "Containers", "icon": "box"},
    "virtualization": {"name": "Virtualization", "icon": "server"},
    "network": {"name": "Network & Security", "icon": "network"},
    "services": {"name": "Services & Logs", "icon": "activity"},
    "power": {"name": "UPS & Power", "icon": "battery"}
}


def get_plugin(plugin_id: str) -> dict | None:
    """Get a plugin definition by ID."""
    return PLUGINS.get(plugin_id)


def get_all_plugins() -> list[dict]:
    """Get all available plugins."""
    return list(PLUGINS.values())


def get_plugins_by_category(category: str) -> list[dict]:
    """Get all plugins in a specific category."""
    return [p for p in PLUGINS.values() if p.get("category") == category]
