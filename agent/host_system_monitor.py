#!/usr/bin/env python3
"""
Host System Monitor for Kubernetes AI Agent
Executes commands on the host node to collect system and GlusterFS statistics
"""

import logging
import subprocess
import json
import re
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class SystemStats:
    """Container for system statistics"""
    cpu_usage: float
    memory_usage: Dict[str, int]
    disk_usage: List[Dict[str, Any]]
    network_stats: Dict[str, Any]
    process_count: int
    load_average: List[float]
    uptime: float


@dataclass
class GlusterFSStats:
    """Container for GlusterFS statistics"""
    volume_info: Dict[str, Any]
    peer_status: Dict[str, Any]
    heal_info: Dict[str, Any]
    brick_status: Dict[str, Any]
    quota_info: Dict[str, Any]


class HostSystemMonitor:
    """Monitor host system statistics from within a privileged container"""
    
    def __init__(self, use_host_exec: bool = True):
        self.logger = logging.getLogger(__name__)
        self.use_host_exec = use_host_exec and os.path.exists("/usr/local/bin/host-exec")
        self.gluster_exec = "/usr/local/bin/gluster-exec" if os.path.exists("/usr/local/bin/gluster-exec") else "gluster"
        
        if self.use_host_exec:
            self.logger.info("Using host namespace execution for system monitoring")
        else:
            self.logger.info("Using container-native execution for system monitoring")
    
    def _execute_command(self, command: List[str], use_host: bool = True, timeout: int = 30) -> Optional[str]:
        """Execute a command, optionally in host namespace"""
        try:
            if use_host and self.use_host_exec:
                cmd = ["/usr/local/bin/host-exec"] + command
            else:
                cmd = command
            
            self.logger.debug(f"Executing command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                self.logger.warning(f"Command failed: {' '.join(cmd)}, return code: {result.returncode}")
                self.logger.debug(f"Error output: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out: {' '.join(command)}")
            return None
        except Exception as e:
            self.logger.error(f"Error executing command {' '.join(command)}: {e}")
            return None
    
    def get_cpu_stats(self) -> Dict[str, float]:
        """Get CPU usage statistics"""
        stats = {}
        
        # Get CPU usage from /proc/stat
        output = self._execute_command(["cat", "/proc/stat"])
        if output:
            lines = output.split('\n')
            cpu_line = lines[0] if lines else ""
            if cpu_line.startswith('cpu '):
                values = [int(x) for x in cpu_line.split()[1:]]
                total = sum(values)
                idle = values[3] if len(values) > 3 else 0
                stats['cpu_usage_percent'] = ((total - idle) / total * 100) if total > 0 else 0
        
        # Get load average
        output = self._execute_command(["cat", "/proc/loadavg"])
        if output:
            load_parts = output.split()
            if len(load_parts) >= 3:
                stats.update({
                    'load_1min': float(load_parts[0]),
                    'load_5min': float(load_parts[1]),
                    'load_15min': float(load_parts[2])
                })
        
        return stats
    
    def get_memory_stats(self) -> Dict[str, int]:
        """Get memory usage statistics"""
        stats = {}
        
        output = self._execute_command(["cat", "/proc/meminfo"])
        if output:
            for line in output.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().replace(' kB', '')
                    try:
                        stats[key] = int(value) * 1024  # Convert kB to bytes
                    except ValueError:
                        continue
        
        return stats
    
    def get_disk_stats(self) -> List[Dict[str, Any]]:
        """Get disk usage statistics"""
        disks = []
        
        # Get disk usage with df
        output = self._execute_command(["df", "-h", "--output=source,fstype,size,used,avail,pcent,target"])
        if output:
            lines = output.split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 7:
                        disks.append({
                            'device': parts[0],
                            'filesystem': parts[1],
                            'size': parts[2],
                            'used': parts[3],
                            'available': parts[4],
                            'usage_percent': parts[5],
                            'mount_point': parts[6]
                        })
        
        # Get I/O statistics
        output = self._execute_command(["cat", "/proc/diskstats"])
        if output:
            for line in output.split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 14:
                        device = parts[2]
                        # Find corresponding disk entry
                        for disk in disks:
                            if device in disk.get('device', ''):
                                disk.update({
                                    'reads_completed': int(parts[3]),
                                    'reads_merged': int(parts[4]),
                                    'sectors_read': int(parts[5]),
                                    'read_time_ms': int(parts[6]),
                                    'writes_completed': int(parts[7]),
                                    'writes_merged': int(parts[8]),
                                    'sectors_written': int(parts[9]),
                                    'write_time_ms': int(parts[10])
                                })
                                break
        
        return disks
    
    def get_network_stats(self) -> Dict[str, Any]:
        """Get network interface statistics"""
        interfaces = {}
        
        output = self._execute_command(["cat", "/proc/net/dev"])
        if output:
            lines = output.split('\n')[2:]  # Skip headers
            for line in lines:
                if ':' in line:
                    interface, stats = line.split(':', 1)
                    interface = interface.strip()
                    stats_values = [int(x) for x in stats.split() if x.isdigit()]
                    
                    if len(stats_values) >= 16:
                        interfaces[interface] = {
                            'rx_bytes': stats_values[0],
                            'rx_packets': stats_values[1],
                            'rx_errors': stats_values[2],
                            'rx_dropped': stats_values[3],
                            'tx_bytes': stats_values[8],
                            'tx_packets': stats_values[9],
                            'tx_errors': stats_values[10],
                            'tx_dropped': stats_values[11]
                        }
        
        return interfaces
    
    def get_process_stats(self) -> Dict[str, int]:
        """Get process statistics"""
        stats = {'total_processes': 0, 'running_processes': 0, 'sleeping_processes': 0}
        
        output = self._execute_command(["ps", "axo", "stat", "--no-headers"])
        if output:
            states = output.split('\n')
            stats['total_processes'] = len([s for s in states if s.strip()])
            stats['running_processes'] = len([s for s in states if s.startswith('R')])
            stats['sleeping_processes'] = len([s for s in states if s.startswith('S')])
        
        return stats
    
    def get_glusterfs_volume_info(self) -> Dict[str, Any]:
        """Get GlusterFS volume information"""
        volumes = {}
        
        output = self._execute_command([self.gluster_exec, "volume", "info", "--xml"], use_host=True)
        if output:
            try:
                # Parse XML output (simplified)
                volume_lines = [line for line in output.split('\n') if 'Volume Name:' in line or 'Status:' in line or 'Number of Bricks:' in line]
                current_volume = None
                
                for line in volume_lines:
                    if 'Volume Name:' in line:
                        current_volume = line.split(':', 1)[1].strip()
                        volumes[current_volume] = {}
                    elif current_volume and 'Status:' in line:
                        volumes[current_volume]['status'] = line.split(':', 1)[1].strip()
                    elif current_volume and 'Number of Bricks:' in line:
                        volumes[current_volume]['brick_count'] = line.split(':', 1)[1].strip()
                        
            except Exception as e:
                self.logger.error(f"Error parsing GlusterFS volume info: {e}")
        
        return volumes
    
    def get_glusterfs_peer_status(self) -> Dict[str, Any]:
        """Get GlusterFS peer status"""
        peers = {}
        
        output = self._execute_command([self.gluster_exec, "peer", "status"], use_host=True)
        if output:
            try:
                lines = output.split('\n')
                current_peer = None
                
                for line in lines:
                    if 'Hostname:' in line:
                        current_peer = line.split(':', 1)[1].strip()
                        peers[current_peer] = {}
                    elif current_peer and 'State:' in line:
                        peers[current_peer]['state'] = line.split(':', 1)[1].strip()
                        
            except Exception as e:
                self.logger.error(f"Error parsing GlusterFS peer status: {e}")
        
        return peers
    
    def get_system_stats(self) -> SystemStats:
        """Get comprehensive system statistics"""
        try:
            cpu_stats = self.get_cpu_stats()
            memory_stats = self.get_memory_stats()
            disk_stats = self.get_disk_stats()
            network_stats = self.get_network_stats()
            process_stats = self.get_process_stats()
            
            return SystemStats(
                cpu_usage=cpu_stats.get('cpu_usage_percent', 0.0),
                memory_usage=memory_stats,
                disk_usage=disk_stats,
                network_stats=network_stats,
                process_count=process_stats.get('total_processes', 0),
                load_average=[
                    cpu_stats.get('load_1min', 0.0),
                    cpu_stats.get('load_5min', 0.0),
                    cpu_stats.get('load_15min', 0.0)
                ],
                uptime=0.0  # TODO: Implement uptime calculation
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting system stats: {e}")
            return SystemStats(0.0, {}, [], {}, 0, [0.0, 0.0, 0.0], 0.0)
    
    def get_glusterfs_stats(self) -> GlusterFSStats:
        """Get comprehensive GlusterFS statistics"""
        try:
            volume_info = self.get_glusterfs_volume_info()
            peer_status = self.get_glusterfs_peer_status()
            
            return GlusterFSStats(
                volume_info=volume_info,
                peer_status=peer_status,
                heal_info={},  # TODO: Implement heal info
                brick_status={},  # TODO: Implement brick status
                quota_info={}  # TODO: Implement quota info
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting GlusterFS stats: {e}")
            return GlusterFSStats({}, {}, {}, {}, {})
    
    def collect_all_stats(self) -> Dict[str, Any]:
        """Collect all system and GlusterFS statistics"""
        timestamp = datetime.now().isoformat()
        
        system_stats = self.get_system_stats()
        glusterfs_stats = self.get_glusterfs_stats()
        
        return {
            'timestamp': timestamp,
            'system': {
                'cpu_usage_percent': system_stats.cpu_usage,
                'memory': system_stats.memory_usage,
                'disks': system_stats.disk_usage,
                'network': system_stats.network_stats,
                'processes': system_stats.process_count,
                'load_average': system_stats.load_average,
                'uptime': system_stats.uptime
            },
            'glusterfs': {
                'volumes': glusterfs_stats.volume_info,
                'peers': glusterfs_stats.peer_status,
                'heal_info': glusterfs_stats.heal_info,
                'brick_status': glusterfs_stats.brick_status,
                'quota_info': glusterfs_stats.quota_info
            }
        }


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    monitor = HostSystemMonitor()
    
    stats = monitor.collect_all_stats()
    print(json.dumps(stats, indent=2))
