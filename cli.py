import json
import sys
import os
from multiprocessing import Process
from typing import Optional

import click
from tabulate import tabulate

from job import Job, JobState
from queue_manager import QueueManager  # Changed from 'queue'
from worker import Worker
from storage import Storage
from config import Config
from utils import kill_process, is_process_running


# Initialize global instances
storage = Storage()
config = Config()
queue_manager = QueueManager(storage, config)


@click.group()
def cli():
    """QueueCTL - CLI-based background job queue system"""
    pass


@cli.command()
@click.argument('job_spec')
def enqueue(job_spec: str):
    """Enqueue a new job
    
    Example: queuectl enqueue '{"id":"job1","command":"sleep 2"}'
    """
    try:
        spec = json.loads(job_spec)
        
        if 'command' not in spec:
            click.echo("Error: 'command' field is required", err=True)
            sys.exit(1)
        
        job = queue_manager.enqueue(
            command=spec['command'],
            job_id=spec.get('id'),
            max_retries=spec.get('max_retries')
        )
        
        click.echo(f"Job enqueued successfully: {job.id}")
        click.echo(json.dumps(job.to_dict(), indent=2))
    
    except json.JSONDecodeError:
        click.echo("Error: Invalid JSON format", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.group()
def worker():
    """Worker management commands"""
    pass


def _worker_process():
    """Worker process function"""
    w = Worker(Storage(), Config())
    w.start()


@worker.command('start')
@click.option('--count', default=1, help='Number of workers to start')
def worker_start(count: int):
    """Start worker processes"""
    # Clean up stale workers
    workers = storage.get_workers()
    for w in workers:
        if not is_process_running(w['pid']):
            storage.unregister_worker(w['id'])
    
    processes = []
    
    for i in range(count):
        p = Process(target=_worker_process)
        p.start()
        processes.append(p)
        click.echo(f"Started worker {i+1}/{count} (PID: {p.pid})")
    
    click.echo(f"\n{count} worker(s) started successfully")
    click.echo("Press Ctrl+C to stop all workers")
    
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        click.echo("\nStopping workers...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        click.echo("All workers stopped")


@worker.command('stop')
def worker_stop():
    """Stop all running workers"""
    workers = storage.get_workers()
    
    if not workers:
        click.echo("No workers are currently running")
        return
    
    stopped = 0
    for w in workers:
        if kill_process(w['pid']):
            storage.unregister_worker(w['id'])
            stopped += 1
    
    click.echo(f"Stopped {stopped} worker(s)")


@cli.command()
def status():
    """Show queue status"""
    status_info = queue_manager.get_status()
    
    click.echo("=== Queue Status ===\n")
    
    # Job counts
    click.echo("Jobs by State:")
    job_table = [
        [state, count]
        for state, count in status_info['job_counts'].items()
    ]
    click.echo(tabulate(job_table, headers=['State', 'Count'], tablefmt='grid'))
    
    # Workers
    click.echo(f"\nActive Workers: {status_info['active_workers']}")
    
    if status_info['workers']:
        worker_table = [
            [w['id'][:8], w['pid'], '✓' if is_process_running(w['pid']) else '✗']
            for w in status_info['workers']
        ]
        click.echo(tabulate(worker_table, headers=['Worker ID', 'PID', 'Running'], tablefmt='grid'))


@cli.command('list')
@click.option('--state', type=click.Choice([s.value for s in JobState]), help='Filter by state')
def list_jobs(state: Optional[str]):
    """List jobs"""
    if state:
        jobs = queue_manager.list_jobs(JobState(state))
    else:
        jobs = queue_manager.list_jobs()
    
    if not jobs:
        click.echo("No jobs found")
        return
    
    # Sort by created_at
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    
    table = [
        [
            j.id[:8],
            j.command[:30] + ('...' if len(j.command) > 30 else ''),
            j.state,
            f"{j.attempts}/{j.max_retries}",
            j.created_at[:19]
        ]
        for j in jobs
    ]
    
    click.echo(tabulate(
        table,
        headers=['Job ID', 'Command', 'State', 'Attempts', 'Created'],
        tablefmt='grid'
    ))


@cli.group()
def dlq():
    """Dead Letter Queue management"""
    pass


@dlq.command('list')
def dlq_list():
    """List jobs in DLQ"""
    jobs = queue_manager.list_jobs(JobState.DEAD)
    
    if not jobs:
        click.echo("No jobs in DLQ")
        return
    
    table = [
        [
            j.id[:8],
            j.command[:30] + ('...' if len(j.command) > 30 else ''),
            j.attempts,
            j.last_error[:40] + ('...' if j.last_error and len(j.last_error) > 40 else '') if j.last_error else ''
        ]
        for j in jobs
    ]
    
    click.echo(tabulate(
        table,
        headers=['Job ID', 'Command', 'Attempts', 'Error'],
        tablefmt='grid'
    ))


@dlq.command('retry')
@click.argument('job_id')
def dlq_retry(job_id: str):
    """Retry a job from DLQ"""
    if queue_manager.retry_job(job_id):
        click.echo(f"Job {job_id} moved back to queue for retry")
    else:
        click.echo(f"Job {job_id} not found in DLQ or cannot be retried", err=True)
        sys.exit(1)


@cli.group('config')  # Add 'config' as the command name
def config_cmd():
    """Configuration management"""
    pass


@config_cmd.command('get')
@click.argument('key', required=False)
def config_get(key: Optional[str]):
    """Get configuration value(s)"""
    if key:
        value = config.get(key)
        click.echo(f"{key}: {value}")
    else:
        all_config = config.get_all()
        click.echo(json.dumps(all_config, indent=2))


@config_cmd.command('set')
@click.argument('key')
@click.argument('value')
def config_set(key: str, value: str):
    """Set configuration value"""
    # Try to convert to int if possible
    try:
        value = int(value)
    except ValueError:
        pass
    
    config.set(key, value)
    click.echo(f"Configuration updated: {key} = {value}")


if __name__ == '__main__':
    cli()