import sqlite3
import logging
import os
from datetime import datetime, timedelta

class ProcessedMeetingsDB:
    def __init__(self, db_path):
        """Initialize the database manager for tracking processed meetings."""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure the database directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Table for processed meetings
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_meetings (
                        meeting_id TEXT PRIMARY KEY,
                        meeting_title TEXT,
                        meeting_date TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        notion_page_id TEXT,
                        action_count INTEGER DEFAULT 0,
                        sync_status TEXT DEFAULT 'completed'
                    )
                ''')
                
                # Table for sync statistics
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sync_stats (
                        sync_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sync_start TIMESTAMP,
                        sync_end TIMESTAMP,
                        meetings_processed INTEGER DEFAULT 0,
                        actions_created INTEGER DEFAULT 0,
                        errors_encountered INTEGER DEFAULT 0
                    )
                ''')
                
                # Table for sync errors
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sync_errors (
                        error_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sync_id INTEGER,
                        meeting_id TEXT,
                        error_type TEXT,
                        error_message TEXT,
                        error_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (sync_id) REFERENCES sync_stats(sync_id)
                    )
                ''')
                
                conn.commit()
                self.logger.info("Database tables created or verified")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create database tables: {e}")

    def is_processed(self, meeting_id):
        """Check if a meeting has already been processed."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM processed_meetings WHERE meeting_id = ?', (meeting_id,))
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error(f"Failed to check if meeting is processed: {e}")
            return False

    def mark_processed(self, meeting_id, meeting_title=None, meeting_date=None, notion_page_id=None, action_count=0):
        """Mark a meeting as processed with optional metadata."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO processed_meetings 
                    (meeting_id, meeting_title, meeting_date, processed_at, notion_page_id, action_count) 
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', 
                    (meeting_id, meeting_title, meeting_date, datetime.now().isoformat(), notion_page_id, action_count)
                )
                conn.commit()
                self.logger.info(f"Meeting {meeting_id} marked as processed")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to mark meeting as processed: {e}")
            return False

    def update_meeting_status(self, meeting_id, notion_page_id=None, action_count=None, sync_status=None):
        """Update the status of a previously processed meeting."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build the update query dynamically based on provided parameters
                update_parts = []
                params = []
                
                if notion_page_id is not None:
                    update_parts.append("notion_page_id = ?")
                    params.append(notion_page_id)
                    
                if action_count is not None:
                    update_parts.append("action_count = ?")
                    params.append(action_count)
                    
                if sync_status is not None:
                    update_parts.append("sync_status = ?")
                    params.append(sync_status)
                
                if not update_parts:
                    self.logger.warning("No update parameters provided for meeting status update")
                    return False
                
                # Add meeting_id to parameters
                params.append(meeting_id)
                
                # Execute update
                cursor.execute(
                    f"UPDATE processed_meetings SET {', '.join(update_parts)} WHERE meeting_id = ?",
                    params
                )
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Updated status for meeting {meeting_id}")
                    return True
                else:
                    self.logger.warning(f"No rows updated for meeting {meeting_id}")
                    return False
                    
        except sqlite3.Error as e:
            self.logger.error(f"Failed to update meeting status: {e}")
            return False

    def start_sync_session(self):
        """Start a new sync session and return the session ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sync_stats (sync_start) VALUES (?)",
                    (datetime.now().isoformat(),)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.Error as e:
            self.logger.error(f"Failed to start sync session: {e}")
            return None

    def end_sync_session(self, sync_id, meetings_processed=0, actions_created=0, errors_encountered=0):
        """End a sync session with statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE sync_stats 
                    SET sync_end = ?, meetings_processed = ?, actions_created = ?, errors_encountered = ?
                    WHERE sync_id = ?
                    """,
                    (datetime.now().isoformat(), meetings_processed, actions_created, errors_encountered, sync_id)
                )
                conn.commit()
                self.logger.info(f"Sync session {sync_id} completed")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to end sync session: {e}")
            return False

    def log_error(self, sync_id, meeting_id, error_type, error_message):
        """Log an error that occurred during synchronization."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO sync_errors (sync_id, meeting_id, error_type, error_message) VALUES (?, ?, ?, ?)",
                    (sync_id, meeting_id, error_type, error_message)
                )
                conn.commit()
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Failed to log sync error: {e}")
            return False

    def get_recent_meetings(self, days=7, limit=10):
        """Get a list of recently processed meetings."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute(
                    """
                    SELECT * FROM processed_meetings 
                    WHERE processed_at > ? 
                    ORDER BY processed_at DESC
                    LIMIT ?
                    """,
                    (cutoff_date, limit)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get recent meetings: {e}")
            return []

    def get_sync_stats(self, days=30):
        """Get synchronization statistics for a time period."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute(
                    """
                    SELECT * FROM sync_stats 
                    WHERE sync_start > ? 
                    ORDER BY sync_start DESC
                    """,
                    (cutoff_date,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get sync stats: {e}")
            return []

    def get_error_report(self, days=7):
        """Get recent error reports."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute(
                    """
                    SELECT e.*, m.meeting_title 
                    FROM sync_errors e
                    LEFT JOIN processed_meetings m ON e.meeting_id = m.meeting_id
                    WHERE e.error_time > ? 
                    ORDER BY e.error_time DESC
                    """,
                    (cutoff_date,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get error report: {e}")
            return []

    def get_total_counts(self):
        """Get total counts of processed meetings and actions."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total meetings processed
                cursor.execute("SELECT COUNT(*) FROM processed_meetings")
                total_meetings = cursor.fetchone()[0]
                
                # Total actions created
                cursor.execute("SELECT SUM(action_count) FROM processed_meetings")
                total_actions = cursor.fetchone()[0] or 0
                
                # Total errors
                cursor.execute("SELECT COUNT(*) FROM sync_errors")
                total_errors = cursor.fetchone()[0]
                
                # Total sync sessions
                cursor.execute("SELECT COUNT(*) FROM sync_stats")
                total_syncs = cursor.fetchone()[0]
                
                return {
                    "total_meetings": total_meetings,
                    "total_actions": total_actions,
                    "total_errors": total_errors,
                    "total_syncs": total_syncs
                }
        except sqlite3.Error as e:
            self.logger.error(f"Failed to get total counts: {e}")
            return {
                "total_meetings": 0,
                "total_actions": 0,
                "total_errors": 0,
                "total_syncs": 0
            } 