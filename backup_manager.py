#!/usr/bin/env python3
"""
Automated Backup System for Bitcoin Analyzer
Ensures data persistence and recovery capabilities
"""
import os
import time
import shutil
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import gzip

logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automated backups for database and cache files"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Backup configuration
        self.config = {
            'max_backups': 10,  # Keep last 10 backups
            'backup_interval': 3600,  # Backup every hour
            'compress': True,  # Compress backups
            'include_files': [
                'bitcoin_data.db',
                'bitcoin_data.db-wal',
                'bitcoin_data.db-shm',
                'cache.json',
                'config.py',
                'CLAUDE.md'
            ]
        }
        
        self.last_backup = 0
        self.backup_history = []
        
    def create_backup(self) -> Dict:
        """Create a backup of critical files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}"
            backup_path = self.backup_dir / backup_name
            backup_path.mkdir(exist_ok=True)
            
            backup_info = {
                'timestamp': int(time.time()),
                'name': backup_name,
                'files': [],
                'size': 0,
                'compressed': self.config['compress']
            }
            
            # Backup each configured file
            for file_name in self.config['include_files']:
                if os.path.exists(file_name):
                    try:
                        dest = backup_path / file_name
                        
                        if self.config['compress'] and file_name.endswith('.db'):
                            # Compress database files
                            self._compress_file(file_name, f"{dest}.gz")
                            backup_info['files'].append(f"{file_name}.gz")
                            backup_info['size'] += os.path.getsize(f"{dest}.gz")
                        else:
                            # Copy other files directly
                            shutil.copy2(file_name, dest)
                            backup_info['files'].append(file_name)
                            backup_info['size'] += os.path.getsize(dest)
                            
                    except Exception as e:
                        logger.error(f"Failed to backup {file_name}: {e}")
                        
            # Create backup metadata
            metadata = {
                'created': timestamp,
                'timestamp': backup_info['timestamp'],
                'files': backup_info['files'],
                'size_bytes': backup_info['size'],
                'size_mb': round(backup_info['size'] / 1024 / 1024, 2),
                'database_stats': self._get_database_stats()
            }
            
            with open(backup_path / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)
                
            # Update backup history
            self.backup_history.append(backup_info)
            self.last_backup = backup_info['timestamp']
            
            # Clean old backups
            self._clean_old_backups()
            
            logger.info(f"Backup created: {backup_name} ({backup_info['size']/1024:.1f}KB)")
            return backup_info
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return {'error': str(e)}
            
    def _compress_file(self, source: str, dest: str):
        """Compress a file using gzip"""
        with open(source, 'rb') as f_in:
            with gzip.open(dest, 'wb', compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
                
    def _get_database_stats(self) -> Dict:
        """Get database statistics for backup metadata"""
        try:
            conn = sqlite3.connect('bitcoin_data.db', timeout=5)
            cursor = conn.cursor()
            
            stats = {}
            tables = ['price_data', 'whale_movements', 'mstr_data', 'mempool_stats']
            
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    stats[table] = count
                except:
                    stats[table] = 0
                    
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
            
    def _clean_old_backups(self):
        """Remove old backups beyond max_backups limit"""
        try:
            backups = sorted([d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith('backup_')])
            
            if len(backups) > self.config['max_backups']:
                for old_backup in backups[:-self.config['max_backups']]:
                    shutil.rmtree(old_backup)
                    logger.info(f"Removed old backup: {old_backup.name}")
                    
        except Exception as e:
            logger.error(f"Failed to clean old backups: {e}")
            
    def restore_backup(self, backup_name: str) -> bool:
        """Restore from a specific backup"""
        try:
            backup_path = self.backup_dir / backup_name
            
            if not backup_path.exists():
                logger.error(f"Backup not found: {backup_name}")
                return False
                
            # Read metadata
            with open(backup_path / 'metadata.json', 'r') as f:
                metadata = json.load(f)
                
            # Restore each file
            for file_name in metadata['files']:
                source = backup_path / file_name
                
                if file_name.endswith('.gz'):
                    # Decompress database files
                    dest = file_name[:-3]  # Remove .gz extension
                    with gzip.open(source, 'rb') as f_in:
                        with open(dest, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                else:
                    # Copy other files directly
                    shutil.copy2(source, file_name)
                    
            logger.info(f"Restored from backup: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
            
    def list_backups(self) -> List[Dict]:
        """List all available backups"""
        backups = []
        
        try:
            for backup_dir in sorted(self.backup_dir.iterdir(), reverse=True):
                if backup_dir.is_dir() and backup_dir.name.startswith('backup_'):
                    metadata_path = backup_dir / 'metadata.json'
                    
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            backups.append({
                                'name': backup_dir.name,
                                'created': metadata['created'],
                                'size_mb': metadata['size_mb'],
                                'files': len(metadata['files']),
                                'database_records': sum(metadata.get('database_stats', {}).values())
                            })
                            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            
        return backups
        
    def get_backup_status(self) -> Dict:
        """Get current backup system status"""
        backups = self.list_backups()
        
        return {
            'enabled': True,
            'last_backup': self.last_backup,
            'time_since_backup': int(time.time() - self.last_backup) if self.last_backup else None,
            'next_backup': self.last_backup + self.config['backup_interval'] if self.last_backup else int(time.time()),
            'total_backups': len(backups),
            'max_backups': self.config['max_backups'],
            'backup_size_mb': sum(b['size_mb'] for b in backups),
            'recent_backups': backups[:5]
        }
        
    async def start_auto_backup(self):
        """Start automatic backup process"""
        logger.info("Starting automatic backup system")
        
        while True:
            try:
                # Check if backup is needed
                if time.time() - self.last_backup >= self.config['backup_interval']:
                    self.create_backup()
                    
                # Wait before next check (5 minutes)
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Auto-backup error: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute
                
    def verify_backup(self, backup_name: str) -> Dict:
        """Verify backup integrity"""
        try:
            backup_path = self.backup_dir / backup_name
            
            if not backup_path.exists():
                return {'valid': False, 'error': 'Backup not found'}
                
            # Check metadata
            metadata_path = backup_path / 'metadata.json'
            if not metadata_path.exists():
                return {'valid': False, 'error': 'Metadata missing'}
                
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            # Verify all files exist
            missing_files = []
            for file_name in metadata['files']:
                if not (backup_path / file_name).exists():
                    missing_files.append(file_name)
                    
            if missing_files:
                return {
                    'valid': False,
                    'error': 'Missing files',
                    'missing': missing_files
                }
                
            # Check file sizes
            actual_size = sum(
                (backup_path / f).stat().st_size 
                for f in metadata['files']
            )
            
            if abs(actual_size - metadata['size_bytes']) > 1000:  # Allow 1KB difference
                return {
                    'valid': False,
                    'error': 'Size mismatch',
                    'expected': metadata['size_bytes'],
                    'actual': actual_size
                }
                
            return {
                'valid': True,
                'files': len(metadata['files']),
                'size_mb': metadata['size_mb'],
                'created': metadata['created']
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}

# Singleton instance
_backup_manager = None

def get_backup_manager() -> BackupManager:
    """Get or create backup manager instance"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager

