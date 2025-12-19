"""
Main sync orchestration for Granola transcripts

Coordinates all components to perform intelligent, robust syncing of
Granola transcripts to Obsidian with enhanced error handling and monitoring.
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from .config import GranolaConfig
from .api import GranolaAPI, GranolaAPIError  
from .participants import ParticipantManager
from .obsidian import ObsidianIntegration


class SyncStats:
    """Track sync operation statistics"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.documents_processed = 0
        self.documents_created = 0
        self.documents_updated = 0
        self.documents_skipped = 0
        self.documents_failed = 0
        self.transcripts_fetched = 0
        self.transcripts_failed = 0
        
    @property
    def duration(self) -> float:
        """Get sync duration in seconds"""
        return (datetime.now() - self.start_time).total_seconds()
    
    @property
    def success_rate(self) -> float:
        """Get success rate as percentage"""
        if self.documents_processed == 0:
            return 0.0
        return ((self.documents_processed - self.documents_failed) / self.documents_processed) * 100
    
    def summary(self) -> Dict[str, Any]:
        """Get complete stats summary"""
        return {
            'duration_seconds': round(self.duration, 2),
            'documents_processed': self.documents_processed,
            'documents_created': self.documents_created,
            'documents_updated': self.documents_updated,
            'documents_skipped': self.documents_skipped,
            'documents_failed': self.documents_failed,
            'transcripts_fetched': self.transcripts_fetched,
            'transcripts_failed': self.transcripts_failed,
            'success_rate_percent': round(self.success_rate, 1)
        }


