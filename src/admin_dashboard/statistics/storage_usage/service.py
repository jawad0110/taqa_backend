import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from src.db.models import ProductImage
import asyncio
import platform

async def get_system_storage() -> Dict:
    """Get system storage information with proper error handling"""
    try:
        # Get disk usage using shutil (cross-platform)
        if platform.system() == 'Windows':
            total, used, free = shutil.disk_usage('C:\\')
        else:
            total, used, free = shutil.disk_usage('/')
        
        disks = []
        try:
            # Get detailed disk info - different commands for different OS
            if platform.system() == 'Windows':
                # Use dir command for Windows
                result = subprocess.run(['dir', 'C:\\'], capture_output=True, text=True, shell=True)
                # For Windows, we'll use a simpler approach
                disks.append({
                    'filesystem': 'C:',
                    'size': f"{round(total / (1024**3), 1)}G",
                    'used': f"{round(used / (1024**3), 1)}G",
                    'available': f"{round(free / (1024**3), 1)}G",
                    'use_percentage': f"{round((used / total) * 100, 1)}",
                    'mounted_on': 'C:\\'
                })
            else:
                # Use df command for Unix-like systems
                df_output = subprocess.check_output(
                    ['df', '-h'], 
                    stderr=subprocess.STDOUT
                ).decode('utf-8')
                
                # Parse df output (skip header line)
                for line in df_output.split('\n')[1:]:
                    if not line.strip():
                        continue
                        
                    parts = line.split()
                    if len(parts) >= 6:
                        disk_info = {
                            'filesystem': parts[0],
                            'size': parts[1],
                            'used': parts[2],
                            'available': parts[3],
                            'use_percentage': parts[4].replace('%', ''),
                            'mounted_on': ' '.join(parts[5:])  # Handle paths with spaces
                        }
                        disks.append(disk_info)
        except Exception as e:
            # Fallback to shutil if detailed commands fail
            print(f"Warning: Could not get detailed disk info: {str(e)}")
            
        if not disks:
            # Add root filesystem info if no disks were found
            root_path = 'C:\\' if platform.system() == 'Windows' else '/'
            disks.append({
                'filesystem': root_path,
                'size': f"{round(total / (1024**3), 1)}G",
                'used': f"{round(used / (1024**3), 1)}G",
                'available': f"{round(free / (1024**3), 1)}G",
                'use_percentage': f"{round((used / total) * 100, 1)}",
                'mounted_on': root_path
            })
            
        return {
            'total_gb': round(total / (1024**3), 2),
            'used_gb': round(used / (1024**3), 2),
            'free_gb': round(free / (1024**3), 2),
            'use_percentage': round((used / total) * 100, 1) if total > 0 else 0,
            'disks': disks
        }
        
    except Exception as e:
        print(f"Error getting system storage: {str(e)}")
        # Return a safe default if everything fails
        return {
            'total_gb': 0,
            'used_gb': 0,
            'free_gb': 0,
            'use_percentage': 0,
            'disks': []
        }


async def get_application_storage(db: AsyncSession) -> Dict:
    """Get application-specific storage information"""
    try:
        # Get total number of images from database
        result = await db.execute(select(func.count()).select_from(ProductImage))
        total_images = result.scalar() or 0
        
        # Calculate total storage size and average size
        images_dir = Path("static/images/products")
        total_size_bytes = 0
        
        if images_dir.exists() and images_dir.is_dir():
            for file_path in images_dir.rglob("*"):
                try:
                    if file_path.is_file():
                        total_size_bytes += file_path.stat().st_size
                except (PermissionError, OSError) as e:
                    print(f"Warning: Could not access {file_path}: {str(e)}")
                    continue
        
        total_storage_mb = total_size_bytes / (1024 * 1024)
        average_size_kb = (total_size_bytes / total_images) / 1024 if total_images > 0 else 0
        
        return {
            'total_images': total_images,
            'total_storage_mb': round(total_storage_mb, 2),
            'average_size_kb': round(average_size_kb, 2),
            'storage_path': str(images_dir.absolute())
        }
        
    except Exception as e:
        print(f"Error getting application storage: {str(e)}")
        return {
            'total_images': 0,
            'total_storage_mb': 0,
            'average_size_kb': 0,
            'storage_path': 'N/A'
        }


async def get_storage_statistics(db: AsyncSession) -> Dict:
    """Get combined storage statistics with error handling"""
    try:
        # Get both system and application storage in parallel
        system_storage, app_storage = await asyncio.gather(
            get_system_storage(),
            get_application_storage(db)
        )
        
        return {
            'application': app_storage,
            'system': system_storage
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get storage statistics: {str(e)}"
        )
