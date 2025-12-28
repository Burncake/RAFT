"""
Simple file-based key-value store for RAFT committed logs
"""
import json
import os
import threading
from typing import Optional, Dict


class KeyValueStore:
    """Thread-safe file-based key-value storage"""
    
    def __init__(self, node_id: str, data_dir: str = "data"):
        """
        Initialize the key-value store
        
        Args:
            node_id: Unique identifier for this node
            data_dir: Directory to store data files
        """
        self.node_id = node_id
        self.data_dir = data_dir
        self.db_file = os.path.join(data_dir, f"node_{node_id}_db.json")
        self.lock = threading.RLock()
        self.data: Dict[str, str] = {}
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Load existing data
        self._load()
    
    def _load(self):
        """Load data from disk"""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r') as f:
                    self.data = json.load(f)
                print(f"[KVStore-{self.node_id}] Loaded {len(self.data)} entries from disk")
        except Exception as e:
            print(f"[KVStore-{self.node_id}] Error loading data: {e}")
            self.data = {}
    
    def _save(self):
        """Save data to disk"""
        try:
            with open(self.db_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[KVStore-{self.node_id}] Error saving data: {e}")
    
    def set(self, key: str, value: str) -> bool:
        """
        Set a key-value pair
        
        Args:
            key: Key to set
            value: Value to store
            
        Returns:
            True if successful
        """
        with self.lock:
            self.data[key] = value
            self._save()
            print(f"[KVStore-{self.node_id}] SET {key}={value}")
            return True
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value for a key
        
        Args:
            key: Key to retrieve
            
        Returns:
            Value if key exists, None otherwise
        """
        with self.lock:
            value = self.data.get(key)
            print(f"[KVStore-{self.node_id}] GET {key}={value}")
            return value
    
    def delete(self, key: str) -> bool:
        """
        Delete a key
        
        Args:
            key: Key to delete
            
        Returns:
            True if key existed and was deleted
        """
        with self.lock:
            if key in self.data:
                del self.data[key]
                self._save()
                print(f"[KVStore-{self.node_id}] DELETE {key}")
                return True
            return False
    
    def apply_command(self, command: str) -> str:
        """
        Apply a command to the store
        
        Args:
            command: Command string in format "SET key value" or "GET key" or "DELETE key"
            
        Returns:
            Result message
        """
        parts = command.split(maxsplit=2)
        if not parts:
            return "ERROR: Empty command"
        
        cmd = parts[0].upper()
        
        if cmd == "SET":
            if len(parts) < 3:
                return "ERROR: SET requires key and value"
            key, value = parts[1], parts[2]
            self.set(key, value)
            return f"OK: SET {key}={value}"
        
        elif cmd == "GET":
            if len(parts) < 2:
                return "ERROR: GET requires key"
            key = parts[1]
            value = self.get(key)
            if value is not None:
                return f"OK: {value}"
            return f"ERROR: Key '{key}' not found"
        
        elif cmd == "DELETE":
            if len(parts) < 2:
                return "ERROR: DELETE requires key"
            key = parts[1]
            if self.delete(key):
                return f"OK: Deleted {key}"
            return f"ERROR: Key '{key}' not found"
        
        else:
            return f"ERROR: Unknown command '{cmd}'"
    
    def get_all(self) -> Dict[str, str]:
        """Get all key-value pairs"""
        with self.lock:
            return self.data.copy()
    
    def clear(self):
        """Clear all data (for testing)"""
        with self.lock:
            self.data = {}
            self._save()
            print(f"[KVStore-{self.node_id}] Cleared all data")
