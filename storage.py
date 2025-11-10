import json
import os
import fcntl
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import contextmanager

from job import Job, JobState


class Storage:
    """Handles persistent storage of jobs"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(str(Path.home()), '.queuectl')
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.jobs_file = self.data_dir / 'jobs.json'
        self.workers_file = self.data_dir / 'workers.json'
        
        # Initialize files if they don't exist
        if not self.jobs_file.exists():
            self._write_jobs({})
        if not self.workers_file.exists():
            self._write_workers([])
    
    @contextmanager
    def _lock_file(self, file_path: Path):
        """Context manager for file locking"""
        lock_file = file_path.with_suffix('.lock')
        with open(lock_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def _read_jobs(self) -> Dict[str, dict]:
        """Read all jobs from storage"""
        with self._lock_file(self.jobs_file):
            with open(self.jobs_file, 'r') as f:
                return json.load(f)
    
    def _write_jobs(self, jobs: Dict[str, dict]):
        """Write all jobs to storage"""
        with self._lock_file(self.jobs_file):
            with open(self.jobs_file, 'w') as f:
                json.dump(jobs, f, indent=2)
    
    def _read_workers(self) -> List[dict]:
        """Read worker info from storage"""
        with self._lock_file(self.workers_file):
            with open(self.workers_file, 'r') as f:
                return json.load(f)
    
    def _write_workers(self, workers: List[dict]):
        """Write worker info to storage"""
        with self._lock_file(self.workers_file):
            with open(self.workers_file, 'w') as f:
                json.dump(workers, f, indent=2)
    
    def save_job(self, job: Job):
        """Save a job to storage"""
        jobs = self._read_jobs()
        jobs[job.id] = job.to_dict()
        self._write_jobs(jobs)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID"""
        jobs = self._read_jobs()
        job_data = jobs.get(job_id)
        if job_data:
            return Job.from_dict(job_data)
        return None
    
    def get_jobs_by_state(self, state: JobState) -> List[Job]:
        """Get all jobs with a specific state"""
        jobs = self._read_jobs()
        return [
            Job.from_dict(job_data)
            for job_data in jobs.values()
            if job_data['state'] == state.value
        ]
    
    def get_all_jobs(self) -> List[Job]:
        """Get all jobs"""
        jobs = self._read_jobs()
        return [Job.from_dict(job_data) for job_data in jobs.values()]
    
    def delete_job(self, job_id: str):
        """Delete a job from storage"""
        jobs = self._read_jobs()
        if job_id in jobs:
            del jobs[job_id]
            self._write_jobs(jobs)
    
    def get_job_counts(self) -> Dict[str, int]:
        """Get counts of jobs by state"""
        jobs = self._read_jobs()
        counts = {state.value: 0 for state in JobState}
        for job_data in jobs.values():
            counts[job_data['state']] += 1
        return counts
    
    def register_worker(self, worker_id: str, pid: int):
        """Register a worker"""
        workers = self._read_workers()
        workers.append({'id': worker_id, 'pid': pid})
        self._write_workers(workers)
    
    def unregister_worker(self, worker_id: str):
        """Unregister a worker"""
        workers = self._read_workers()
        workers = [w for w in workers if w['id'] != worker_id]
        self._write_workers(workers)
    
    def get_workers(self) -> List[dict]:
        """Get all registered workers"""
        return self._read_workers()
    
    def clear_workers(self):
        """Clear all worker registrations"""
        self._write_workers([])