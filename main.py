#!/usr/bin/env python3
"""
Granola Sync - Main Entry Point

Enhanced Granola transcript sync with smart data management,
robust error handling, and comprehensive automation support.

Usage:
    python3 granola_sync_main.py [--config CONFIG_PATH] [--dry-run] [--verbose]
"""

import argparse
import sys
from pathlib import Path

# Add package to path if running locally
sys.path.insert(0, str(Path(__file__).parent))

from granola_sync import run_granola_sync


def main():
    """Main entry point for Granola sync"""
    parser = argparse.ArgumentParser(
        description="Sync Granola transcripts to Obsidian with enhanced features",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (default: granola_config.yaml)'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Preview changes without making actual modifications'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output with detailed logging'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Granola Sync 2.0.0'
    )
    
    args = parser.parse_args()
    
    # Set configuration overrides based on arguments
    if args.dry_run or args.verbose:
        print("⚠️  Configuration overrides not yet implemented via CLI")
        print("   Please modify granola_config.yaml directly for now")
    
    try:
        # Run sync with specified config
        result = run_granola_sync(config_path=args.config)
        
        # Handle results
        if result['success']:
            stats = result['stats']
            print(f"✅ Sync completed successfully!")
            
            if stats['documents_processed'] > 0:
                print(f"   📊 Processed {stats['documents_processed']} documents")
                print(f"   ✨ Created {stats['documents_created']}, Updated {stats['documents_updated']}")
                print(f"   🎯 Success rate: {stats['success_rate_percent']}%")
                
                if 'next_sync_after' in result:
                    print(f"   🔄 Next sync will check for documents since: {result['next_sync_after']}")
            
            sys.exit(0)
        else:
            print(f"❌ Sync failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\\n⏹️  Sync interrupted by user")
        sys.exit(130)  # Standard Unix exit code for SIGINT
        
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()