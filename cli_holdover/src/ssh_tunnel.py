import subprocess
import threading
import time
import socket
from typing import Optional, Dict, Any
from contextlib import contextmanager
from dataclasses import dataclass

@dataclass
class SSHConfig:
    host: str
    port: int = 22
    username: str = None
    key_file: str = None
    password: str = None
    local_port: int = None
    remote_port: int = 11434
    remote_host: str = "localhost"

class SSHTunnel:
    def __init__(self, ssh_config: SSHConfig):
        self.config = ssh_config
        self.process: Optional[subprocess.Popen] = None
        self.local_port = ssh_config.local_port or self._find_free_port()
        self._tunnel_ready = threading.Event()
    
    def _find_free_port(self) -> int:
        """Find a free local port for the tunnel"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def start(self) -> bool:
        """Start the SSH tunnel"""
        if self.is_active():
            return True
        
        # Build SSH command
        ssh_cmd = [
            "ssh",
            "-N",  # Don't execute remote command
            "-L", f"{self.local_port}:{self.config.remote_host}:{self.config.remote_port}",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR"
        ]
        
        # Add authentication options
        if self.config.key_file:
            ssh_cmd.extend(["-i", self.config.key_file])
        
        # Add user and host
        if self.config.username:
            ssh_cmd.append(f"{self.config.username}@{self.config.host}")
        else:
            ssh_cmd.append(self.config.host)
        
        # Add port if not default
        if self.config.port != 22:
            ssh_cmd.extend(["-p", str(self.config.port)])
        
        try:
            # Start SSH tunnel process
            self.process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )
            
            # Wait a bit for tunnel to establish
            time.sleep(2)
            
            # Check if process is still running (tunnel established)
            if self.process.poll() is None:
                # Test the tunnel by attempting to connect
                if self._test_tunnel():
                    self._tunnel_ready.set()
                    return True
                else:
                    self.stop()
                    return False
            else:
                # Process exited, tunnel failed
                stderr_output = self.process.stderr.read().decode('utf-8')
                print(f"SSH tunnel failed: {stderr_output}")
                return False
                
        except Exception as e:
            print(f"Error starting SSH tunnel: {e}")
            return False
    
    def _test_tunnel(self) -> bool:
        """Test if the tunnel is working by attempting to connect"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                result = s.connect_ex(('localhost', self.local_port))
                return result == 0
        except Exception:
            return False
    
    def stop(self) -> None:
        """Stop the SSH tunnel"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        self._tunnel_ready.clear()
    
    def is_active(self) -> bool:
        """Check if the tunnel is active"""
        return self.process is not None and self.process.poll() is None
    
    def get_local_url(self) -> str:
        """Get the local URL to connect through the tunnel"""
        return f"http://localhost:{self.local_port}"
    
    def wait_ready(self, timeout: int = 10) -> bool:
        """Wait for tunnel to be ready"""
        return self._tunnel_ready.wait(timeout)

@contextmanager
def ssh_tunnel(ssh_config: SSHConfig):
    """Context manager for SSH tunnel"""
    tunnel = SSHTunnel(ssh_config)
    try:
        if tunnel.start():
            yield tunnel
        else:
            raise ConnectionError("Failed to establish SSH tunnel")
    finally:
        tunnel.stop()

class SSHTunnelManager:
    def __init__(self):
        self.active_tunnels: Dict[str, SSHTunnel] = {}
    
    def create_tunnel(self, name: str, ssh_config: SSHConfig) -> Optional[SSHTunnel]:
        """Create and start a new SSH tunnel"""
        if name in self.active_tunnels:
            # Return existing tunnel if it's still active
            tunnel = self.active_tunnels[name]
            if tunnel.is_active():
                return tunnel
            else:
                # Clean up dead tunnel
                del self.active_tunnels[name]
        
        tunnel = SSHTunnel(ssh_config)
        if tunnel.start():
            self.active_tunnels[name] = tunnel
            return tunnel
        return None
    
    def get_tunnel(self, name: str) -> Optional[SSHTunnel]:
        """Get an existing tunnel"""
        tunnel = self.active_tunnels.get(name)
        if tunnel and tunnel.is_active():
            return tunnel
        elif tunnel:
            # Clean up dead tunnel
            del self.active_tunnels[name]
        return None
    
    def close_tunnel(self, name: str) -> None:
        """Close a specific tunnel"""
        if name in self.active_tunnels:
            self.active_tunnels[name].stop()
            del self.active_tunnels[name]
    
    def close_all(self) -> None:
        """Close all active tunnels"""
        for tunnel in self.active_tunnels.values():
            tunnel.stop()
        self.active_tunnels.clear()
    
    def list_active(self) -> Dict[str, str]:
        """List all active tunnels"""
        active = {}
        for name, tunnel in list(self.active_tunnels.items()):
            if tunnel.is_active():
                active[name] = tunnel.get_local_url()
            else:
                # Clean up dead tunnel
                del self.active_tunnels[name]
        return active