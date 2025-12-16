import asyncssh
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple
from app import models

class SSHService:
    def __init__(self, profile: models.ServerProfile):
        self.profile = profile
        self.host = profile.ip_address
        self.username = profile.ssh_username or "matthew" # fallback default
        self.port = profile.ssh_port or 22
        
        # Determine keys
        self.client_keys = None
        if profile.ssh_key_path:
            self.client_keys = [profile.ssh_key_path]

    async def setup_keys(self, password: str) -> str:
        """
        Generates a local keypair (if needed) and installs the public key
        on the remote server using the provided password.
        Returns the path to the private key.
        """
        # 1. Ensure local app key exists
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        
        key_name = "homelab_id_rsa"
        private_key_path = data_dir / key_name
        public_key_path = data_dir / f"{key_name}.pub"
        
        if not private_key_path.exists():
            # Generate new keypair
            key = asyncssh.generate_private_key('ssh-rsa')
            key.write_private_key(str(private_key_path))
            key.write_public_key(str(public_key_path))
            # Set strict permissions
            os.chmod(private_key_path, 0o600)
            
        # Read public key content
        public_key_content = public_key_path.read_text().strip()
        
        # 2. Connect with password
        async with asyncssh.connect(
            self.host,
            port=self.port,
            username=self.username,
            password=password,
            known_hosts=None
        ) as conn:
            # 3. Append to authorized_keys
            # We use a safe one-liner to create dir and append
            cmd = (
                "mkdir -p -m 700 ~/.ssh && "
                f"grep -qF '{public_key_content}' ~/.ssh/authorized_keys 2>/dev/null || "
                f"echo '{public_key_content}' >> ~/.ssh/authorized_keys && "
                "chmod 600 ~/.ssh/authorized_keys"
            )
            result = await conn.run(cmd)
            
            if result.exit_status != 0:
                raise Exception(f"Failed to install key: {result.stderr}")
                
        return str(private_key_path.absolute())

    async def _get_connection(self):
        """Establish valid SSH connection"""
        if not self.host:
            raise Exception("No IP address defined for this profile")
            
        return await asyncssh.connect(
            self.host, 
            port=self.port, 
            username=self.username,
            client_keys=self.client_keys,
            agent_path=None if not self.profile.use_local_agent else asyncssh.SSH_AGENT_PATH,
            known_hosts=None # For lab environment simplicity; use strict checking in prod
        )

    async def execute_command(self, command: str) -> Tuple[str, str, int]:
        """Execute a raw command and return (stdout, stderr, exit_code)"""
        try:
            async with await self._get_connection() as conn:
                result = await conn.run(command)
                return result.stdout, result.stderr, result.exit_status
        except Exception as e:
             return "", str(e), -1

    async def verify_connection(self) -> Dict[str, Any]:
        """Simple ping/echo to verify auth works"""
        stdout, stderr, code = await self.execute_command("echo 'Connected'")
        success = code == 0 and "Connected" in stdout
        return {
            "success": success,
            "message": stdout.strip() if success else f"Failed: {stderr}",
            "host": self.host
        }

    async def get_extended_hardware_info(self) -> Dict[str, Any]:
        """
        Runs a comprehensive hardware scan:
        - PCI Devices (lspci)
        - Block Devices (lsblk)
        - RAID Status (/proc/mdstat)
        - Network Interfaces (ip addr)
        - GPU (lspci filter + nvidia-smi)
        """
        
        info = {
            "pci": [],
            "disks": [],
            "raid": "",
            "zfs_pools": [],
            "zfs_status": "",
            "network": [],
            "gpu": [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": None
        }

        try:
            # 1. PCI Devices
            cmd_pci = "lspci -vmm"
            out_pci, _, _ = await self.execute_command(cmd_pci)
            
            pci_devices = []
            current_device = {}
            for line in out_pci.splitlines():
                if not line.strip():
                    if current_device:
                        pci_devices.append(current_device)
                        current_device = {}
                    continue
                
                parts = line.split(':', 1)
                if len(parts) == 2:
                    current_device[parts[0].strip()] = parts[1].strip()
            
            if current_device:
                pci_devices.append(current_device)
            
            # Filter PCI: Exclude noise (Bridges, System periphs, etc)
            ignored_classes = ["bridge", "system", "serial bus", "communication", "hub", "memory", "isa", "smbus", "usb", "audio"]
            filtered_pci = []
            for d in pci_devices:
                cls = d.get("Class", "").lower()
                # Keep if not in ignored list (partial match)
                if not any(ign in cls for ign in ignored_classes):
                    filtered_pci.append(d)
            
            info["pci"] = filtered_pci

            # 1b. GPU Extraction
            gpu_keywords = ["vga", "3d", "display", "graphics", "video"]
            ignored_gpu_vendors = ["aspeed", "matrox"] # Common BMC/Onboard
            
            gpu_devices = []
            for d in pci_devices:
                cls = d.get("Class", "").lower()
                vendor = d.get("Vendor", "").lower()
                device = d.get("Device", "").lower()
                
                # Check if it's a GPU
                if any(k in cls for k in gpu_keywords):
                    # Filter out onboard/BMC graphics if requested
                    if any(ig in vendor for ig in ignored_gpu_vendors):
                        continue
                    if "integrated" in device:
                        continue
                        
                    gpu_devices.append(d)
            
            # Check for NVIDIA specifics
            cmd_nvidia = "nvidia-smi -L"
            out_nvidia, _, code_nvidia = await self.execute_command(cmd_nvidia)
            if code_nvidia == 0:
                for line in out_nvidia.splitlines():
                    if not any(line in str(g) for g in gpu_devices):
                        gpu_devices.append({"Model": line.strip(), "Vendor": "NVIDIA", "Type": "Dedicated (nvidia-smi)"})
            
            info["gpu"] = gpu_devices

            # 2. Disk Info
            # Added TRAN (transport) and ROTA (rotational) for better classification
            cmd_lsblk = "lsblk -J -o NAME,SIZE,FSTYPE,MOUNTPOINT,TYPE,MODEL,SERIAL,TRAN,ROTA"
            out_lsblk, _, code_lsblk = await self.execute_command(cmd_lsblk)
            
            if code_lsblk == 0:
                try:
                    data = json.loads(out_lsblk)
                    info["disks"] = data.get("blockdevices", [])
                except:
                    info["disks"] = [{"error": "Failed to parse lsblk JSON"}]
            else:
                info["disks"] = [{"error": f"lsblk failed with code {code_lsblk}"}]

            # 3. RAID / ZFS Info
            cmd_raid = "cat /proc/mdstat"
            out_raid, _, _ = await self.execute_command(cmd_raid)
            info["raid"] = out_raid
            
            # ZFS Check
            cmd_zpool_list = "zpool list -H -p -o name,size,alloc,free,health,frag"
            out_zpool, _, code_zpool = await self.execute_command(cmd_zpool_list)
            
            info["zfs_pools"] = []
            info["zfs_status"] = ""
            
            if code_zpool == 0 and out_zpool.strip():
                # Parse list
                for line in out_zpool.splitlines():
                    parts = line.split()
                    if len(parts) >= 5:
                        info["zfs_pools"].append({
                            "name": parts[0],
                            "size": parts[1],
                            "alloc": parts[2],
                            "free": parts[3],
                            "health": parts[4],
                            "frag": parts[5] if len(parts) > 5 else "N/A"
                        })
                        
                # Get detailed status
                out_status, _, _ = await self.execute_command("zpool status")
                info["zfs_status"] = out_status

            # 4. Network Info
            # Try JSON first
            cmd_ip = "ip -j -s addr" 
            out_ip, _, code_ip = await self.execute_command(cmd_ip)
            
            raw_network = []
            if code_ip == 0:
                try:
                    raw_network = json.loads(out_ip)
                except:
                    pass
            
            if not raw_network:
                # Fallback text parser for 'ip addr'
                cmd_ip_text = "ip addr"
                out_ip_text, _, _ = await self.execute_command(cmd_ip_text)
                
                parsed_net = []
                current_iface = None
                
                for line in out_ip_text.splitlines():
                    # 1: lo: <LOOPBACK,UP...> ...
                    if line and line[0].isdigit():
                        parts = line.split(':')
                        if len(parts) >= 3:
                            if current_iface: parsed_net.append(current_iface)
                            
                            # Parse State
                            state = "UNKNOWN"
                            if "state UP" in line: state = "UP"
                            elif "state DOWN" in line: state = "DOWN"
                            
                            current_iface = {
                                "ifname": parts[1].strip(),
                                "operstate": state,
                                "addr_info": []
                            }
                    
                    # inet 192.168.1.5/24 ...
                    if current_iface and "inet " in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            current_iface["addr_info"].append({
                                "local": parts[1],
                                "family": "inet"
                            })
                            
                if current_iface: parsed_net.append(current_iface)
                raw_network = parsed_net

            # Filter Network Interfaces
            # Exclude virtuals: lo, docker, veth, br, virbr, cni, flannel, cali, tun, tap
            ignored_prefixes = ["lo", "docker", "veth", "br", "virbr", "cni", "flannel", "cali", "tun", "tap", "kube"]
            info["network"] = [
                n for n in raw_network 
                if not any(n.get("ifname", "").startswith(p) for p in ignored_prefixes)
            ]

        except Exception as e:
            info["error"] = str(e)
            
        return info

    async def get_system_info(self) -> Dict[str, Any]:
        """
        Remote 'Tool' that runs a script or chain of commands to get JSON stats.
        Simulates the local SystemInfoService but over SSH.
        """
        # 1. OS Info
        cmd_os = "cat /etc/os-release"
        out_os, _, _ = await self.execute_command(cmd_os)
        
        # 2. Hostname
        cmd_host = "hostname"
        out_host, _, _ = await self.execute_command(cmd_host)
        
        # 3. Uptime
        cmd_up = "uptime -p || uptime"
        out_up, _, _ = await self.execute_command(cmd_up)

        # 4. Memory (Linux specific)
        cmd_mem = "free -m | grep Mem"
        out_mem, _, _ = await self.execute_command(cmd_mem)
        mem_percent = 0
        try:
            # Expected: Mem: total used free ...
            parts = out_mem.split()
            if len(parts) >= 3:
                total = int(parts[1])
                used = int(parts[2])
                if total > 0:
                    mem_percent = round((used / total) * 100, 1)
        except:
            pass

        # 5. Disk (Root partition)
        cmd_disk = "df -h / | tail -1"
        out_disk, _, _ = await self.execute_command(cmd_disk)
        disk_percent = 0
        try:
            # Expected: /dev/sda1 50G 20G 30G 40% /
            # We want the percentage, usually the 5th column (index 4)
            parts = out_disk.split()
            for part in parts:
                if part.endswith('%'):
                    disk_percent = int(part.strip('%'))
                    break
        except:
            pass
        
        # Parse simplified results
        os_name = "Unknown"
        for line in out_os.split('\n'):
            if line.startswith('PRETTY_NAME='):
                os_name = line.split('=')[1].strip('"')
                
        return {
            "os": {
                "system": os_name if os_name != "Unknown" else out_os.strip() or "Unknown",
                "hostname": out_host.strip(),
                "uptime": out_up.strip()
            },
            "hardware": {
                "cpu": {"usage_percent": 0}, # Placeholder, tough to get instant snapshot accurately without top/vmstat
                "memory": {"percent": mem_percent},
                "disk": {"percent": disk_percent}
            }
        }