class GranolaSync:
    """Main sync coordinator"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize sync system with configuration"""
        self.config = GranolaConfig(config_path)
        self.api = GranolaAPI(self.config)
        self.participants = ParticipantManager(self.config)
        self.obsidian = ObsidianIntegration(self.config)
        
        # Set up logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize state
        self.stats = SyncStats()
        self._participant_data: Optional[Dict[str, List[Dict[str, Any]]]] = None
        self._document_mapping: Optional[Dict[str, Dict[str, str]]] = None
    
    def _setup_logging(self):
        """Configure logging based on configuration"""
        log_level = getattr(logging, self.config.logging['level'].upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' if self.config.logging['include_timestamps'] else '%(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()  # Console output
            ]
        )
    
    def run_sync(self) -> Dict[str, Any]:
        """
        Run complete sync operation
        
        Returns:
            Dictionary with sync results and statistics
        """
        try:
            self.logger.info("🚀 Starting Granola sync...")
            
            # Initialize components
            self._initialize_sync()
            
            # Get documents to sync
            recent_documents = self._fetch_documents_to_sync()
            
            if not recent_documents:
                self.logger.info("✅ No new documents to sync")
                self.api.update_last_sync_time()
                return self._create_sync_result(success=True)
            
            # Process documents
            self._process_documents(recent_documents)
            
            # Update sync timestamp
            self.api.update_last_sync_time()
            
            # Cleanup old data
            self._cleanup()
            
            # Log completion
            self._log_completion()
            
            return self._create_sync_result(success=True)
            
        except Exception as e:
            self.logger.error(f"❌ Fatal sync error: {e}")
            if self.config.development.get('verbose_output', False):
                import traceback
                traceback.print_exc()
            
            return self._create_sync_result(success=False, error=str(e))
    
    def _initialize_sync(self):
        """Initialize sync components and load data"""
        self.logger.info("📋 Initializing sync components...")
        
        try:
            # Load participant data
            self._participant_data = self.api.load_participant_data()
            
            # Load/refresh document mapping
            self._document_mapping = self.participants.load_document_mapping(self.api)
            
            self.logger.info("✅ Initialization complete")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize sync: {e}")
            raise
    
    def _fetch_documents_to_sync(self) -> List[Dict[str, Any]]:
        """Fetch documents that need to be synced"""
        last_sync = self.api.get_last_sync_time()
        self.logger.info(f"🕐 Last sync: {last_sync.strftime('%Y-%m-%d %H:%M')}")
        
        try:
            documents = self.api.fetch_documents_since(last_sync)
            self.logger.info(f"📄 Found {len(documents)} documents to sync")
            return documents
            
        except GranolaAPIError as e:
            self.logger.error(f"Failed to fetch documents: {e}")
            if not self.config.should_continue_on_error('document'):
                raise
            return []
    
    def _process_documents(self, documents: List[Dict[str, Any]]):
        """Process each document for sync"""
        self.logger.info(f"🔄 Processing {len(documents)} documents...")
        
        for i, document in enumerate(documents, 1):
            try:
                self._process_single_document(document, i, len(documents))
                self.stats.documents_processed += 1
                
            except Exception as e:
                self.stats.documents_failed += 1
                self.logger.error(f"Error processing document {i}: {e}")
                
                if not self.config.should_continue_on_error('document'):
                    raise
            
            # Brief pause between documents
            time.sleep(self.config.api.request_delay)
    
    def _process_single_document(self, document: Dict[str, Any], index: int, total: int):
        """Process a single document"""
        title = document.get('title') or 'Untitled'
        doc_id = document.get('id', '')
        created_at = document.get('created_at', 'N/A')
        
        # Format creation date for display
        created_display = self._format_display_date(created_at)
        
        self.logger.info(f"📋 Document {index}/{total}: {title}")
        self.logger.debug(f"   - Created: {created_display}")
        
        # Get participants for this document
        participants = self.participants.get_participants_for_document(
            doc_id, self._participant_data
        )
        
        # Show enhanced participant info if available
        if len(participants) > 2 or participants != self.config.sync['fallback_participants']:
            self.logger.info(f"   - Participants: {', '.join(participants)}")
        
        # Create filename
        meeting_date = self._extract_date(created_at)
        filename = self.obsidian.create_safe_filename(title, meeting_date)
        output_path = self.config.paths.obsidian_vault / filename
        
        # Check if updating existing file
        is_update = output_path.exists()
        if is_update:
            self.logger.debug(f"   🔄 Updating: {filename}")
        else:
            self.logger.debug(f"   ✨ Creating: {filename}")
        
        # Fetch transcript
        transcript_content = self._fetch_and_parse_transcript(doc_id, participants)
        
        # Get document list information
        document_list_name, document_list_id = self.participants.get_document_list_info(doc_id)
        
        # Create Obsidian note
        note_content, _, _ = self.obsidian.create_note_from_document(
            document=document,
            transcript_content=transcript_content,
            participants=participants,
            document_list_name=document_list_name,
            document_list_id=document_list_id
        )
        
        # Validate note content
        if not self.obsidian.validate_note_content(note_content):
            self.logger.warning(f"   ⚠️ Invalid note content generated for {filename}")
        
        # Save note
        if self.obsidian.save_note(note_content, filename):
            self.logger.info(f"   ✅ Saved successfully")
            if is_update:
                self.stats.documents_updated += 1
            else:
                self.stats.documents_created += 1
        else:
            self.stats.documents_failed += 1
            raise Exception(f"Failed to save note: {filename}")
    
    def _fetch_and_parse_transcript(self, document_id: str, participants: List[str]) -> Optional[Dict[str, Any]]:
        """Fetch and parse transcript for a document"""
        try:
            raw_transcript = self.api.fetch_transcript(document_id)
            
            if raw_transcript:
                parsed_transcript = self.participants.parse_transcript_with_participants(
                    raw_transcript, participants
                )
                
                if parsed_transcript and parsed_transcript.get('text'):
                    char_count = len(parsed_transcript['text'])
                    self.logger.debug(f"   ✅ Transcript: {char_count} chars")
                    self.stats.transcripts_fetched += 1
                    return parsed_transcript
                else:
                    self.logger.debug(f"   ⚠️ No readable transcript content")
            else:
                self.logger.debug(f"   ⚠️ Could not fetch transcript")
            
            self.stats.transcripts_failed += 1
            return None
            
        except Exception as e:
            self.logger.warning(f"   ❌ Transcript error: {e}")
            self.stats.transcripts_failed += 1
            
            if not self.config.should_continue_on_error('transcript'):
                raise
            
            return None
    
    def _format_display_date(self, date_str: str) -> str:
        """Format date string for display"""
        if not date_str:
            return 'Unknown'
        
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M')
        except ValueError:
            return date_str[:19] if len(date_str) >= 19 else date_str
    
    def _extract_date(self, date_str: str) -> str:
        """Extract date portion from datetime string"""
        if not date_str:
            return ""
        
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return date_str[:10] if len(date_str) >= 10 else ""
    
    def _cleanup(self):
        """Perform cleanup operations"""
        try:
            self.participants.cleanup_old_backups()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    def _log_completion(self):
        """Log sync completion with statistics"""
        stats = self.stats.summary()
        
        self.logger.info("🎉 Sync Complete!")
        self.logger.info(f"   ✅ Created: {stats['documents_created']}")
        self.logger.info(f"   🔄 Updated: {stats['documents_updated']}")
        self.logger.info(f"   ⏭️ Skipped: {stats['documents_skipped']}")
        self.logger.info(f"   ❌ Failed: {stats['documents_failed']}")
        self.logger.info(f"   📊 Success Rate: {stats['success_rate_percent']}%")
        self.logger.info(f"   ⏱️ Duration: {stats['duration_seconds']}s")
        
        total_files = self.obsidian.get_total_files_count()
        self.logger.info(f"   📁 Total files: {total_files}")
    
    def _create_sync_result(self, success: bool, error: Optional[str] = None) -> Dict[str, Any]:
        """Create sync result dictionary"""
        result = {
            'success': success,
            'stats': self.stats.summary(),
            'total_files': self.obsidian.get_total_files_count()
        }
        
        if error:
            result['error'] = error
        
        if success and self.stats.documents_processed > 0:
            next_sync_time = datetime.now().strftime('%Y-%m-%d %H:%M')
            result['next_sync_after'] = next_sync_time
        
        return result


# Convenience function for external use
def run_granola_sync(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Run Granola sync with specified configuration"""
    sync = GranolaSync(config_path)
    return sync.run_sync()


if __name__ == "__main__":
    # Allow running sync directly
    result = run_granola_sync()
    
    if result['success']:
        print("Sync completed successfully")
    else:
        print(f"Sync failed: {result.get('error', 'Unknown error')}")
        exit(1)