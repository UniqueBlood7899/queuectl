import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional


class JobState(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD = "dead"


class Job:
    """Represents a job in the queue"""
    
    def __init__(
        self,
        command: str,
        job_id: Optional[str] = None,
        state: str = JobState.PENDING.value,
        attempts: int = 0,
        max_retries: int = 3,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        last_error: Optional[str] = None,
        output: Optional[str] = None
    ):
        self.id = job_id or str(uuid.uuid4())
        self.command = command
        self.state = state
        self.attempts = attempts
        self.max_retries = max_retries
        self.created_at = created_at or datetime.utcnow().isoformat() + 'Z'
        self.updated_at = updated_at or datetime.utcnow().isoformat() + 'Z'
        self.last_error = last_error
        self.output = output
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        return {
            'id': self.id,
            'command': self.command,
            'state': self.state,
            'attempts': self.attempts,
            'max_retries': self.max_retries,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'last_error': self.last_error,
            'output': self.output
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary"""
        return cls(
            command=data['command'],
            job_id=data['id'],
            state=data.get('state', JobState.PENDING.value),
            attempts=data.get('attempts', 0),
            max_retries=data.get('max_retries', 3),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            last_error=data.get('last_error'),
            output=data.get('output')
        )
    
    def update_state(self, state: JobState, error: Optional[str] = None, output: Optional[str] = None):
        """Update job state"""
        self.state = state.value
        self.updated_at = datetime.utcnow().isoformat() + 'Z'
        if error:
            self.last_error = error
        if output:
            self.output = output
    
    def increment_attempts(self):
        """Increment attempt counter"""
        self.attempts += 1
        self.updated_at = datetime.utcnow().isoformat() + 'Z'
    
    def should_retry(self) -> bool:
        """Check if job should be retried"""
        return self.attempts < self.max_retries
    
    def get_backoff_delay(self, base: int = 2) -> int:
        """Calculate exponential backoff delay"""
        return base ** self.attempts