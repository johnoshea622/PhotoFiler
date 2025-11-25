#!/usr/bin/env python3
"""
Copy Organized Photos to Batavia Coast Marina Project Folder

This script copies the already processed and organized photos from the 
Photo adjustments directory to the final Batavia Coast Marina project folder.
"""

import shutil
import sys
from pathlib import Path

def copy_organized_photos():
    """Copy organized photos to the Batavia Coast Marina project folder."""
    
    # Source and destination paths
    source_dir = Path("/Users/johnoshea/Library/CloudStorage/OneDrive-TCDGroup/0 TCD MyDocs/01. BMI Projects/99. Autocad Tricks/Photo adjustments")
    dest_dir = Path("/Users/johnoshea/Library/CloudStorage/OneDrive-TCDGroup/TCD Group - TCD-1816 Batavia Coast Marina Civil & Landscaping (DEVWA)/E Engineering/E4 Photos")
    
    print("🚀 Copying Organized Photos to Batavia Coast Marina Project")
    print("=" * 60)
    print(f"Source: {source_dir}")
    print(f"Destination: {dest_dir}")
    print()
    
    # Check if source exists
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return False
    
    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all date folders (YYYYMMDD format)
    date_folders = [d for d in source_dir.iterdir() 
                   if d.is_dir() and d.name.isdigit() and len(d.name) == 8]
    
    if not date_folders:
        print("❌ No organized date folders found")
        return False
    
    print(f"Found {len(date_folders)} date folders to copy:")
    for folder in sorted(date_folders):
        photo_count = len([f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png'}])
        print(f"  📁 {folder.name} ({photo_count} photos)")
    
    print()
    
    # Ask for confirmation
    response = input("Copy these organized photos to the Batavia Coast Marina project? (y/N): ").lower()
    if response not in ['y', 'yes']:
        print("❌ Operation cancelled")
        return False
    
    print("\nCopying photos...")
    
    total_photos = 0
    copied_folders = 0
    
    # Copy each date folder
    for date_folder in sorted(date_folders):
        dest_folder = dest_dir / date_folder.name
        
        try:
            if dest_folder.exists():
                # Merge with existing folder
                print(f"  📁 Merging {date_folder.name}...")
                for file_path in date_folder.iterdir():
                    if file_path.is_file() and file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.mov', '.mp4'}:
                        dest_file = dest_folder / file_path.name
                        
                        # Handle name conflicts
                        base_name, ext = file_path.name.rsplit('.', 1)
                        counter = 1
                        while dest_file.exists():
                            dest_file = dest_folder / f"{base_name}_{counter}.{ext}"
                            counter += 1
                        
                        shutil.copy2(file_path, dest_file)
                        total_photos += 1
            else:
                # Copy entire folder
                print(f"  📁 Copying {date_folder.name}...")
                shutil.copytree(date_folder, dest_folder)
                photo_count = len([f for f in date_folder.iterdir() 
                                 if f.is_file() and f.suffix.lower() in {'.jpg', '.jpeg', '.png', '.mov', '.mp4'}])
                total_photos += photo_count
            
            copied_folders += 1
            
        except Exception as e:
            print(f"  ❌ Error copying {date_folder.name}: {e}")
    
    # Copy log files
    log_files = ['ai_rename_log.csv', 'sort_log.csv']
    for log_file in log_files:
        log_path = source_dir / log_file
        if log_path.exists():
            try:
                shutil.copy2(log_path, dest_dir / log_file)
                print(f"  📄 Copied {log_file}")
            except Exception as e:
                print(f"  ⚠️  Could not copy {log_file}: {e}")
    
    print("\n" + "=" * 60)
    print("✅ COPY OPERATION COMPLETE")
    print("=" * 60)
    print(f"Folders copied: {copied_folders}")
    print(f"Total photos: {total_photos}")
    print(f"Destination: {dest_dir}")
    print("\n🎉 Photos are now available in the Batavia Coast Marina project folder!")
    
    return True

if __name__ == "__main__":
    success = copy_organized_photos()
    sys.exit(0 if success else 1)