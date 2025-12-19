#!/usr/bin/env python3
"""
Setup script for Granola sync automation
Helps configure cron jobs for regular syncing
"""

import subprocess
import os
from pathlib import Path

def get_current_crontab():
    """Get current crontab entries"""
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return ""
    except FileNotFoundError:
        print("❌ crontab command not found. Please install cron.")
        return None

def add_cron_job(frequency_choice):
    """Add cron job based on frequency choice"""
    script_path = Path(__file__).parent.absolute() / "run_sync.sh"
    
    # Cron schedules
    schedules = {
        "1": f"0 * * * * {script_path}",      # Every hour
        "2": f"0 */4 * * * {script_path}",    # Every 4 hours
        "3": f"0 9,17 * * 1-5 {script_path}", # Twice daily on weekdays (9am, 5pm)
        "4": f"0 9 * * * {script_path}",      # Once daily at 9am
        "5": f"0 9 * * 1 {script_path}",      # Weekly on Monday at 9am
    }
    
    if frequency_choice not in schedules:
        print("❌ Invalid frequency choice")
        return False
    
    cron_entry = schedules[frequency_choice]
    current_crontab = get_current_crontab()
    
    if current_crontab is None:
        return False
    
    # Check if entry already exists
    if str(script_path) in current_crontab:
        print("⚠️  Granola sync job already exists in crontab")
        print("Current entry found. Removing old entry...")
        
        # Remove old entries
        lines = current_crontab.split('\n')
        filtered_lines = [line for line in lines if str(script_path) not in line]
        current_crontab = '\n'.join(filtered_lines)
    
    # Add new entry
    if current_crontab:
        new_crontab = current_crontab + '\n' + cron_entry
    else:
        new_crontab = cron_entry
    
    # Write to crontab
    try:
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_crontab)
        
        if process.returncode == 0:
            print("✅ Cron job added successfully!")
            return True
        else:
            print("❌ Failed to add cron job")
            return False
    except Exception as e:
        print(f"❌ Error setting up cron job: {e}")
        return False

def remove_cron_job():
    """Remove Granola sync cron jobs"""
    script_path = Path(__file__).parent.absolute() / "run_sync.sh"
    current_crontab = get_current_crontab()
    
    if current_crontab is None:
        return False
    
    if str(script_path) not in current_crontab:
        print("ℹ️  No Granola sync jobs found in crontab")
        return True
    
    # Remove entries
    lines = current_crontab.split('\n')
    filtered_lines = [line for line in lines if str(script_path) not in line]
    new_crontab = '\n'.join(filtered_lines)
    
    try:
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_crontab)
        
        if process.returncode == 0:
            print("✅ Cron job removed successfully!")
            return True
        else:
            print("❌ Failed to remove cron job")
            return False
    except Exception as e:
        print(f"❌ Error removing cron job: {e}")
        return False

def show_current_jobs():
    """Show current cron jobs related to Granola sync"""
    script_path = Path(__file__).parent.absolute() / "run_granola_sync.sh"
    current_crontab = get_current_crontab()
    
    if current_crontab is None:
        return
    
    granola_jobs = [line for line in current_crontab.split('\n') if str(script_path) in line]
    
    if granola_jobs:
        print("📋 Current Granola sync cron jobs:")
        for job in granola_jobs:
            print(f"   {job}")
    else:
        print("ℹ️  No Granola sync cron jobs found")

def main():
    """Main setup function"""
    print("🔄 Granola Sync Automation Setup")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Set up automatic syncing")
        print("2. Remove automatic syncing") 
        print("3. Show current sync jobs")
        print("4. Test sync script")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            print("\n📅 Choose sync frequency:")
            print("1. Every hour")
            print("2. Every 4 hours") 
            print("3. Twice daily (9am, 5pm) on weekdays")
            print("4. Once daily (9am)")
            print("5. Weekly (Monday 9am)")
            
            freq_choice = input("\nEnter frequency choice (1-5): ").strip()
            
            if freq_choice in ["1", "2", "3", "4", "5"]:
                if add_cron_job(freq_choice):
                    frequencies = {
                        "1": "every hour",
                        "2": "every 4 hours",
                        "3": "twice daily on weekdays",
                        "4": "once daily",
                        "5": "weekly"
                    }
                    print(f"🎉 Granola sync will now run {frequencies[freq_choice]}")
                    
                    # Show log location
                    log_dir = Path(__file__).parent.absolute() / "logs"
                    print(f"📁 Logs will be saved to: {log_dir}")
                else:
                    print("❌ Failed to set up automation")
            else:
                print("❌ Invalid choice")
        
        elif choice == "2":
            remove_cron_job()
        
        elif choice == "3":
            show_current_jobs()
        
        elif choice == "4":
            print("🧪 Testing sync script...")
            script_path = Path(__file__).parent.absolute() / "run_granola_sync.sh"
            try:
                result = subprocess.run([str(script_path)], capture_output=True, text=True)
                if result.returncode == 0:
                    print("✅ Test completed successfully!")
                else:
                    print(f"❌ Test failed with code {result.returncode}")
                    if result.stderr:
                        print(f"Error: {result.stderr}")
            except Exception as e:
                print(f"❌ Error running test: {e}")
        
        elif choice == "5":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()