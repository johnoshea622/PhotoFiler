#!/usr/bin/env python3
"""
AI Photo Analysis and Renaming for Construction Photos

Uses computer vision to analyze construction photos and rename them based on detected content:
- Soil/dirt colors (brown, red, clay, sandy, dark, light)
- Construction equipment (excavator, bulldozer, truck, compactor, crane)
- Infrastructure (pipes, concrete, steel, drainage, culvert)
- Construction phases (excavation, foundation, compaction, laying)

Features:
- Uses pre-trained CLIP model for zero-shot image classification
- Dominant color analysis for soil classification
- Maintains date folder organization
- Creates descriptive filenames: YYYYMMDD_HHmm_description.ext
- Dry-run mode for testing
- CSV log of all renames

Usage:
  python ai_photo_renamer.py [--dir "/path/to/photos"] [--dry-run] [--max-files 100]
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

# Default settings
DEFAULT_DIR = "/Users/johnoshea/Library/CloudStorage/OneDrive-TCDGroup/TCD MyDocs/01. BMI Projects/99. Autocad Tricks/Photo adjustments"
DRY_RUN = False

# Media extensions
MEDIA_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".mov", ".mp4"}

# Extensions that should be converted to JPG for Windows compatibility
CONVERT_TO_JPG = {".heic", ".heif"}

# Construction-specific classification categories
CONSTRUCTION_CATEGORIES = {
    "equipment": [
        "excavator digging dirt",
        "bulldozer pushing soil", 
        "dump truck with dirt",
        "compactor rolling ground",
        "crane lifting materials",
        "loader moving earth",
        "grader leveling ground",
        "backhoe excavating"
    ],
    "materials": [
        "concrete pipe in trench",
        "steel reinforcement bars",
        "drainage pipe installation", 
        "culvert pipe laying",
        "aggregate stone pile",
        "sand stockpile",
        "gravel material"
    ],
    "soil_types": [
        "brown clay soil",
        "red clay dirt",
        "sandy light soil", 
        "dark topsoil",
        "rocky ground",
        "wet muddy soil",
        "compacted base course"
    ],
    "activities": [
        "excavation work in progress",
        "foundation preparation",
        "trench digging",
        "ground compaction",
        "pipe installation",
        "earthwork construction",
        "road base preparation"
    ]
}

# Color classification for soil
SOIL_COLORS = {
    "brown": [(139, 69, 19), (160, 82, 45), (205, 133, 63)],
    "red": [(178, 34, 34), (165, 42, 42), (220, 20, 60)],
    "sandy": [(238, 203, 173), (222, 184, 135), (245, 222, 179)],
    "dark": [(64, 64, 64), (105, 105, 105), (128, 128, 128)],
    "clay": [(188, 143, 143), (205, 133, 63), (210, 180, 140)]
}


def convert_heic_to_jpg(heic_path: Path, quality: int = 95) -> Optional[Path]:
    """
    Convert HEIC file to JPG for Windows compatibility.
    Returns the new JPG path if successful, None if failed.
    """
    try:
        # Generate JPG filename
        jpg_name = heic_path.stem + ".jpg"
        jpg_path = heic_path.parent / jpg_name
        
        # Handle name conflicts
        counter = 1
        while jpg_path.exists():
            jpg_name = f"{heic_path.stem}_{counter}.jpg"
            jpg_path = heic_path.parent / jpg_name
            counter += 1
        
        # Convert HEIC to JPG
        with Image.open(heic_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Preserve EXIF data if available
            exif_dict = None
            if hasattr(img, 'getexif'):
                exif_dict = img.getexif()
            
            save_kwargs = {
                'format': 'JPEG',
                'quality': quality,
                'optimize': True
            }
            
            if exif_dict:
                save_kwargs['exif'] = exif_dict
            
            img.save(jpg_path, **save_kwargs)
        
        print(f"    Converted {heic_path.name} → {jpg_path.name}")
        return jpg_path
        
    except Exception as e:
        print(f"    Error converting {heic_path.name}: {e}")
        return None


class AIPhotoAnalyzer:
    def __init__(self):
        print("Loading AI models...")
        try:
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            print("✓ CLIP model loaded successfully")
        except Exception as e:
            print(f"Error loading AI model: {e}")
            print("Continuing with basic color analysis only...")
            self.model = None
            self.processor = None
    
    def analyze_dominant_color(self, image_path: Path) -> str:
        """Analyze dominant colors to classify soil type."""
        try:
            # Load and resize image for efficiency
            img = cv2.imread(str(image_path))
            if img is None:
                return ""
            
            img = cv2.resize(img, (150, 150))
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Get dominant colors using k-means
            pixels = img_rgb.reshape(-1, 3)
            pixels = np.float32(pixels)
            
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            k = 3
            _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
            
            # Find the most frequent color
            centers = np.uint8(centers)
            dominant_color = centers[np.argmax(np.bincount(labels.flatten()))]
            
            # Classify soil color
            min_distance = float('inf')
            closest_soil = ""
            
            for soil_type, colors in SOIL_COLORS.items():
                for ref_color in colors:
                    distance = np.linalg.norm(dominant_color - np.array(ref_color))
                    if distance < min_distance:
                        min_distance = distance
                        closest_soil = soil_type
            
            return closest_soil if min_distance < 80 else ""
            
        except Exception as e:
            print(f"Color analysis error for {image_path.name}: {e}")
            return ""
    
    def analyze_with_clip(self, image_path: Path) -> List[str]:
        """Use CLIP model to classify construction elements."""
        if not self.model or not self.processor:
            return []
        
        try:
            image = Image.open(image_path).convert("RGB")
            
            # Prepare all classification texts
            all_texts = []
            for category_texts in CONSTRUCTION_CATEGORIES.values():
                all_texts.extend(category_texts)
            
            # Add generic fallbacks
            all_texts.extend([
                "construction site",
                "earthwork project", 
                "civil engineering",
                "outdoor work area"
            ])
            
            inputs = self.processor(text=all_texts, images=image, return_tensors="pt", padding=True)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Get top 3 classifications
            top_indices = probs[0].topk(3).indices
            detected = []
            
            for idx in top_indices:
                confidence = probs[0][idx].item()
                if confidence > 0.15:  # Threshold for relevance
                    detected.append(all_texts[idx])
            
            return detected
            
        except Exception as e:
            print(f"CLIP analysis error for {image_path.name}: {e}")
            return []
    
    def analyze_photo(self, image_path: Path) -> Dict[str, any]:
        """Complete photo analysis combining color and object detection."""
        result = {
            "soil_color": "",
            "detected_objects": [],
            "primary_category": "",
            "confidence_score": 0.0
        }
        
        # Color analysis
        soil_color = self.analyze_dominant_color(image_path)
        if soil_color:
            result["soil_color"] = soil_color
        
        # CLIP analysis
        detected = self.analyze_with_clip(image_path)
        result["detected_objects"] = detected
        
        # Determine primary category
        if detected:
            primary = detected[0].lower()
            
            # Categorize the detection
            if any(word in primary for word in ["excavator", "bulldozer", "truck", "compactor", "crane", "loader", "grader"]):
                result["primary_category"] = "equipment"
            elif any(word in primary for word in ["pipe", "concrete", "steel", "drainage", "culvert"]):
                result["primary_category"] = "infrastructure"
            elif any(word in primary for word in ["soil", "dirt", "clay", "sand", "ground"]):
                result["primary_category"] = "soil"
            elif any(word in primary for word in ["excavation", "foundation", "trench", "compaction"]):
                result["primary_category"] = "activity"
            else:
                result["primary_category"] = "construction"
            
            result["confidence_score"] = 0.8  # Simplified confidence
        
        return result


def extract_timestamp_from_filename(filename: str) -> Optional[datetime]:
    """Try to extract timestamp from various filename patterns."""
    patterns = [
        r"PXL_(\d{8})_(\d{6})",  # PXL_20250708_052126
        r"IMG_(\d{8})_(\d{6})",  # IMG_20250708_052126  
        r"(\d{8})_(\d{6})",      # 20250708_052126
        r"IMG-(\d{8})-WA(\d{4})", # IMG-20250808-WA0001
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                if "WA" in pattern:
                    date_str = match.group(1)
                    time_str = match.group(2).ljust(6, '0')  # Pad time if needed
                else:
                    date_str = match.group(1)
                    time_str = match.group(2)
                
                dt = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                return dt
            except ValueError:
                continue
    
    return None


def generate_new_filename(original_path: Path, analysis: Dict, timestamp: Optional[datetime] = None) -> str:
    """Generate descriptive filename based on AI analysis."""
    
    # Use extracted timestamp or current time
    if timestamp:
        dt = timestamp
    else:
        dt = datetime.fromtimestamp(original_path.stat().st_mtime)
    
    date_prefix = dt.strftime("%Y%m%d_%H%M")
    
    # Build description parts
    parts = []
    
    # Add soil color if detected
    if analysis["soil_color"]:
        parts.append(analysis["soil_color"])
    
    # Add primary detection
    if analysis["detected_objects"]:
        primary = analysis["detected_objects"][0].lower()
        # Simplify the description
        if "excavator" in primary:
            parts.append("excavator")
        elif "bulldozer" in primary:
            parts.append("bulldozer") 
        elif "truck" in primary:
            parts.append("truck")
        elif "pipe" in primary:
            parts.append("pipe")
        elif "concrete" in primary:
            parts.append("concrete")
        elif "excavation" in primary:
            parts.append("excavation")
        elif "foundation" in primary:
            parts.append("foundation")
        elif "compaction" in primary:
            parts.append("compaction")
        else:
            # Extract key words
            key_words = []
            for word in primary.split():
                if word in ["dirt", "soil", "clay", "sand", "ground", "work", "construction", "site"]:
                    key_words.append(word)
            if key_words:
                parts.append("_".join(key_words[:2]))
            else:
                parts.append("construction")
    
    # Fallback if no analysis results
    if not parts:
        parts.append("site")
    
    # Create filename
    description = "_".join(parts)
    extension = original_path.suffix.lower()
    
    return f"{date_prefix}_{description}{extension}"


def rename_photos_in_folder(folder_path: Path, analyzer: AIPhotoAnalyzer, dry_run: bool = True, max_files: int = None) -> List[Dict]:
    """Process all photos in a folder."""
    
    photo_files = []
    for ext in MEDIA_EXT:
        photo_files.extend(folder_path.glob(f"*{ext}"))
        photo_files.extend(folder_path.glob(f"*{ext.upper()}"))
    
    if max_files:
        photo_files = photo_files[:max_files]
    
    if not photo_files:
        return []
    
    print(f"Processing {len(photo_files)} files in {folder_path.name}...")
    
    results = []
    
    for i, photo_path in enumerate(photo_files, 1):
        print(f"  [{i}/{len(photo_files)}] Analyzing {photo_path.name}...")
        
        try:
            # Convert HEIC to JPG for Windows compatibility
            original_path = photo_path
            if photo_path.suffix.lower() in CONVERT_TO_JPG:
                converted_path = convert_heic_to_jpg(photo_path)
                if converted_path:
                    photo_path = converted_path
            
            # Extract timestamp from filename
            timestamp = extract_timestamp_from_filename(photo_path.name)
            
            # Analyze photo
            analysis = analyzer.analyze_photo(photo_path)
            
            # Generate new filename
            new_filename = generate_new_filename(photo_path, analysis, timestamp)
            
            # Avoid conflicts
            new_path = photo_path.parent / new_filename
            counter = 1
            base_name_part = new_filename.rsplit('.', 1)[0]
            ext_part = new_filename.rsplit('.', 1)[1]
            
            while new_path.exists() and new_path != photo_path:
                new_filename = f"{base_name_part}_{counter}.{ext_part}"
                new_path = photo_path.parent / new_filename
                counter += 1
            
            # Perform rename
            if new_path != photo_path:
                if not dry_run:
                    photo_path.rename(new_path)
                    print(f"    ✓ Renamed to: {new_filename}")
                    
                    # Remove original HEIC file if conversion occurred
                    if original_path != photo_path and original_path.suffix.lower() in CONVERT_TO_JPG:
                        try:
                            original_path.unlink()
                            print(f"    ✓ Removed original: {original_path.name}")
                        except Exception as e:
                            print(f"    Warning: Could not remove {original_path.name}: {e}")
                else:
                    print(f"    → Would rename to: {new_filename}")
                
                results.append({
                    "original_path": str(original_path),
                    "new_path": str(new_path),
                    "analysis": analysis,
                    "timestamp": timestamp.isoformat() if timestamp else "",
                    "renamed": not dry_run
                })
            else:
                print(f"    - No change needed")
                
        except Exception as e:
            print(f"    ✗ Error processing {photo_path.name}: {e}")
            results.append({
                "original_path": str(photo_path),
                "new_path": "",
                "analysis": {"error": str(e)},
                "timestamp": "",
                "renamed": False
            })
    
    return results


def write_rename_log(results: List[Dict], output_path: Path) -> None:
    """Write detailed log of all rename operations."""
    with output_path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "original_filename", "new_filename", "folder", "soil_color", 
            "detected_objects", "primary_category", "timestamp", "renamed"
        ])
        
        for result in results:
            analysis = result.get("analysis", {})
            original_path = Path(result["original_path"])
            new_path = Path(result["new_path"]) if result["new_path"] else original_path
            
            writer.writerow([
                original_path.name,
                new_path.name,
                original_path.parent.name,
                analysis.get("soil_color", ""),
                "; ".join(analysis.get("detected_objects", [])),
                analysis.get("primary_category", ""),
                result.get("timestamp", ""),
                result.get("renamed", False)
            ])


def main():
    parser = argparse.ArgumentParser(description="AI-powered photo analysis and renaming for construction photos")
    parser.add_argument("--dir", default=DEFAULT_DIR, help="Directory containing date folders with photos")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be renamed without actually renaming")
    parser.add_argument("--max-files", type=int, help="Limit number of files to process (for testing)")
    parser.add_argument("--folder", help="Process only specific folder (folder name)")
    args = parser.parse_args()
    
    root_dir = Path(args.dir)
    if not root_dir.exists():
        print(f"Directory not found: {root_dir}")
        sys.exit(1)
    
    # Initialize AI analyzer
    analyzer = AIPhotoAnalyzer()
    
    # Determine dry run mode
    dry_run = args.dry_run
    
    # Find date folders to process
    if args.folder:
        folders = [root_dir / args.folder]
        folders = [f for f in folders if f.exists() and f.is_dir()]
    else:
        folders = [f for f in root_dir.iterdir() if f.is_dir() and re.match(r'^\d{8}$', f.name)]
        folders = sorted(folders)
    
    if not folders:
        print("No date folders found to process")
        return
    
    print(f"Found {len(folders)} folders to process")
    print(f"Dry run mode: {dry_run}")
    
    all_results = []
    
    for folder in folders:
        folder_results = rename_photos_in_folder(folder, analyzer, dry_run, args.max_files)
        all_results.extend(folder_results)
    
    # Write log
    log_path = root_dir / "ai_rename_log.csv"
    write_rename_log(all_results, log_path)
    
    # Summary
    total_processed = len(all_results)
    total_renamed = sum(1 for r in all_results if r.get("renamed", False))
    total_errors = sum(1 for r in all_results if "error" in r.get("analysis", {}))
    
    print(f"\n--- AI Photo Renaming Complete ---")
    print(f"Total files processed: {total_processed}")
    print(f"Files renamed: {total_renamed}")
    print(f"Errors: {total_errors}")
    print(f"Dry run: {dry_run}")
    print(f"Log file: {log_path}")
    
    if dry_run and total_processed > 0:
        print(f"\nTo actually rename files, run with: --no-dry-run")


if __name__ == "__main__":
    main()