async def start_backup_service():
    """Start the backup service"""
    manager = get_backup_manager()
    await manager.start_auto_backup()

if __name__ == "__main__":
    # Test backup system
    manager = get_backup_manager()
    
    print("🔐 BACKUP SYSTEM TEST")
    print("-" * 40)
    
    # Create a backup
    print("Creating backup...")
    backup = manager.create_backup()
    
    if 'error' not in backup:
        print(f"✅ Backup created: {backup['name']}")
        print(f"   Files: {len(backup['files'])}")
        print(f"   Size: {backup['size']/1024:.1f}KB")
    else:
        print(f"❌ Backup failed: {backup['error']}")
    
    # List backups
    print("\n📁 Available Backups:")
    for b in manager.list_backups()[:5]:
        print(f"  • {b['name']} - {b['size_mb']:.1f}MB ({b['database_records']} records)")
    
    # Get status
    status = manager.get_backup_status()
    print(f"\n📊 Backup Status:")
    print(f"  Total backups: {status['total_backups']}")
    print(f"  Total size: {status['backup_size_mb']:.1f}MB")
    
    if backup and 'name' in backup:
        # Verify the backup
        print(f"\n🔍 Verifying backup {backup['name']}...")
        verification = manager.verify_backup(backup['name'])
        if verification['valid']:
            print(f"✅ Backup is valid")
        else:
            print(f"❌ Backup verification failed: {verification.get('error')}")