"""
Basic Security Functions
Simplified version without middleware for immediate deployment
"""

import hashlib
import re
import os
import time
import logging
from typing import Dict, Any
from datetime import datetime
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Input sanitization utilities
def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not isinstance(text, str):
        return str(text)
    
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>"\'\0\r\n]', '', text)
    
    # Limit length
    return sanitized[:1000]

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging."""
    return hashlib.sha256(data.encode()).hexdigest()[:8]

# Simple rate limiter
class SimpleRateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.limit = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '30'))
    
    def is_allowed(self, client_ip: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip] 
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[client_ip]) >= self.limit:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return False
        
        # Add current request
        self.requests[client_ip].append(now)
        return True

# Security monitoring
class SecurityMonitor:
    """Monitor security events and generate alerts."""
    
    def __init__(self):
        self.failed_logins: Dict[str, int] = defaultdict(int)
        self.blocked_requests: Dict[str, int] = defaultdict(int)
    
    def log_failed_login(self, ip: str, email: str):
        """Log failed login attempt."""
        self.failed_logins[ip] += 1
        logger.warning(f"🚨 Failed login attempt from {ip} for {hash_sensitive_data(email)}")
    
    def log_blocked_request(self, ip: str, reason: str):
        """Log blocked request."""
        self.blocked_requests[ip] += 1
        logger.warning(f"🛡️ Blocked request from {ip}: {reason}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        return {
            "failed_logins_by_ip": dict(self.failed_logins),
            "blocked_requests_by_ip": dict(self.blocked_requests),
            "timestamp": datetime.now().isoformat()
        }

# Placeholder for SecurityMiddleware - will be implemented later
class SecurityMiddleware:
    """Placeholder security middleware."""
    
    def __init__(self, app):
        self.app = app
        logger.warning("⚠️ Using placeholder security middleware. Implement full version for production.")

# Initialize security monitor and rate limiter
security_monitor = SecurityMonitor()
rate_limiter = SimpleRateLimiter()