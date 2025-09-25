from pydantic import BaseModel
from typing import List

class DiskInfo(BaseModel):
    filesystem: str
    size: str
    used: str
    available: str
    use_percentage: str
    mounted_on: str

class ApplicationStorageStats(BaseModel):
    total_images: int
    total_storage_mb: float
    average_size_kb: float
    storage_path: str

class SystemStorageStats(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    use_percentage: float
    disks: List[DiskInfo]

class StorageStats(BaseModel):
    application: ApplicationStorageStats
    system: SystemStorageStats
