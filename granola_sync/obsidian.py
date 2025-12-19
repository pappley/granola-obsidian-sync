"""
Obsidian integration for Granola transcripts

Handles creation of properly formatted Obsidian notes with YAML frontmatter,
safe filename generation, and content structure optimization.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

from .config import GranolaConfig


class ObsidianIntegration:
    """Handles creation and management of Obsidian notes"""
    
    def __init__(self, config: GranolaConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def create_note_from_document(
        self, 
        document: Dict[str, Any], 
        transcript_content: Optional[Dict[str, Any]],
        participants: List[str],
        document_list_name: str = "",
        document_list_id: str = ""
    ) -> Tuple[str, str, str]:
        """
        Create an enhanced Obsidian-formatted note from document data
        
        Returns:
            Tuple of (note_content, title, meeting_date)
        """
        # Extract basic document info
        title = document.get('title') or 'Untitled Meeting'
        created_at = document.get('created_at', '')
        updated_at = document.get('updated_at', '')
        doc_id = document.get('id', '')
        
        # Parse and format date
        meeting_date = self._extract_meeting_date(created_at)
        
        # Create YAML frontmatter
        frontmatter = self._create_frontmatter(
            title=title,
            meeting_date=meeting_date,
            participants=participants,
            doc_id=doc_id,
            created_at=created_at,
            updated_at=updated_at,
            document_list_name=document_list_name,
            document_list_id=document_list_id
        )
        
        # Build note content
        content = self._build_note_content(
            title=title,
            transcript_content=transcript_content,
            document_list_name=document_list_name
        )
        
        # Combine frontmatter and content
        full_note = self._format_yaml_frontmatter(frontmatter) + content
        
        return full_note, title, meeting_date
    
    def _extract_meeting_date(self, created_at: str) -> str:
        """Extract and format meeting date from created_at timestamp"""
        if not created_at:
            return ""
        
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            # Fallback to string slicing if ISO parsing fails
            return created_at[:10] if len(created_at) >= 10 else ""
    
    def _create_frontmatter(
        self, 
        title: str,
        meeting_date: str,
        participants: List[str],
        doc_id: str,
        created_at: str,
        updated_at: str,
        document_list_name: str = "",
        document_list_id: str = ""
    ) -> Dict[str, Any]:
        """Create YAML frontmatter dictionary based on configuration"""
        
        frontmatter = {}
        
        # Add fields based on configuration
        for field in self.config.get_frontmatter_fields():
            if field == 'title':
                frontmatter['title'] = title
            elif field == 'date':
                if meeting_date:
                    frontmatter['date'] = meeting_date
            elif field == 'participants':
                frontmatter['participants'] = participants
            elif field == 'granola_id':
                frontmatter['granola_id'] = doc_id
            elif field == 'created_at':
                if created_at:
                    frontmatter['created_at'] = created_at
            elif field == 'updated_at':
                if updated_at:
                    frontmatter['updated_at'] = updated_at
            elif field == 'source':
                frontmatter['source'] = 'granola'
            elif field == 'document_list' and document_list_name:
                frontmatter['document_list'] = document_list_name
            elif field == 'document_list_id' and document_list_id:
                frontmatter['document_list_id'] = document_list_id
        
        return frontmatter
    
    def _format_yaml_frontmatter(self, frontmatter: Dict[str, Any]) -> str:
        """Format frontmatter dictionary as YAML header"""
        yaml_header = "---\n"
        
        for key, value in frontmatter.items():
            if isinstance(value, list):
                if value:  # Only include non-empty lists
                    yaml_header += f"{key}: {json.dumps(value)}\n"
            elif value:  # Only include non-empty values
                # Escape quotes in string values
                if isinstance(value, str):
                    escaped_value = value.replace('"', '\\"')
                    yaml_header += f'{key}: "{escaped_value}"\n'
                else:
                    yaml_header += f'{key}: "{value}"\n'
        
        yaml_header += "---\n\n"
        return yaml_header
    
    def _build_note_content(
        self,
        title: str,
        transcript_content: Optional[Dict[str, Any]],
        document_list_name: str = ""
    ) -> str:
        """Build the main content section of the note"""
        content = f"# {title}\n\n"
        
        # Add meeting series information if configured
        if document_list_name and self.config.obsidian.get('include_meeting_series', True):
            content += f"**Meeting Series:** {document_list_name}\n\n"
        
        # Add transcript or placeholder
        if transcript_content and transcript_content.get('text'):
            content += f"{self.config.documents['transcript_section_header']}\n\n"
            content += transcript_content['text']
            content += "\n\n"
            
            # Add speaker statistics if available and configured
            if (transcript_content.get('speaker_stats') and 
                self.config.obsidian.get('include_participant_count', False)):
                content += self._format_speaker_stats(transcript_content['speaker_stats'])
        else:
            content += f"{self.config.documents['notes_section_header']}\n\n"
            content += f"{self.config.documents['no_transcript_message']}\n\n"
        
        return content
    
    def _format_speaker_stats(self, speaker_stats: Dict[str, Dict[str, int]]) -> str:
        """Format speaker statistics section"""
        if not speaker_stats:
            return ""
        
        stats_content = "### Speaking Summary\n\n"
        
        # Sort speakers by word count (descending)
        sorted_speakers = sorted(
            speaker_stats.items(), 
            key=lambda x: x[1]['word_count'], 
            reverse=True
        )
        
        for speaker, stats in sorted_speakers:
            word_count = stats['word_count']
            segment_count = stats['segment_count']
            stats_content += f"- **{speaker}**: {word_count} words in {segment_count} segments\n"
        
        stats_content += "\n"
        return stats_content
    
    def create_safe_filename(self, title: str, date: str) -> str:
        """Create a filesystem-safe filename from title and date"""
        # Handle None or empty titles
        if not title or not isinstance(title, str):
            title = "Untitled"
        
        # Remove unsafe characters
        pattern = self.config.get_safe_filename_pattern()
        safe_title = re.sub(pattern, '', title).strip()
        safe_title = re.sub(r'[-\s]+', '-', safe_title)
        
        # Ensure reasonable length
        max_length = self.config.documents.get('max_filename_length', 255)
        if len(safe_title) > max_length - 20:  # Leave room for date and extension
            safe_title = safe_title[:max_length - 20]
        
        # Build filename based on format configuration
        filename_format = self.config.documents.get('filename_format', '{date}-{title}.md')
        
        if date and '{date}' in filename_format:
            filename = filename_format.format(date=date, title=safe_title)
        else:
            filename = filename_format.replace('{date}-', '').format(title=safe_title)
        
        return filename
    
    def save_note(self, content: str, filename: str, update_existing: bool = None) -> bool:
        """
        Save note to Obsidian vault
        
        Args:
            content: Note content to save
            filename: Target filename
            update_existing: Whether to update existing files (uses config default if None)
            
        Returns:
            True if successful, False otherwise
        """
        if update_existing is None:
            update_existing = self.config.sync.get('update_existing_files', True)
        
        output_path = self.config.paths.obsidian_vault / filename
        
        # Check if file exists and handle accordingly
        if output_path.exists():
            if not update_existing:
                self.logger.info(f"File exists and updates disabled, skipping: {filename}")
                return False
            
            # Create backup if configured
            if self.config.sync.get('create_backup_before_update', False):
                self._create_file_backup(output_path)
            
            self.logger.debug(f"Updating existing file: {filename}")
        else:
            self.logger.debug(f"Creating new file: {filename}")
        
        # Save the file
        try:
            if self.config.is_dry_run():
                self.logger.info(f"[DRY RUN] Would save note to: {output_path}")
                return True
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save note {filename}: {e}")
            return False
    
    def _create_file_backup(self, file_path: Path):
        """Create a backup of existing file"""
        if not file_path.exists():
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
            backup_path = self.config.paths.backup_directory / backup_name
            
            import shutil
            shutil.copy2(file_path, backup_path)
            self.logger.debug(f"Created file backup: {backup_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to create backup for {file_path}: {e}")
    
    def get_total_files_count(self) -> int:
        """Get total count of markdown files in Obsidian vault"""
        try:
            return len(list(self.config.paths.obsidian_vault.glob('*.md')))
        except Exception:
            return 0
    
    def validate_note_content(self, content: str) -> bool:
        """Validate note content structure and format"""
        if not content or not isinstance(content, str):
            return False
        
        # Check for YAML frontmatter
        if not content.startswith('---'):
            self.logger.warning("Note content missing YAML frontmatter")
            return False
        
        # Basic structure validation
        parts = content.split('---', 2)
        if len(parts) < 3:
            self.logger.warning("Invalid YAML frontmatter structure")
            return False
        
        return True