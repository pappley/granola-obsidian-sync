"""
Granola Sync Package

A comprehensive system for syncing Granola transcripts to Obsidian with 
enhanced participant detection, smart data management, and robust automation.
"""

__version__ = "2.0.0"
__author__ = "Personal OS System"

from .config import GranolaConfig
from .sync import GranolaSync, run_granola_sync

__all__ = ['GranolaConfig', 'GranolaSync', 'run_granola_sync']