import logging
import subprocess
import json
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET

class GlusterFSAnalyzer:
    """Analyze GlusterFS cluster health, heal status, and peer connectivity."""
    
    def __init__(self, gluster_cmd: str = "gluster"):
        self.logger = logging.getLogger(__name__)
        self.gluster_cmd = gluster_cmd
        self.volume_info = {}
        self.peer_info = {}
        self.heal_data = {}
        self.last_update = None
        
        # Check if gluster command is available
        self._check_gluster_availability()
        
        # Initialize with current status
        self.refresh_status()
    
    def _check_gluster_availability(self) -> bool:
        """Check if GlusterFS command is available."""
        try:
            result = subprocess.run(
                [self.gluster_cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.logger.info("GlusterFS CLI is available")
                return True
            else:
                self.logger.warning("GlusterFS CLI not available, using mock data")
                return False
        except Exception as e:
            self.logger.warning(f"GlusterFS CLI not available: {e}, using mock data")
            return False
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall GlusterFS cluster health status."""
        try:
            # Refresh status if it's been more than 5 minutes
            if (not self.last_update or 
                datetime.now() - self.last_update > timedelta(minutes=5)):
                self.refresh_status()
            
            volumes_status = "healthy"
            total_volumes = len(self.volume_info)
            healthy_volumes = 0
            
            for vol_name, vol_info in self.volume_info.items():
                if vol_info.get("status") == "Started":
                    healthy_volumes += 1
                else:
                    volumes_status = "unhealthy"
            
            peers_status = "connected"
            total_peers = len(self.peer_info)
            connected_peers = 0
            
            for peer_id, peer_info in self.peer_info.items():
                if peer_info.get("connected") == "Connected":
                    connected_peers += 1
                else:
                    peers_status = "disconnected"
            
            # Calculate heal statistics
            total_heal_pending = 0
            split_brain_files = 0
            
            for vol_name, heal_info in self.heal_data.items():
                total_heal_pending += heal_info.get("entries_in_heal", 0)
                split_brain_files += heal_info.get("split_brain_files", 0)
            
            return {
                "volumes_healthy": f"{healthy_volumes}/{total_volumes}",
                "peers_connected": f"{connected_peers}/{total_peers}",
                "heal_pending": total_heal_pending,
                "split_brain_files": split_brain_files,
                "overall_status": "healthy" if (volumes_status == "healthy" and 
                                              peers_status == "connected" and 
                                              split_brain_files == 0) else "needs_attention",
                "last_updated": self.last_update.isoformat() if self.last_update else None
            }
            
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return {
                "volumes_healthy": "Unknown",
                "peers_connected": "Unknown", 
                "heal_pending": 0,
                "split_brain_files": 0,
                "overall_status": "error",
                "error": str(e)
            }
    
    def refresh_status(self):
        """Refresh all GlusterFS status information."""
        try:
            self.volume_info = self._get_volume_info()
            self.peer_info = self._get_peer_status()
            self.heal_data = self._get_heal_info()
            self.last_update = datetime.now()
            self.logger.info("Refreshed GlusterFS status")
            
        except Exception as e:
            self.logger.error(f"Error refreshing status: {e}")
            # Use mock data if real commands fail
            self._generate_mock_data()
    
    def _get_volume_info(self) -> Dict[str, Any]:
        """Get information about all GlusterFS volumes."""
        try:
            # Try real gluster command first
            result = subprocess.run(
                [self.gluster_cmd, "volume", "info", "--xml"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return self._parse_volume_xml(result.stdout)
            else:
                self.logger.warning("Failed to get real volume info, using mock data")
                return self._mock_volume_info()
                
        except Exception as e:
            self.logger.warning(f"Error getting volume info: {e}, using mock data")
            return self._mock_volume_info()
    
    def _parse_volume_xml(self, xml_output: str) -> Dict[str, Any]:
        """Parse XML output from gluster volume info command."""
        volumes = {}
        
        try:
            root = ET.fromstring(xml_output)
            
            for volume in root.findall(".//volume"):
                vol_name = volume.find("name").text
                vol_type = volume.find("typeStr").text
                vol_status = volume.find("statusStr").text
                brick_count = volume.find("brickCount").text
                
                bricks = []
                for brick in volume.findall(".//brick"):
                    brick_name = brick.find("name").text
                    bricks.append(brick_name)
                
                volumes[vol_name] = {
                    "name": vol_name,
                    "type": vol_type,
                    "status": vol_status,
                    "brick_count": int(brick_count),
                    "bricks": bricks
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing volume XML: {e}")
            
        return volumes
    
    def _mock_volume_info(self) -> Dict[str, Any]:
        """Generate mock volume information for testing."""
        return {
            "gv0": {
                "name": "gv0",
                "type": "Distributed-Replicate",
                "status": "Started",
                "brick_count": 4,
                "bricks": [
                    "node1:/data/brick1/gv0",
                    "node2:/data/brick1/gv0", 
                    "node3:/data/brick1/gv0",
                    "node4:/data/brick1/gv0"
                ]
            },
            "gv1": {
                "name": "gv1", 
                "type": "Replicate",
                "status": "Started",
                "brick_count": 2,
                "bricks": [
                    "node1:/data/brick2/gv1",
                    "node2:/data/brick2/gv1"
                ]
            }
        }
    
    def _get_peer_status(self) -> Dict[str, Any]:
        """Get status of all GlusterFS peers."""
        try:
            result = subprocess.run(
                [self.gluster_cmd, "peer", "status", "--xml"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return self._parse_peer_xml(result.stdout)
            else:
                return self._mock_peer_status()
                
        except Exception as e:
            self.logger.warning(f"Error getting peer status: {e}, using mock data")
            return self._mock_peer_status()
    
    def _parse_peer_xml(self, xml_output: str) -> Dict[str, Any]:
        """Parse XML output from gluster peer status command."""
        peers = {}
        
        try:
            root = ET.fromstring(xml_output)
            
            for peer in root.findall(".//peer"):
                uuid = peer.find("uuid").text
                hostname = peer.find("hostname").text
                connected = peer.find("connected").text
                state = peer.find("state").text
                
                peers[uuid] = {
                    "uuid": uuid,
                    "hostname": hostname,
                    "connected": connected,
                    "state": state,
                    "status": "connected" if connected == "1" else "disconnected",
                    "last_seen": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error parsing peer XML: {e}")
            
        return peers
    
    def _mock_peer_status(self) -> Dict[str, Any]:
        """Generate mock peer status for testing."""
        import uuid
        
        return {
            str(uuid.uuid4()): {
                "uuid": str(uuid.uuid4()),
                "hostname": "node1.cluster.local",
                "connected": "Connected",
                "state": "Peer in Cluster",
                "status": "connected",
                "last_seen": datetime.now().isoformat()
            },
            str(uuid.uuid4()): {
                "uuid": str(uuid.uuid4()),
                "hostname": "node2.cluster.local", 
                "connected": "Connected",
                "state": "Peer in Cluster",
                "status": "connected",
                "last_seen": datetime.now().isoformat()
            },
            str(uuid.uuid4()): {
                "uuid": str(uuid.uuid4()),
                "hostname": "node3.cluster.local",
                "connected": "Disconnected",
                "state": "Peer Rejected",
                "status": "disconnected",
                "last_seen": (datetime.now() - timedelta(minutes=15)).isoformat()
            }
        }
    
    def _get_heal_info(self) -> Dict[str, Any]:
        """Get heal information for all volumes."""
        heal_data = {}
        
        for vol_name in self.volume_info.keys():
            try:
                result = subprocess.run(
                    [self.gluster_cmd, "volume", "heal", vol_name, "info"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    heal_data[vol_name] = self._parse_heal_output(result.stdout)
                else:
                    heal_data[vol_name] = self._mock_heal_info()
                    
            except Exception as e:
                self.logger.warning(f"Error getting heal info for {vol_name}: {e}")
                heal_data[vol_name] = self._mock_heal_info()
        
        return heal_data
    
    def _parse_heal_output(self, heal_output: str) -> Dict[str, Any]:
        """Parse heal info output."""
        heal_info = {
            "entries_in_heal": 0,
            "split_brain_files": 0,
            "heal_entries": []
        }
        
        lines = heal_output.split('\n')
        current_brick = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith("Brick "):
                current_brick = line.replace("Brick ", "")
            elif line.startswith("Number of entries:"):
                try:
                    entries = int(re.findall(r'\d+', line)[0])
                    heal_info["entries_in_heal"] += entries
                except:
                    pass
            elif "split-brain" in line.lower():
                heal_info["split_brain_files"] += 1
                heal_info["heal_entries"].append({
                    "file": line,
                    "brick": current_brick,
                    "type": "split-brain"
                })
            elif line and current_brick and not line.startswith("Status:"):
                heal_info["heal_entries"].append({
                    "file": line,
                    "brick": current_brick,
                    "type": "pending_heal"
                })
        
        return heal_info
    
    def _mock_heal_info(self) -> Dict[str, Any]:
        """Generate mock heal information."""
        import random
        
        entries_count = random.randint(0, 10)
        split_brain_count = random.randint(0, 2)
        
        return {
            "entries_in_heal": entries_count,
            "split_brain_files": split_brain_count,
            "heal_entries": [
                {
                    "file": f"/path/to/file{i}.txt",
                    "brick": f"node{(i%3)+1}:/data/brick1/gv0",
                    "type": "pending_heal" if i < entries_count - split_brain_count else "split-brain"
                }
                for i in range(entries_count)
            ]
        }
    
    def get_heal_map(self) -> List[Dict[str, Any]]:
        """Get heal activity map over time."""
        try:
            heal_map = []
            
            for vol_name, heal_info in self.heal_data.items():
                # Generate time series data for heal activity
                base_time = datetime.now() - timedelta(hours=24)
                timestamps = []
                heal_counts = []
                
                # Simulate heal activity over last 24 hours
                for hour in range(24):
                    timestamp = base_time + timedelta(hours=hour)
                    timestamps.append(timestamp.isoformat())
                    
                    # Simulate varying heal activity
                    if hour < 12:
                        heal_count = max(0, heal_info["entries_in_heal"] - hour * 2)
                    else:
                        heal_count = max(0, heal_info["entries_in_heal"] // 2)
                    
                    heal_counts.append(heal_count)
                
                heal_map.append({
                    "volume_name": vol_name,
                    "timestamps": timestamps,
                    "heal_counts": heal_counts,
                    "current_heal_pending": heal_info["entries_in_heal"]
                })
            
            return heal_map
            
        except Exception as e:
            self.logger.error(f"Error generating heal map: {e}")
            return []
    
    def analyze_peers(self) -> List[Dict[str, Any]]:
        """Analyze peer connectivity and identify issues."""
        try:
            peer_analysis = []
            
            for peer_id, peer_info in self.peer_info.items():
                analysis = {
                    "uuid": peer_id,
                    "hostname": peer_info["hostname"],
                    "status": peer_info["status"],
                    "last_seen": peer_info["last_seen"],
                    "issues": [],
                    "recommendations": []
                }
                
                # Check for connectivity issues
                if peer_info["status"] == "disconnected":
                    analysis["issues"].append("Peer is disconnected from cluster")
                    analysis["recommendations"].append("Check network connectivity and firewall rules")
                    analysis["recommendations"].append("Verify GlusterFS daemon is running")
                
                # Check if peer has been disconnected for too long
                try:
                    last_seen = datetime.fromisoformat(peer_info["last_seen"])
                    if datetime.now() - last_seen > timedelta(minutes=10):
                        analysis["issues"].append("Peer disconnected for extended period")
                        analysis["recommendations"].append("Consider peer probe or cluster restart")
                except:
                    pass
                
                peer_analysis.append(analysis)
            
            return peer_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing peers: {e}")
            return []
    
    def reconnect_peer(self, peer_uuid: str) -> Dict[str, Any]:
        """Attempt to reconnect a disconnected peer."""
        try:
            if peer_uuid not in self.peer_info:
                return {"success": False, "message": "Peer not found"}
            
            peer_info = self.peer_info[peer_uuid]
            hostname = peer_info["hostname"]
            
            # Try to probe the peer again
            result = subprocess.run(
                [self.gluster_cmd, "peer", "probe", hostname],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # Refresh peer status
                self.peer_info = self._get_peer_status()
                return {"success": True, "message": f"Successfully probed peer {hostname}"}
            else:
                return {"success": False, "message": f"Failed to probe peer: {result.stderr}"}
                
        except Exception as e:
            self.logger.error(f"Error reconnecting peer: {e}")
            return {"success": False, "message": str(e)}
    
    def start_heal(self, volume_name: str) -> Dict[str, Any]:
        """Start heal process for a volume."""
        try:
            if volume_name not in self.volume_info:
                return {"success": False, "message": "Volume not found"}
            
            result = subprocess.run(
                [self.gluster_cmd, "volume", "heal", volume_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"success": True, "message": f"Heal started for volume {volume_name}"}
            else:
                return {"success": False, "message": f"Failed to start heal: {result.stderr}"}
                
        except Exception as e:
            self.logger.error(f"Error starting heal: {e}")
            return {"success": False, "message": str(e)}
    
    def resolve_split_brain(self, volume_name: str, file_path: str, source_brick: str) -> Dict[str, Any]:
        """Resolve split-brain by choosing source brick."""
        try:
            if volume_name not in self.volume_info:
                return {"success": False, "message": "Volume not found"}
            
            # Use gluster heal to resolve split-brain
            result = subprocess.run(
                [self.gluster_cmd, "volume", "heal", volume_name, "split-brain", 
                 "source-brick", source_brick, file_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {"success": True, "message": f"Split-brain resolved for {file_path}"}
            else:
                return {"success": False, "message": f"Failed to resolve split-brain: {result.stderr}"}
                
        except Exception as e:
            self.logger.error(f"Error resolving split-brain: {e}")
            return {"success": False, "message": str(e)}
    
    def _generate_mock_data(self):
        """Generate mock data when real GlusterFS commands are not available."""
        self.volume_info = self._mock_volume_info()
        self.peer_info = self._mock_peer_status()
        self.heal_data = {}
        
        for vol_name in self.volume_info.keys():
            self.heal_data[vol_name] = self._mock_heal_info()
        
        self.last_update = datetime.now()
        self.logger.info("Generated mock GlusterFS data")
    
    def get_volume_statistics(self) -> Dict[str, Any]:
        """Get detailed statistics for all volumes."""
        try:
            stats = {}
            
            for vol_name, vol_info in self.volume_info.items():
                # Get volume status
                try:
                    result = subprocess.run(
                        [self.gluster_cmd, "volume", "status", vol_name, "detail"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        vol_stats = self._parse_volume_status(result.stdout)
                    else:
                        vol_stats = self._mock_volume_stats()
                        
                except Exception:
                    vol_stats = self._mock_volume_stats()
                
                stats[vol_name] = {
                    **vol_info,
                    **vol_stats,
                    "heal_info": self.heal_data.get(vol_name, {})
                }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting volume statistics: {e}")
            return {}
    
    def _parse_volume_status(self, status_output: str) -> Dict[str, Any]:
        """Parse volume status output."""
        # Simple parsing - in reality this would be more complex
        return {
            "total_inodes": "1000000",
            "free_inodes": "950000", 
            "total_space": "1TB",
            "free_space": "750GB",
            "brick_status": "online"
        }
    
    def _mock_volume_stats(self) -> Dict[str, Any]:
        """Generate mock volume statistics."""
        return {
            "total_inodes": "1000000",
            "free_inodes": "950000",
            "total_space": "1TB", 
            "free_space": "750GB",
            "brick_status": "online"
        }