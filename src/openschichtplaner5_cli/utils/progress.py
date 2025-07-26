# openschichtplaner5-cli/src/openschichtplaner5_cli/utils/progress.py
"""
Progress indication utilities for long-running operations.
"""

import sys
import time
import threading
from typing import Optional, Callable, Any
from contextlib import contextmanager


class ProgressIndicator:
    """Simple progress indicator for CLI operations."""
    
    def __init__(self, message: str = "Working", show_spinner: bool = True):
        self.message = message
        self.show_spinner = show_spinner
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self._spinner_index = 0
    
    def start(self):
        """Start the progress indicator."""
        if self.show_spinner and sys.stdout.isatty():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._spinner_loop)
            self._thread.daemon = True
            self._thread.start()
        else:
            # Just print the message without spinner for non-TTY
            print(f"{self.message}...", flush=True)
    
    def stop(self, success_message: Optional[str] = None, error_message: Optional[str] = None):
        """Stop the progress indicator."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=0.5)
            
            # Clear the spinner line
            if sys.stdout.isatty():
                sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
                sys.stdout.flush()
        
        # Print final message
        if error_message:
            print(f"❌ {error_message}")
        elif success_message:
            print(f"✅ {success_message}")
    
    def _spinner_loop(self):
        """Run the spinner animation."""
        while not self._stop_event.is_set():
            if sys.stdout.isatty():
                spinner = self._spinner_chars[self._spinner_index]
                sys.stdout.write(f'\r{spinner} {self.message}...')
                sys.stdout.flush()
                self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
            
            time.sleep(0.1)


class ProgressBar:
    """Simple progress bar for operations with known total."""
    
    def __init__(self, total: int, description: str = "", width: int = 50):
        self.total = total
        self.current = 0
        self.description = description
        self.width = width
        self.start_time = time.time()
    
    def update(self, amount: int = 1):
        """Update progress by the given amount."""
        self.current = min(self.current + amount, self.total)
        self._draw()
    
    def set_progress(self, current: int):
        """Set absolute progress."""
        self.current = min(max(current, 0), self.total)
        self._draw()
    
    def finish(self, message: Optional[str] = None):
        """Finish the progress bar."""
        self.current = self.total
        self._draw()
        print()  # New line
        
        if message:
            print(f"✅ {message}")
    
    def _draw(self):
        """Draw the progress bar."""
        if not sys.stdout.isatty():
            return
        
        if self.total == 0:
            percent = 100
        else:
            percent = (self.current / self.total) * 100
        
        # Calculate progress bar
        filled = int(self.width * self.current / self.total) if self.total > 0 else 0
        bar = '█' * filled + '░' * (self.width - filled)
        
        # Calculate ETA
        elapsed = time.time() - self.start_time
        if self.current > 0 and self.current < self.total:
            rate = self.current / elapsed
            eta = (self.total - self.current) / rate
            eta_str = f" ETA: {self._format_time(eta)}"
        else:
            eta_str = ""
        
        # Format output
        output = f'\r{self.description} [{bar}] {self.current}/{self.total} ({percent:.1f}%){eta_str}'
        sys.stdout.write(output)
        sys.stdout.flush()
    
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


@contextmanager
def progress_context(message: str = "Working", show_spinner: bool = True):
    """Context manager for progress indication."""
    indicator = ProgressIndicator(message, show_spinner)
    try:
        indicator.start()
        yield indicator
    except Exception as e:
        indicator.stop(error_message=f"Failed: {e}")
        raise
    else:
        indicator.stop(success_message="Done")


def create_progress_bar(total: int, description: str = "") -> ProgressBar:
    """Create a progress bar for operations with known total."""
    return ProgressBar(total, description)


class StepProgress:
    """Progress tracker for multi-step operations."""
    
    def __init__(self, steps: list, description: str = "Processing"):
        self.steps = steps
        self.current_step = 0
        self.description = description
        self.start_time = time.time()
    
    def next_step(self, message: Optional[str] = None):
        """Move to the next step."""
        if self.current_step < len(self.steps):
            step_name = self.steps[self.current_step]
            display_message = message or step_name
            
            progress = (self.current_step + 1) / len(self.steps) * 100
            print(f"[{progress:5.1f}%] {display_message}")
            
            self.current_step += 1
    
    def finish(self, message: Optional[str] = None):
        """Finish all steps."""
        elapsed = time.time() - self.start_time
        final_message = message or f"Completed {len(self.steps)} steps in {elapsed:.2f}s"
        print(f"✅ {final_message}")


# Utility functions for common operations
def with_progress(func: Callable, message: str = "Working", *args, **kwargs) -> Any:
    """Execute a function with progress indication."""
    with progress_context(message) as indicator:
        return func(*args, **kwargs)


def batch_process_with_progress(items: list, process_func: Callable, 
                               description: str = "Processing items") -> list:
    """Process a list of items with progress bar."""
    results = []
    progress = create_progress_bar(len(items), description)
    
    try:
        for item in items:
            result = process_func(item)
            results.append(result)
            progress.update()
        
        progress.finish("All items processed")
        return results
        
    except Exception as e:
        progress.finish(f"Failed: {e}")
        raise