from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.main import get_session
from .schemas import StorageStats, ApplicationStorageStats, SystemStorageStats, DiskInfo
from .service import get_storage_statistics, get_system_storage

storage_usage_router = APIRouter()

@storage_usage_router.get("/storage", response_model=StorageStats)
async def get_storage_usage(db: AsyncSession = Depends(get_session)):
    """
    Get storage usage statistics including both application and system storage.
    
    Returns:
        StorageStats: Object containing detailed storage information
    """
    try:
        stats = await get_storage_statistics(db)
        return stats
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving storage statistics: {str(e)}"
        )

@storage_usage_router.get("/system")
async def get_system_storage_info():
    """
    Get system storage information only.
    This endpoint is useful for quick system health checks.
    """
    try:
        return await get_system_storage()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving system storage info: {str(e)}"
        )

# Add a health check endpoint for storage
@storage_usage_router.get("/health")
async def check_storage_health():
    """
    Simple health check for storage service.
    Returns basic status and version information.
    """
    return {
        "status": "ok", 
        "service": "storage_monitoring",
        "version": "1.0.0"
    }
