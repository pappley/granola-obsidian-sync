"""
Participant detection and speaker identification for Granola transcripts

Handles mapping of audio sources to real participant names using 
document list information and enhanced speaker detection logic.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from .config import GranolaConfig


class ParticipantManager:
    """Manages participant detection and speaker identification"""
    
    def __init__(self, config: GranolaConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._document_mapping: Optional[Dict[str, Dict[str, str]]] = None
        self._participant_data: Optional[Dict[str, List[Dict[str, Any]]]] = None
        
    def load_document_mapping(self, api_client) -> Dict[str, Dict[str, str]]:
        """Load or create document to list mapping with smart refresh"""
        mapping_path = self.config.paths.document_mapping
        
        # Check if mapping exists and is fresh
        if self._should_refresh_mapping():
            self.logger.info("Document mapping is stale or missing, refreshing...")
            mapping = self._create_document_mapping(api_client)
        else:
            # Load existing mapping
            try:
                with open(mapping_path, 'r') as f:
                    mapping = json.load(f)
                self.logger.info(f"Loaded document mapping for {len(mapping)} documents")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                self.logger.warning(f"Could not load document mapping: {e}, creating new one")
                mapping = self._create_document_mapping(api_client)
        
        self._document_mapping = mapping
        return mapping
    
    def _should_refresh_mapping(self) -> bool:
        """Check if document mapping should be refreshed"""
        if not self.config.should_auto_refresh_mapping():
            return False
            
        mapping_path = self.config.paths.document_mapping
        
        if not mapping_path.exists():
            return True
        
        # Check age of mapping file
        try:
            file_age = datetime.now() - datetime.fromtimestamp(mapping_path.stat().st_mtime)
            max_age = timedelta(hours=self.config.get_mapping_max_age_hours())
            
            if file_age > max_age:
                self.logger.debug(f"Mapping file is {file_age} old, max age is {max_age}")
                return True
        except OSError:
            return True
            
        return False
    
    def _create_document_mapping(self, api_client) -> Dict[str, Dict[str, str]]:
        """Create mapping of documents to document lists"""
        document_lists = api_client.fetch_document_lists()
        mapping = {}
        
        for doc_list in document_lists:
            list_id = doc_list.get('id')
            list_name = doc_list.get('name', 'Untitled List')
            documents = doc_list.get('documents', [])
            
            for doc in documents:
                doc_id = doc.get('id')
                doc_title = doc.get('title', 'Untitled')
                
                if doc_id:
                    mapping[doc_id] = {
                        'document_list_id': list_id,
                        'document_list_name': list_name,
                        'document_title': doc_title
                    }
        
        # Save mapping with backup
        self._save_mapping_with_backup(mapping)
        
        self.logger.info(f"Created mapping for {len(mapping)} documents")
        return mapping
    
    def _save_mapping_with_backup(self, mapping: Dict[str, Dict[str, str]]):
        """Save mapping with automatic backup"""
        mapping_path = self.config.paths.document_mapping
        
        # Create backup if enabled and original exists
        if self.config.data.get('auto_backup_mapping', True) and mapping_path.exists():
            backup_name = f"document_mapping_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = self.config.paths.backup_directory / backup_name
            
            try:
                import shutil
                shutil.copy2(mapping_path, backup_path)
                self.logger.debug(f"Created mapping backup: {backup_path}")
            except Exception as e:
                self.logger.warning(f"Failed to create mapping backup: {e}")
        
        # Save new mapping
        try:
            with open(mapping_path, 'w') as f:
                json.dump(mapping, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save document mapping: {e}")
            raise
    
    def get_participants_for_document(self, document_id: str, participant_data: Dict[str, List[Dict[str, Any]]]) -> List[str]:
        """Get participant list for a document using the mapping"""
        if not self._document_mapping or document_id not in self._document_mapping:
            return self.config.sync['fallback_participants']
        
        list_info = self._document_mapping[document_id]
        document_list_id = list_info['document_list_id']
        
        if document_list_id in participant_data:
            participants = participant_data[document_list_id]
            names = []
            
            for p in participants:
                name = p.get('name', p.get('email', 'Unknown'))
                if name and name not in names:
                    names.append(name)
            
            # Add "Me" to represent the user if not already present
            if "Me" not in names:
                names.insert(0, "Me")
            
            return names
        
        return self.config.sync['fallback_participants']
    
    def parse_transcript_with_participants(self, transcript_data: List[Dict[str, Any]], participants: List[str]) -> Optional[Dict[str, Any]]:
        """Parse transcript data with enhanced participant mapping"""
        if not transcript_data or not isinstance(transcript_data, list):
            return None
        
        transcript_text = ""
        speakers = set()
        speaker_stats = {}  # Track speaking time per detected speaker
        
        # Enhanced speaker detection logic
        participant_names = participants.copy()
        
        for item in transcript_data:
            if isinstance(item, dict) and 'text' in item:
                text = item.get('text', '').strip()
                if not text:
                    continue
                
                # Determine speaker from source field with enhanced logic
                speaker = self._detect_speaker(item, participant_names, speaker_stats)
                
                if speaker and text:
                    speakers.add(speaker)
                    
                    # Update speaker statistics
                    if speaker not in speaker_stats:
                        speaker_stats[speaker] = {'word_count': 0, 'segment_count': 0}
                    
                    speaker_stats[speaker]['word_count'] += len(text.split())
                    speaker_stats[speaker]['segment_count'] += 1
                    
                    transcript_text += f"{speaker}: {text}\n\n"
        
        return {
            'text': transcript_text,
            'speakers': list(speakers),
            'speaker_stats': speaker_stats,
            'raw_data': transcript_data
        }
    
    def _detect_speaker(self, item: Dict[str, Any], participants: List[str], speaker_stats: Dict[str, Any]) -> str:
        """Enhanced speaker detection logic"""
        source = item.get('source', 'unknown')
        
        if source == 'microphone':
            # Microphone is typically the user
            return participants[0] if participants else "Me"
            
        elif source == 'system':
            # System audio - try to intelligently assign to other participants
            # Use specific names only for 2-person meetings, otherwise use "Them"
            
            other_participants = participants[1:] if len(participants) > 1 else ["Them"]
            
            if len(other_participants) == 1:
                # 2-person meeting: use specific name for clarity
                return other_participants[0]
            else:
                # 3+ person meeting: use "Them" to maintain Me/Them dichotomy
                return "Them"
            
        else:
            # Unknown source, try to map to a participant name or fall back
            source_title = source.title()
            if source_title in participants:
                return source_title
            
            return "Unknown"
    
    def get_document_list_info(self, document_id: str) -> Tuple[str, str]:
        """Get document list name and ID for a document"""
        if not self._document_mapping or document_id not in self._document_mapping:
            return "", ""
        
        list_info = self._document_mapping[document_id]
        return list_info.get('document_list_name', ''), list_info.get('document_list_id', '')
    
    def cleanup_old_backups(self):
        """Remove old backup files based on retention policy"""
        if not self.config.data.get('auto_backup_mapping', True):
            return
            
        backup_dir = self.config.paths.backup_directory
        retention_days = self.config.data.get('backup_retention_days', 30)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        try:
            for backup_file in backup_dir.glob('document_mapping_backup_*.json'):
                if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                    backup_file.unlink()
                    self.logger.debug(f"Removed old backup: {backup_file}")
        except Exception as e:
            self.logger.warning(f"Error during backup cleanup: {e}")
    
    def validate_participants(self, participants: List[str]) -> List[str]:
        """Validate and clean up participant list"""
        if not participants:
            return self.config.sync['fallback_participants']
        
        # Remove empty or invalid participants
        valid_participants = []
        for p in participants:
            if isinstance(p, str) and p.strip() and len(p.strip()) <= 50:  # Reasonable name length limit
                valid_participants.append(p.strip())
        
        if not valid_participants:
            return self.config.sync['fallback_participants']
        
        # Ensure "Me" is first if present
        if "Me" in valid_participants:
            valid_participants.remove("Me")
            valid_participants.insert(0, "Me")
        
        return valid_participants