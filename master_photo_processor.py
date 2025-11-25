#!/Users/johnoshea/Documents/programming/venvs/photo-sorting/bin/python
"""
Master Photo Processing Script for Construction Photos

This script combines all photo processing steps into one comprehensive workflow:
1. Sorts photos by date into YYYYMMDD folders
2. Converts HEIC files to JPG for Windows compatibility
3. Uses AI to rename photos with descriptive names
4. Copies organized photos to final destination folder
5. Maintains detailed logs of all operations

Features:
- Complete automation from input to final destination
- HEIC to JPG conversion with EXIF preservation
- AI-powered descriptive naming based on construction content
- Date-based folder organization
- Comprehensive error handling and logging
- Dry-run mode for testing

Usage:
  python master_photo_processor.py [--input "/path/to/input"] [--output "/path/to/output"] [--dry-run]
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import traceback
import contextlib
import io
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import modules from our existing scripts
try:
    from PIL import Image, ExifTags
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError as e:
    HEIF_AVAILABLE = False
    print(f"Warning: pillow-heif not available. HEIC conversion will be skipped.")
    print(f"  Install with: pip install pillow-heif")
    print(f"  Error: {e}")

try:
    import cv2
    import numpy as np
    import torch
    from transformers import CLIPProcessor, CLIPModel
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False
    print(f"Warning: AI libraries not available. Basic renaming will be used.")
    print(f"  Install with: pip install opencv-python torch transformers")
    print(f"  Error: {e}")

# Configuration
DEFAULT_INPUT = "/Users/johnoshea/Library/CloudStorage/OneDrive-TCDGroup/0 TCD MyDocs/01. BMI Projects/99. Autocad Tricks/Photo adjustments/input photos"
DEFAULT_OUTPUT = "/Users/johnoshea/Library/CloudStorage/OneDrive-TCDGroup/TCD Group - TCD-1816 Batavia Coast Marina Civil & Landscaping (DEVWA)/E Engineering/E4 Photos"
TEMP_PROCESSING = "/tmp/photo_processing"
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
LOCAL_MODEL_DIR = BASE_DIR / "packaging" / "models" / "clip-vit-base-patch32"

# File extensions
MEDIA_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".mov", ".mp4"}
CONVERT_TO_JPG = {".heic", ".heif"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif"}

# Logging
MASTER_LOG = "master_photo_processing_log.csv"

# Default tags used for AI naming (prioritized for construction field cues)
DEFAULT_TAGS = [
    # Pipes / services (color-coded)
    "yellow trench protection mesh",
    "orange conduit bundle",
    "blue water pipe in trench",
    "green sewer pipe in trench",
    "concrete stormwater pipe installation",
    "pit lid and riser",

    # Earthworks / trenching
    "open trench excavation",
    "backfilling trench",
    "bulk earthworks stockpile",
    "benching or batter slope",

    # Roads / pavements
    "asphalt paving",
    "road base preparation",
    "concrete footpath pour",

    # Equipment
    "excavator digging trench",
    "roller compaction",
    "grader on road subgrade",

    # Landscaping
    "turf installation",
    "irrigation installation",
    "landscape planting beds",
]


class PhotoProcessor:
    def __init__(
        self, 
        input_dir: str, 
        output_dir: str, 
        dry_run: bool = False,
        target_format: str = "auto",
        ai_tags: Optional[List[str]] = None
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.dry_run = dry_run
        self.temp_dir = Path(TEMP_PROCESSING)
        self.target_ext = self._normalize_target_format(target_format)
        self.ai_tags = self._prepare_tags(ai_tags)
        
        # Processing logs
        self.processing_log: List[Dict] = []
        
        # Initialize AI if available
        self.ai_analyzer = None
        if AI_AVAILABLE:
            self.ai_analyzer = self._initialize_ai()
    
    def _normalize_target_format(self, target_format: str) -> Optional[str]:
        fmt = (target_format or "auto").lower()
        if fmt in {"auto", "source", "original", ""}:
            return None
        if fmt in {"jpg", "jpeg"}:
            return ".jpg"
        if fmt == "png":
            return ".png"
        return None

    def _prepare_tags(self, tags: Optional[List[str]]) -> List[str]:
        cleaned: List[str] = []
        for tag in (tags or DEFAULT_TAGS):
            text = tag.strip()
            if text and text not in cleaned:
                cleaned.append(text)
        if not cleaned:
            cleaned = list(DEFAULT_TAGS)
        # TODO: extract tag management into its own module to store/load user preferences.
        return cleaned
    
    def _initialize_ai(self):
        """Initialize AI models for photo analysis."""
        model_id = "openai/clip-vit-base-patch32"
        local_path = LOCAL_MODEL_DIR

        def load_from(path: Path, offline: bool):
            return (
                CLIPModel.from_pretrained(path, local_files_only=offline),
                CLIPProcessor.from_pretrained(path, local_files_only=offline),
            )

        try:
            if local_path.exists():
                print(f"Loading AI models from bundled cache: {local_path}")
                model, processor = load_from(local_path, offline=True)
                print("✓ AI models loaded (offline)")
            else:
                print("Bundled AI model cache not found; downloading from Hugging Face...")
                model, processor = load_from(model_id, offline=False)
                print("✓ AI models downloaded")
            return {"model": model, "processor": processor}
        except Exception as e:
            print(f"Warning: Could not load AI models: {e}")
            return None

    def _color_tags(self, image_path: Path) -> List[str]:
        """Lightweight color heuristic for trench protections and pipe colors."""
        tags: List[str] = []
        try:
            img = cv2.imread(str(image_path))
            if img is None:
                return tags
            img_small = cv2.resize(img, (320, 320))
            hsv = cv2.cvtColor(img_small, cv2.COLOR_BGR2HSV)
            total = hsv.shape[0] * hsv.shape[1]

            def ratio(mask):
                return float(cv2.countNonZero(mask)) / float(total)

            color_ranges = {
                "yellow": [(20, 80, 80), (35, 255, 255)],
                "orange": [(10, 80, 80), (19, 255, 255)],
                "blue": [(90, 80, 60), (130, 255, 255)],
                "green": [(40, 60, 40), (85, 255, 255)],
                "red1": [(0, 80, 60), (8, 255, 255)],
                "red2": [(170, 80, 60), (180, 255, 255)],
            }

            ratios = {}
            for name, (low, high) in color_ranges.items():
                mask = cv2.inRange(hsv, np.array(low), np.array(high))
                ratios[name] = ratio(mask)
            red_ratio = ratios.get("red1", 0) + ratios.get("red2", 0)

            if ratios.get("yellow", 0) > 0.02:
                tags.append("yellow_trench_protection")
            if ratios.get("orange", 0) > 0.02:
                tags.append("orange_conduit")
            if ratios.get("blue", 0) > 0.02:
                tags.append("blue_water_pipe")
            if ratios.get("green", 0) > 0.02:
                tags.append("green_sewer_pipe")
            if red_ratio > 0.02:
                tags.append("red_electrical_marker")
        except Exception:
            # Heuristic failure should not break processing
            pass
        return tags
    
    def setup_temp_directory(self):
        """Create temporary processing directory."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True)
        print(f"Created temporary processing directory: {self.temp_dir}")
    
    def cleanup_temp_directory(self):
        """Remove temporary processing directory."""
        if self.temp_dir.exists() and not self.dry_run:
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up temporary directory: {self.temp_dir}")
    
    def convert_heic_to_jpg(self, heic_path: Path, output_dir: Path, quality: int = 95) -> Optional[Path]:
        """Convert HEIC file to JPG."""
        if not HEIF_AVAILABLE:
            return None
        
        try:
            jpg_name = heic_path.stem + ".jpg"
            jpg_path = output_dir / jpg_name
            
            # Handle name conflicts
            counter = 1
            while jpg_path.exists():
                jpg_name = f"{heic_path.stem}_{counter}.jpg"
                jpg_path = output_dir / jpg_name
                counter += 1
            
            if self.dry_run:
                print(f"  [DRY RUN] Would convert {heic_path.name} → {jpg_path.name}")
                return jpg_path
            
            # Convert HEIC to JPG
            with Image.open(heic_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Preserve EXIF data
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
                
                jpg_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(jpg_path, **save_kwargs)
            
            print(f"  ✓ Converted {heic_path.name} → {jpg_path.name}")
            return jpg_path
            
        except Exception as e:
            print(f"  ✗ Error converting {heic_path.name}: {e}")
            return None
    
    def convert_image_format(self, source_path: Path, dest_path: Path) -> bool:
        """Convert an image to the configured target format."""
        if self.dry_run:
            print(f"    [DRY RUN] Would convert {source_path.name} → {dest_path.name}")
            return True

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            if source_path.suffix.lower() not in IMAGE_EXT:
                shutil.copy2(source_path, dest_path)
                return True

            with Image.open(source_path) as img:
                if dest_path.suffix.lower() in {".jpg", ".jpeg"} and img.mode != "RGB":
                    img = img.convert("RGB")
                save_format = dest_path.suffix.replace(".", "").upper() or "JPEG"
                img.save(dest_path, format=save_format)

            print(f"    ✓ Saved as: {dest_path.name}")
            return True
        except Exception as e:
            print(f"    ✗ Error converting {source_path.name} to {dest_path.suffix}: {e}")
            return False
    
    def get_file_timestamp(self, file_path: Path) -> datetime:
        """Get file timestamp from EXIF or file system."""
        try:
            # Try EXIF first for images
            if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
                with Image.open(file_path) as img:
                    exif = img.getexif()
                    if exif:
                        # Look for DateTimeOriginal
                        for tag_id, value in exif.items():
                            tag = ExifTags.TAGS.get(tag_id, tag_id)
                            if tag == "DateTimeOriginal":
                                try:
                                    return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                                except:
                                    pass
        except:
            pass
        
        # Fallback to file birth time or mtime
        stat = file_path.stat()
        timestamp = getattr(stat, 'st_birthtime', stat.st_mtime)
        return datetime.fromtimestamp(timestamp)
    
    def analyze_photo_content(self, image_path: Path) -> Dict:
        """Analyze photo content using AI for construction-specific classification."""
        color_tags = self._color_tags(image_path)

        if not self.ai_analyzer:
            tags = color_tags or ["construction"]
            return {"description": tags[0], "confidence": 0.5, "tags": tags[:3]}
        
        try:
            from PIL import Image
            
            # Load image
            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            construction_categories = self.ai_tags or DEFAULT_TAGS

            # Process image with CLIP
            inputs = self.ai_analyzer['processor'](
                text=construction_categories,
                images=image,
                return_tensors="pt",
                padding=True
            )
            
            with torch.no_grad():
                outputs = self.ai_analyzer['model'](**inputs)
                logits_per_image = outputs.logits_per_image
                probs = logits_per_image.softmax(dim=1)
            
            # Get top predictions
            top_k = min(3, len(construction_categories))
            top_indices = probs[0].topk(top_k).indices.tolist()
            confidence = probs[0][top_indices[0]].item()
            clip_tags = []
            for idx in top_indices:
                tag = construction_categories[idx]
                tag = tag.replace(" ", "_").replace("/", "_")
                if tag not in clip_tags:
                    clip_tags.append(tag)

            # Merge color heuristics first, then CLIP tags, limit to 3
            merged_tags: List[str] = []
            for tag in color_tags + clip_tags:
                if tag not in merged_tags:
                    merged_tags.append(tag)
                if len(merged_tags) >= 3:
                    break

            description = merged_tags[0] if merged_tags else "construction"
            
            print(f"    AI Analysis tags: {', '.join(merged_tags)} (top confidence: {confidence:.2f})")
            
            return {"description": description, "confidence": confidence, "tags": merged_tags}
                
        except Exception as e:
            print(f"  Warning: Could not analyze {image_path.name}: {e}")
            tags = color_tags or ["construction"]
            return {"description": tags[0], "confidence": 0.5, "tags": tags[:3]}
    
    def generate_descriptive_filename(self, original_path: Path, timestamp: datetime, analysis: Dict) -> str:
        """Generate descriptive filename based on analysis."""
        date_prefix = timestamp.strftime("%Y%m%d_%H%M")
        tags = analysis.get("tags") or []
        if tags:
            description = "_".join(tags[:3])
        else:
            description = analysis.get("description", "construction")
        is_image = original_path.suffix.lower() in IMAGE_EXT
        extension = (
            self.target_ext
            if (self.target_ext and is_image)
            else (".jpg" if original_path.suffix.lower() in CONVERT_TO_JPG else original_path.suffix.lower() or ".jpg")
        )
        
        return f"{date_prefix}_{description}{extension}"
    
    def process_single_photo(self, photo_path: Path, temp_dir: Path) -> Dict:
        """Process a single photo through the complete pipeline."""
        result = {
            "original_path": str(photo_path),
            "final_path": "",
            "timestamp": "",
            "converted": False,
            "analyzed": False,
            "success": False,
            "error": ""
        }
        
        try:
            print(f"  Processing {photo_path.name}...")
            
            current_path = photo_path
            
            # Step 1: Convert HEIC to JPG if needed
            if photo_path.suffix.lower() in CONVERT_TO_JPG:
                if not self.dry_run:
                    converted_path = self.convert_heic_to_jpg(photo_path, temp_dir)
                    if converted_path:
                        current_path = converted_path
                        result["converted"] = True
                else:
                    # In dry-run, use original HEIC file for analysis
                    print(f"  [DRY RUN] Would convert {photo_path.name} → {photo_path.stem}.jpg")
                    result["converted"] = True
                    # Keep current_path as the original HEIC for analysis
            
            # Step 2: Get timestamp
            timestamp = self.get_file_timestamp(current_path)
            result["timestamp"] = timestamp.isoformat()
            
            # Step 3: Analyze photo content (works with both HEIC and JPG)
            analysis = self.analyze_photo_content(current_path)
            result["analyzed"] = True
            
            # Step 4: Generate new filename
            new_filename = self.generate_descriptive_filename(photo_path, timestamp, analysis)
            
            # Step 5: Create date folder structure
            date_folder = timestamp.strftime("%Y%m%d")
            final_dir = temp_dir / date_folder
            final_path = final_dir / new_filename
            
            # Handle filename conflicts
            base_name, ext = new_filename.rsplit('.', 1)
            counter = 1
            while final_path.exists():
                new_filename = f"{base_name}_{counter}.{ext}"
                final_path = final_dir / new_filename
                counter += 1
            
            # Step 6: Copy to final location
            if not self.dry_run:
                final_dir.mkdir(parents=True, exist_ok=True)
                if self.target_ext and final_path.suffix.lower() != current_path.suffix.lower():
                    converted_ok = self.convert_image_format(current_path, final_path)
                    result["converted"] = result["converted"] or (final_path.suffix.lower() != photo_path.suffix.lower())
                    if not converted_ok:
                        raise RuntimeError(f"Failed to convert {photo_path.name} to {self.target_ext}")
                else:
                    if current_path != final_path:
                        shutil.copy2(current_path, final_path)
            else:
                print(f"    [DRY RUN] Would save as: {date_folder}/{new_filename}")
            
            result["final_path"] = str(final_path)
            result["converted"] = result["converted"] or (final_path.suffix.lower() != photo_path.suffix.lower())
            result["success"] = True
            
            print(f"    ✓ Processed as: {date_folder}/{new_filename}")
            
        except Exception as e:
            result["error"] = str(e)
            print(f"    ✗ Error: {e}")
        
        return result
    
    def copy_to_final_destination(self):
        """Copy organized photos from temp directory to final destination."""
        if self.dry_run:
            print(f"[DRY RUN] Would copy organized photos to: {self.output_dir}")
            return
        
        print(f"Copying organized photos to final destination: {self.output_dir}")
        
        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy each date folder
            for date_folder in self.temp_dir.iterdir():
                if date_folder.is_dir():
                    dest_folder = self.output_dir / date_folder.name
                    if dest_folder.exists():
                        # Merge with existing folder
                        for file_path in date_folder.iterdir():
                            if file_path.is_file():
                                dest_file = dest_folder / file_path.name
                                # Handle conflicts
                                counter = 1
                                while dest_file.exists():
                                    name_part, ext = file_path.name.rsplit('.', 1)
                                    dest_file = dest_folder / f"{name_part}_{counter}.{ext}"
                                    counter += 1
                                shutil.copy2(file_path, dest_file)
                    else:
                        shutil.copytree(date_folder, dest_folder)
                    
                    print(f"  ✓ Copied {date_folder.name} ({len(list(date_folder.glob('*')))} files)")
            
            print("✓ All photos copied to final destination")
            
        except Exception as e:
            print(f"✗ Error copying to final destination: {e}")
    
    def write_master_log(self):
        """Write comprehensive log of all processing."""
        log_path = self.output_dir / MASTER_LOG if not self.dry_run else Path(MASTER_LOG)
        
        try:
            with log_path.open('w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "original_filename", "original_path", "final_filename", 
                    "final_path", "date_folder", "converted_from_heic", "ai_analyzed", 
                    "success", "error"
                ])
                
                for result in self.processing_log:
                    original_path = Path(result["original_path"])
                    final_path = Path(result["final_path"]) if result["final_path"] else None
                    
                    writer.writerow([
                        datetime.now().isoformat(),
                        original_path.name,
                        result["original_path"],
                        final_path.name if final_path else "",
                        result["final_path"],
                        final_path.parent.name if final_path else "",
                        result["converted"],
                        result["analyzed"],
                        result["success"],
                        result["error"]
                    ])
            
            print(f"✓ Master log written to: {log_path}")
            
        except Exception as e:
            print(f"✗ Error writing master log: {e}")
    
    def run(self, specific_files: Optional[List[Path]] = None):
        """Execute the complete photo processing pipeline.
        
        If specific_files is provided, only those files are processed. Otherwise,
        the entire input directory is scanned.
        """
        print("=" * 60)
        print("MASTER PHOTO PROCESSING PIPELINE")
        print("=" * 60)
        print(f"Input directory: {self.input_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Dry run mode: {self.dry_run}")
        print(f"Target format: {self.target_ext or 'auto (source format)'}")
        print(f"HEIC conversion: {'Available' if HEIF_AVAILABLE else 'Not available'}")
        print(f"AI analysis: {'Available' if AI_AVAILABLE else 'Basic only'}")
        if specific_files:
            print(f"Mode: selected files only ({len(specific_files)} items)")
        else:
            print("Mode: entire input folder")
        print("-" * 60)
        
        # Validate input directory when scanning folders
        if not specific_files:
            if not self.input_dir.exists():
                print(f"✗ Input directory not found: {self.input_dir}")
                return False
        
        # Collect files to process
        if specific_files:
            media_files = []
            for p in specific_files:
                path = Path(p)
                if not path.exists():
                    print(f"✗ Skipping missing file: {path}")
                    continue
                if path.suffix.lower() not in MEDIA_EXT:
                    print(f"✗ Skipping unsupported file: {path.name}")
                    continue
                media_files.append(path)
        else:
            media_files = []
            for ext in MEDIA_EXT:
                media_files.extend(self.input_dir.glob(f"*{ext}"))
                media_files.extend(self.input_dir.glob(f"*{ext.upper()}"))
        
        # Setup temporary processing directory
        self.setup_temp_directory()
        
        try:
            if not media_files:
                print("✗ No media files found to process")
                return False
            
            print(f"Found {len(media_files)} media files to process")
            
            # Process each photo
            print("\nProcessing photos...")
            for i, photo_path in enumerate(media_files, 1):
                print(f"[{i}/{len(media_files)}] {photo_path.name}")
                result = self.process_single_photo(photo_path, self.temp_dir)
                self.processing_log.append(result)
            
            # Copy to final destination
            print(f"\nCopying to final destination...")
            self.copy_to_final_destination()
            
            # Write master log
            print(f"\nWriting processing log...")
            self.write_master_log()
            
            # Summary
            successful = sum(1 for r in self.processing_log if r["success"])
            converted = sum(1 for r in self.processing_log if r["converted"])
            errors = len(self.processing_log) - successful
            
            print("\n" + "=" * 60)
            print("PROCESSING COMPLETE")
            print("=" * 60)
            print(f"Total files processed: {len(self.processing_log)}")
            print(f"Successfully processed: {successful}")
            print(f"HEIC files converted: {converted}")
            print(f"Errors: {errors}")
            print(f"Final destination: {self.output_dir}")
            print(f"Dry run: {self.dry_run}")
            
            if not self.dry_run:
                print(f"Log file: {self.output_dir / MASTER_LOG}")
            
            return successful > 0
            
        finally:
            # Cleanup
            self.cleanup_temp_directory()


