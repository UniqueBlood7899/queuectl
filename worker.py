import os
import signal
import subprocess
import time
import uuid
from typing import Optional

from job import Job, JobState
from storage import Storage
from config import Config


class Worker:
    """Worker that processes jobs from the queue"""
    
    def __init__(self, storage: Storage, config: Config, worker_id: Optional[str] = None):
        self.storage = storage
        self.config = config
        self.worker_id = worker_id or str(uuid.uuid4())
        self.running = False
        self.current_job: Optional[Job] = None
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        print(f"\nWorker {self.worker_id}: Received shutdown signal, finishing current job...")
        self.running = False
    
    def start(self):
        """Start processing jobs"""
        self.running = True
        self.storage.register_worker(self.worker_id, os.getpid())
        
        print(f"Worker {self.worker_id} started (PID: {os.getpid()})")
        
        try:
            while self.running:
                job = self._get_next_job()
                
                if job:
                    self._process_job(job)
                else:
                    # No jobs available, sleep briefly
                    time.sleep(self.config.get('worker_poll_interval'))
        finally:
            self.storage.unregister_worker(self.worker_id)
            print(f"Worker {self.worker_id} stopped")
    
    def _get_next_job(self) -> Optional[Job]:
        """Get the next pending job"""
        pending_jobs = self.storage.get_jobs_by_state(JobState.PENDING)
        
        if not pending_jobs:
            # Check for failed jobs that need retry
            failed_jobs = self.storage.get_jobs_by_state(JobState.FAILED)
            for job in failed_jobs:
                if job.should_retry():
                    # Check if enough time has passed for retry
                    backoff = job.get_backoff_delay(self.config.get('backoff_base'))
                    # For simplicity, retry immediately (in production, check time)
                    return job
            return None
        
        # Get first pending job
        job = pending_jobs[0]
        
        # Mark as processing to prevent other workers from picking it up
        job.update_state(JobState.PROCESSING)
        self.storage.save_job(job)
        
        return job
    
    def _process_job(self, job: Job):
        """Process a single job"""
        self.current_job = job
        print(f"Worker {self.worker_id}: Processing job {job.id}")
        
        try:
            # Execute the command
            result = subprocess.run(
                job.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                # Job succeeded
                job.update_state(JobState.COMPLETED, output=result.stdout)
                print(f"Worker {self.worker_id}: Job {job.id} completed successfully")
            else:
                # Job failed
                error = result.stderr or f"Command exited with code {result.returncode}"
                self._handle_job_failure(job, error)
        
        except subprocess.TimeoutExpired:
            self._handle_job_failure(job, "Job timed out")
        
        except Exception as e:
            self._handle_job_failure(job, str(e))
        
        finally:
            self.storage.save_job(job)
            self.current_job = None
    
    def _handle_job_failure(self, job: Job, error: str):
        """Handle job failure with retry logic"""
        job.increment_attempts()
        
        if job.should_retry():
            job.update_state(JobState.FAILED, error=error)
            backoff = job.get_backoff_delay(self.config.get('backoff_base'))
            print(f"Worker {self.worker_id}: Job {job.id} failed (attempt {job.attempts}/{job.max_retries}), "
                  f"will retry in {backoff}s. Error: {error}")
            
            # Sleep for backoff period
            time.sleep(backoff)
            
            # Move back to pending for retry
            job.update_state(JobState.PENDING, error=error)
        else:
            # Max retries exceeded, move to DLQ
            job.update_state(JobState.DEAD, error=error)
            print(f"Worker {self.worker_id}: Job {job.id} moved to DLQ after {job.attempts} attempts. "
                  f"Error: {error}")