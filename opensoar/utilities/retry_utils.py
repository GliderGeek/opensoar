"""
Retry utilities for robust network operations.

This module provides lightweight retry decorators for handling transient failures
in network requests and file operations.
"""

import time
import functools
from typing import Callable, Union, Tuple, Type


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
):
    """
    Lightweight retry decorator for handling transient failures.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Exception types to catch and retry on
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry(max_attempts=3, delay=1.0, exceptions=requests.exceptions.RequestException)
        def download_file(url):
            response = requests.get(url)
            response.raise_for_status()
            return response.content
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        raise
                    
                    print(f"Attempt {attempt + 1} failed: {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


# Predefined retry decorators for common use cases
def web_request_retry(max_attempts: int = 3):
    """Retry decorator specifically for web requests."""
    import requests
    return retry(
        max_attempts=max_attempts,
        delay=1.0,
        backoff=2.0,
        exceptions=requests.exceptions.RequestException
    )
