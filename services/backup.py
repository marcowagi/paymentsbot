"""
Backup service for the Telegram Finance Bot
Creates ZIP backups of database and reports
"""

import logging
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from config import BACKUPS_DIR, DATA_DIR, REPORTS_DIR

logger = logging.getLogger(__name__)

class BackupService:
    def __init__(self):
        self.backups_dir = BACKUPS_DIR
        self.backups_dir.mkdir(exist_ok=True, parents=True)
    
    async def create_full_backup(self) -> Path:
        """Create a full backup including database and reports"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"full_backup_{timestamp}.zip"
        backup_path = self.backups_dir / backup_filename
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database file
                db_file = DATA_DIR / "db.sqlite3"
                if db_file.exists():
                    zipf.write(db_file, f"database/db.sqlite3")
                    logger.info("Added database to backup")
                
                # Add all reports
                if REPORTS_DIR.exists():
                    for report_file in REPORTS_DIR.glob("*"):
                        if report_file.is_file():
                            zipf.write(report_file, f"reports/{report_file.name}")
                    logger.info("Added reports to backup")
                
                # Add config files (without sensitive data)
                config_files = [
                    DATA_DIR.parent / ".env.example",
                    DATA_DIR.parent / "requirements.txt"
                ]
                
                for config_file in config_files:
                    if config_file.exists():
                        zipf.write(config_file, f"config/{config_file.name}")
                
            logger.info(f"Created full backup: {backup_filename}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            # Clean up partial backup file
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    async def create_database_backup(self) -> Path:
        """Create a backup of just the database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"database_backup_{timestamp}.zip"
        backup_path = self.backups_dir / backup_filename
        
        try:
            db_file = DATA_DIR / "db.sqlite3"
            if not db_file.exists():
                raise FileNotFoundError("Database file not found")
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(db_file, "db.sqlite3")
            
            logger.info(f"Created database backup: {backup_filename}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating database backup: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    async def create_reports_backup(self) -> Path:
        """Create a backup of all reports"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"reports_backup_{timestamp}.zip"
        backup_path = self.backups_dir / backup_filename
        
        try:
            if not REPORTS_DIR.exists() or not any(REPORTS_DIR.iterdir()):
                raise FileNotFoundError("No reports found to backup")
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for report_file in REPORTS_DIR.glob("*"):
                    if report_file.is_file():
                        zipf.write(report_file, report_file.name)
            
            logger.info(f"Created reports backup: {backup_filename}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating reports backup: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise
    
    def list_backups(self) -> list[Path]:
        """List all backup files"""
        try:
            backups = list(self.backups_dir.glob("*.zip"))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return backups
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    def cleanup_old_backups(self, keep_count: int = 10):
        """Keep only the most recent backups, delete older ones"""
        try:
            backups = self.list_backups()
            
            if len(backups) > keep_count:
                for backup in backups[keep_count:]:
                    backup.unlink()
                    logger.info(f"Deleted old backup: {backup.name}")
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    def get_backup_info(self, backup_path: Path) -> dict:
        """Get information about a backup file"""
        try:
            stat = backup_path.stat()
            
            # Get contents info
            contents = []
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                for file_info in zipf.filelist:
                    contents.append({
                        'filename': file_info.filename,
                        'size': file_info.file_size,
                        'compressed_size': file_info.compress_size
                    })
            
            return {
                'filename': backup_path.name,
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'contents': contents
            }
        except Exception as e:
            logger.error(f"Error getting backup info: {e}")
            return {}
    
    async def restore_from_backup(self, backup_path: Path, target_dir: Path = None) -> bool:
        """Restore from a backup file (basic implementation)"""
        if target_dir is None:
            target_dir = DATA_DIR
        
        try:
            # Create backup of current data before restore
            current_backup = await self.create_full_backup()
            logger.info(f"Created safety backup before restore: {current_backup.name}")
            
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(target_dir)
            
            logger.info(f"Restored from backup: {backup_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return False