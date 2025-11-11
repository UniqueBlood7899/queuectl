from typing import List, Optional

from job import Job, JobState
from storage import Storage
from config import Config


class QueueManager:
    """Manages the job queue"""
    
    def __init__(self, storage: Storage, config: Config):
        self.storage = storage
        self.config = config
    
    def enqueue(self, command: str, job_id: Optional[str] = None, max_retries: Optional[int] = None) -> Job:
        """Add a job to the queue"""
        if max_retries is None:
            max_retries = self.config.get('max_retries')
        
        job = Job(command=command, job_id=job_id, max_retries=max_retries)
        self.storage.save_job(job)
        return job
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        return self.storage.get_job(job_id)
    
    def list_jobs(self, state: Optional[JobState] = None) -> List[Job]:
        """List jobs, optionally filtered by state"""
        if state:
            return self.storage.get_jobs_by_state(state)
        return self.storage.get_all_jobs()
    
    def get_status(self) -> dict:
        """Get queue status"""
        counts = self.storage.get_job_counts()
        workers = self.storage.get_workers()
        
        return {
            'job_counts': counts,
            'active_workers': len(workers),
            'workers': workers
        }
    
    def retry_job(self, job_id: str) -> bool:
        """Retry a job from DLQ"""
        job = self.storage.get_job(job_id)
        
        if not job:
            return False
        
        if job.state != JobState.DEAD.value:
            return False
        
        # Reset job for retry
        job.attempts = 0
        job.update_state(JobState.PENDING)
        self.storage.save_job(job)
        
        return True