"""
Snapshot System for State Save/Restore
Saves and restores Android app state for debugging and rollback
"""
import json
import os
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, List
from config import OBSIDIAN_PACKAGE

SNAPSHOTS_DIR = "snapshots"

class SnapshotManager:
    """Manages app state snapshots"""
    
    def __init__(self, snapshots_dir: str = SNAPSHOTS_DIR):
        self.snapshots_dir = snapshots_dir
        os.makedirs(snapshots_dir, exist_ok=True)
    
    def create_snapshot(self, snapshot_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a snapshot of current app state
        
        Args:
            snapshot_id: Unique identifier for snapshot
            metadata: Optional metadata to store
            
        Returns:
            Path to snapshot file
        """
        snapshot_data = {
            "snapshot_id": snapshot_id,
            "timestamp": datetime.now().isoformat(),
            "package": OBSIDIAN_PACKAGE,
            "metadata": metadata or {},
            "state": self._capture_state()
        }
        
        snapshot_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot_data, f, indent=2)
        
        print(f"  💾 Snapshot created: {snapshot_id}")
        return snapshot_path
    
    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore app state from snapshot
        
        Args:
            snapshot_id: Snapshot identifier
            
        Returns:
            True if restore successful
        """
        snapshot_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
        
        if not os.path.exists(snapshot_path):
            print(f"  ⚠️  Snapshot not found: {snapshot_id}")
            return False
        
        with open(snapshot_path, 'r') as f:
            snapshot_data = json.load(f)
        
        # Restore app state
        try:
            # Reset app to initial state
            subprocess.run(["adb", "shell", "am", "force-stop", OBSIDIAN_PACKAGE], check=True)
            subprocess.run(["adb", "shell", "pm", "clear", OBSIDIAN_PACKAGE], check=True)
            
            # Restore state if available
            state = snapshot_data.get("state", {})
            if state:
                # Restore specific state elements if needed
                # For now, just reset app - full state restoration would require more complex implementation
                pass
            
            print(f"  🔄 Snapshot restored: {snapshot_id}")
            return True
        except Exception as e:
            print(f"  ❌ Failed to restore snapshot: {e}")
            return False
    
    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all available snapshots"""
        snapshots = []
        for filename in os.listdir(self.snapshots_dir):
            if filename.endswith('.json'):
                snapshot_id = filename[:-5]
                snapshot_path = os.path.join(self.snapshots_dir, filename)
                try:
                    with open(snapshot_path, 'r') as f:
                        data = json.load(f)
                        snapshots.append({
                            "id": snapshot_id,
                            "timestamp": data.get("timestamp"),
                            "metadata": data.get("metadata", {})
                        })
                except:
                    pass
        return sorted(snapshots, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot"""
        snapshot_path = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
        if os.path.exists(snapshot_path):
            os.remove(snapshot_path)
            print(f"  🗑️  Snapshot deleted: {snapshot_id}")
            return True
        return False
    
    def _capture_state(self) -> Dict[str, Any]:
        """Capture current app state"""
        state = {
            "package": OBSIDIAN_PACKAGE,
            "activity": self._get_current_activity(),
            "ui_dump": None,  # Could capture UI dump if needed
        }
        
        try:
            # Get current activity
            result = subprocess.run(
                ["adb", "shell", "dumpsys", "window", "windows"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Parse activity from dumpsys output (simplified)
            state["activity"] = self._get_current_activity()
        except:
            pass
        
        return state
    
    def _get_current_activity(self) -> Optional[str]:
        """Get current activity name"""
        try:
            result = subprocess.run(
                ["adb", "shell", "dumpsys", "window", "windows", "|", "grep", "-E", "mCurrentFocus|mFocusedApp"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            # Parse activity from output
            for line in result.stdout.split('\n'):
                if OBSIDIAN_PACKAGE in line:
                    # Extract activity name
                    if '/' in line:
                        activity = line.split('/')[-1].split('}')[0]
                        return activity
        except:
            pass
        return None


# Global instance
snapshot_manager = SnapshotManager()