def launch_gui(default_input: str = DEFAULT_INPUT, default_output: str = DEFAULT_OUTPUT, default_target: str = "auto"):
    """Launch a minimal Tkinter GUI for drag-and-drop processing."""
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as e:
        print(f"✗ Tkinter is required for the GUI: {e}")
        return

    try:
        from tkinterdnd2 import DND_FILES, TkinterDnD
        dnd_available = True
    except Exception:
        dnd_available = False
        DND_FILES = None
        TkinterDnD = None

    class TextRedirector:
        def __init__(self, widget: tk.Text):
            self.widget = widget

        def write(self, message: str):
            if not message:
                return
            self.widget.after(0, lambda: self._append(message))

        def flush(self):
            return

        def _append(self, message: str):
            self.widget.insert(tk.END, message)
            self.widget.see(tk.END)

    class PhotoProcessorGUI:
        def __init__(self):
            base = TkinterDnD.Tk if dnd_available else tk.Tk
            self.root = base()
            self.root.title("Photo Filer")
            self.root.geometry("820x720")

            self.input_var = tk.StringVar(value=default_input)
            self.output_var = tk.StringVar(value=default_output)
            self.format_var = tk.StringVar(value=(default_target or "auto").lower())
            self.dry_run_var = tk.BooleanVar(value=False)
            self.process_folder_var = tk.BooleanVar(value=False)

            self.tags: List[str] = list(DEFAULT_TAGS)
            self.tag_vars: Dict[str, tk.BooleanVar] = {}
            self.dropped_paths: List[Path] = []

            self.log_widget: Optional[tk.Text] = None
            self.text_redirector: Optional[TextRedirector] = None

            self._build_ui()

        def _build_ui(self):
            main = ttk.Frame(self.root, padding=12)
            main.pack(fill="both", expand=True)

            ttk.Label(main, text="Drag photos or choose folders to process.", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 8))

            drop_frame = ttk.LabelFrame(main, text="Drop files or folders")
            drop_frame.pack(fill="x", pady=6)

            drop_label = tk.Label(drop_frame, text="Drop files/folders here", relief="ridge", borderwidth=2, padx=8, pady=20, background="#f2f2f2")
            drop_label.pack(fill="x", padx=8, pady=8)

            if dnd_available:
                drop_label.drop_target_register(DND_FILES)
                drop_label.dnd_bind("<<Drop>>", self._on_drop)
            else:
                ttk.Label(drop_frame, text="Drag-and-drop helper (tkinterdnd2) not found. Use Browse buttons instead.").pack(padx=8, pady=(0, 8), anchor="w")

            # Input/output selection
            path_frame = ttk.Frame(main)
            path_frame.pack(fill="x", pady=4)

            ttk.Label(path_frame, text="Input folder").grid(row=0, column=0, sticky="w", padx=(0, 6))
            input_entry = ttk.Entry(path_frame, textvariable=self.input_var)
            input_entry.grid(row=0, column=1, sticky="ew")
            ttk.Button(path_frame, text="Browse", command=self._choose_input).grid(row=0, column=2, padx=(6, 0))

            ttk.Label(path_frame, text="Output folder").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
            output_entry = ttk.Entry(path_frame, textvariable=self.output_var)
            output_entry.grid(row=1, column=1, sticky="ew", pady=(6, 0))
            ttk.Button(path_frame, text="Browse", command=self._choose_output).grid(row=1, column=2, padx=(6, 0), pady=(6, 0))

            path_frame.columnconfigure(1, weight=1)

            # Options row
            options = ttk.Frame(main)
            options.pack(fill="x", pady=10)

            ttk.Label(options, text="Output type").grid(row=0, column=0, sticky="w")
            format_box = ttk.Combobox(options, textvariable=self.format_var, values=["auto", "jpg", "png"], state="readonly", width=8)
            format_box.grid(row=0, column=1, padx=(6, 14))

            ttk.Checkbutton(options, text="Dry run (no file writes)", variable=self.dry_run_var).grid(row=0, column=2, sticky="w")
            ttk.Checkbutton(options, text="Process entire input folder", variable=self.process_folder_var).grid(row=0, column=3, sticky="w", padx=(12, 0))

            # Tag management
            tag_frame = ttk.LabelFrame(main, text="AI tags (checked items are used for naming)")
            tag_frame.pack(fill="both", expand=False, pady=6)

            canvas = tk.Canvas(tag_frame, height=200)
            scrollbar = ttk.Scrollbar(tag_frame, orient="vertical", command=canvas.yview)
            self.tag_inner = ttk.Frame(canvas)
            self.tag_inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=self.tag_inner, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
            scrollbar.pack(side="right", fill="y", pady=8)

            add_frame = ttk.Frame(main)
            add_frame.pack(fill="x", pady=(0, 10))
            self.new_tag_var = tk.StringVar()
            ttk.Entry(add_frame, textvariable=self.new_tag_var).pack(side="left", fill="x", expand=True, padx=(0, 6))
            ttk.Button(add_frame, text="Add tag", command=self._add_tag).pack(side="left")

            # Action buttons
            action_frame = ttk.Frame(main)
            action_frame.pack(fill="x", pady=(0, 8))
            self.start_btn = ttk.Button(action_frame, text="Start Processing", command=self._start_processing)
            self.start_btn.pack(side="left")
            ttk.Button(action_frame, text="Clear log", command=self._clear_log).pack(side="left", padx=(8, 0))

            # Log output
            log_frame = ttk.LabelFrame(main, text="Log")
            log_frame.pack(fill="both", expand=True)
            self.log_widget = tk.Text(log_frame, height=16, wrap="word")
            self.log_widget.pack(fill="both", expand=True, padx=6, pady=6)
            self.text_redirector = TextRedirector(self.log_widget)

            self._refresh_tags()

        def _refresh_tags(self):
            for child in self.tag_inner.winfo_children():
                child.destroy()
            self.tag_vars.clear()

            for tag in self.tags:
                row = ttk.Frame(self.tag_inner)
                var = tk.BooleanVar(value=True)
                self.tag_vars[tag] = var
                ttk.Checkbutton(row, text=tag, variable=var).pack(side="left", fill="x", expand=True)
                ttk.Button(row, text="X", width=3, command=lambda t=tag: self._remove_tag(t)).pack(side="right", padx=(6, 0))
                row.pack(fill="x", padx=4, pady=2)

        def _add_tag(self):
            tag = self.new_tag_var.get().strip()
            if not tag:
                return
            if tag not in self.tags:
                self.tags.append(tag)
            self.new_tag_var.set("")
            self._refresh_tags()

        def _remove_tag(self, tag: str):
            if tag in self.tags:
                self.tags.remove(tag)
            self._refresh_tags()

        def _choose_input(self):
            path = filedialog.askdirectory(title="Select input folder")
            if path:
                self.input_var.set(path)

        def _choose_output(self):
            path = filedialog.askdirectory(title="Select output folder")
            if path:
                self.output_var.set(path)

        def _on_drop(self, event):
            data = event.data if hasattr(event, "data") else ""
            if not data:
                return
            try:
                raw_paths = self.root.tk.splitlist(data)
            except Exception:
                raw_paths = data.split()
            if not raw_paths:
                return

            paths = [Path(p) for p in raw_paths]
            process_folder = self.process_folder_var.get()

            if process_folder:
                # In folder mode, set input to the first dropped directory or file parent
                first = paths[0]
                target_dir = first if first.is_dir() else first.parent
                self.input_var.set(str(target_dir))
                self.dropped_paths = []
                self._append_log(f"Dropped item(s); folder mode ON. Using input folder: {target_dir}\n")
                return

            files = []
            ignored_dirs = []
            for p in paths:
                if p.is_dir():
                    ignored_dirs.append(p)
                    continue
                files.append(p)

            if ignored_dirs:
                names = ", ".join(d.name for d in ignored_dirs)
                self._append_log(f"Ignored directories ({names}); enable 'Process entire input folder' to include them.\n")

            self.dropped_paths = files
            if files:
                self.input_var.set(str(files[0].parent))
                self._append_log(f"Dropped {len(files)} file(s); will process selected files only.\n")
            else:
                self._append_log("No files to process from drop.\n")

        def _append_log(self, message: str):
            if not self.log_widget:
                return
            self.log_widget.insert(tk.END, message)
            self.log_widget.see(tk.END)

        def _clear_log(self):
            if self.log_widget:
                self.log_widget.delete("1.0", tk.END)

        def _start_processing(self):
            input_dir = self.input_var.get().strip() or default_input
            output_dir = self.output_var.get().strip() or default_output

            process_folder = self.process_folder_var.get()

            if process_folder:
                if not Path(input_dir).exists():
                    messagebox.showerror("Input missing", f"Input directory does not exist:\n{input_dir}")
                    return
                selected_files: Optional[List[Path]] = None
            else:
                selected_files = [p for p in self.dropped_paths if p.exists()]
                if not selected_files:
                    messagebox.showerror("No files selected", "Drop files to process, or enable 'Process entire input folder'.")
                    return

            selected_tags = [tag for tag, var in self.tag_vars.items() if var.get()] or self.tags
            target_format = (self.format_var.get() or "auto").lower()

            self.start_btn.config(state="disabled")
            self._append_log("Starting processing...\n")

            thread = threading.Thread(
                target=self._run_processor,
                args=(input_dir, output_dir, target_format, selected_tags, self.dry_run_var.get(), selected_files),
                daemon=True
            )
            thread.start()

        def _run_processor(self, input_dir: str, output_dir: str, target_format: str, tags: List[str], dry_run: bool, selected_files: Optional[List[Path]]):
            processor = PhotoProcessor(
                input_dir=input_dir,
                output_dir=output_dir,
                dry_run=dry_run,
                target_format=target_format,
                ai_tags=tags
            )

            with contextlib.redirect_stdout(self.text_redirector), contextlib.redirect_stderr(self.text_redirector):
                success = processor.run(specific_files=selected_files)

            self.root.after(0, lambda: self._finish_run(success))

        def _finish_run(self, success: bool):
            self.start_btn.config(state="normal")
            if success:
                messagebox.showinfo("Photo filer", "Processing complete.")
            else:
                messagebox.showwarning("Photo filer", "Processing finished with errors. Check the log.")

        def run(self):
            self.root.mainloop()

    gui = PhotoProcessorGUI()
    gui.run()


def main():
    parser = argparse.ArgumentParser(description="Master photo processing pipeline for construction photos")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input directory containing photos")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output directory for organized photos")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually processing")
    parser.add_argument("--target-format", choices=["auto", "source", "original", "jpg", "jpeg", "png"], default="auto", help="Output format for processed images")
    parser.add_argument("--tags", nargs="*", help="Custom tags to use for AI naming")
    parser.add_argument("--gui", action="store_true", help="Launch drag-and-drop GUI")
    parser.add_argument("--cli", action="store_true", help="Force CLI mode (default is GUI when no arguments)")
    args = parser.parse_args()
    
    # Default to GUI if no specific mode is chosen and no input provided
    if not args.cli and not args.gui and len(sys.argv) == 1:
        launch_gui(default_input=args.input, default_output=args.output, default_target=args.target_format)
        return
    
    if args.gui:
        launch_gui(default_input=args.input, default_output=args.output, default_target=args.target_format)
        return
    
    # Create processor and run
    processor = PhotoProcessor(
        args.input, 
        args.output, 
        args.dry_run, 
        target_format=args.target_format, 
        ai_tags=args.tags
    )
    success = processor.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
