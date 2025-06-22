"""
Advanced Security Middleware and Rate Limiting
Enterprise-grade security features for production deployment
"""

import time
import hashlib
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import ipaddress
import re
import os

# Security configuration
RATE_LIMIT_PER_MINUTE = int(os.environ.get('RATE_LIMIT_PER_MINUTE', '30'))
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
SUSPICIOUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'eval\s*\(',
    r'onclick\s*=',
    r'onerror\s*=',
    r'onload\s*=',
    r'\.\./.*\.\.',  # Path traversal
    r'union\s+select',  # SQL injection
    r'drop\s+table',
    r'delete\s+from',
]

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive security middleware with multiple protection layers.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.request_validator = RequestValidator()
        self.security_headers = SecurityHeaders()
        
    async def dispatch(self, request: Request, call_next):
        """Process request through security layers."""
        try:
            # 1. Rate limiting
            client_ip = self.get_client_ip(request)
            if not self.rate_limiter.is_allowed(client_ip, request.url.path):
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"}
                )
            
            # 2. Request validation
            validation_result = await self.request_validator.validate_request(request)
            if not validation_result["valid"]:
                logger.warning(f"🚨 Suspicious request blocked: {validation_result['reason']}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid request"}
                )
            
            # 3. Process request
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 4. Add security headers
            response = self.security_headers.add_headers(response)
            
            # 5. Add performance header
            response.headers["X-Process-Time"] = str(process_time)
            
            # 6. Log request
            self.log_request(request, response, process_time, client_ip)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Security middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP with proxy support."""
        # Check for real IP in headers (common with proxies/CDNs)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def log_request(self, request: Request, response, process_time: float, client_ip: str):
        """Log request for security monitoring."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "ip": client_ip,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "user_agent": request.headers.get("User-Agent", ""),
            "content_length": request.headers.get("Content-Length", "0")
        }
        
        # Log high-priority events
        if response.status_code >= 400:
            logger.warning(f"🔍 HTTP {response.status_code}: {log_data}")
        elif process_time > 5.0:  # Slow requests
            logger.warning(f"⏱️ Slow request: {log_data}")
        else:
            logger.info(f"✅ Request: {request.method} {request.url.path} - {response.status_code}")

class RateLimiter:
    """
    Advanced rate limiter with sliding window and IP-based tracking.
    """
    
    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, datetime] = {}
        self.whitelist = self._load_ip_whitelist()
    
    def _load_ip_whitelist(self) -> set:
        """Load whitelisted IPs (localhost, admin IPs, etc.)."""
        whitelist = {
            "127.0.0.1",
            "::1",
            "localhost"
        }
        
        # Add admin IPs from environment
        admin_ips = os.environ.get('ADMIN_IPS', '').split(',')
        for ip in admin_ips:
            if ip.strip():
                whitelist.add(ip.strip())
        
        return whitelist
    
    def is_allowed(self, client_ip: str, endpoint: str) -> bool:
        """Check if request is allowed based on rate limits."""
        # Skip rate limiting for whitelisted IPs
        if client_ip in self.whitelist:
            return True
        
        # Check if IP is temporarily blocked
        if client_ip in self.blocked_ips:
            if datetime.now() < self.blocked_ips[client_ip]:
                return False
            else:
                del self.blocked_ips[client_ip]
        
        # Current time
        now = time.time()
        minute_ago = now - 60
        
        # Clean old requests
        client_requests = self.requests[client_ip]
        while client_requests and client_requests[0] < minute_ago:
            client_requests.popleft()
        
        # Check rate limit
        if len(client_requests) >= RATE_LIMIT_PER_MINUTE:
            # Block IP for 5 minutes on rate limit violation
            self.blocked_ips[client_ip] = datetime.now() + timedelta(minutes=5)
            logger.warning(f"🚨 Rate limit exceeded for IP: {client_ip}")
            return False
        
        # Add current request
        client_requests.append(now)
        return True

class RequestValidator:
    """
    Request validation for security threats.
    """
    
    def __init__(self):
        self.suspicious_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SUSPICIOUS_PATTERNS]
    
    async def validate_request(self, request: Request) -> Dict[str, Any]:
        """Validate request for security threats."""
        try:
            # 1. Check request size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_REQUEST_SIZE:
                return {
                    "valid": False,
                    "reason": f"Request size {content_length} exceeds maximum {MAX_REQUEST_SIZE}"
                }
            
            # 2. Validate URL
            url_validation = self._validate_url(str(request.url))
            if not url_validation["valid"]:
                return url_validation
            
            # 3. Validate headers
            header_validation = self._validate_headers(request.headers)
            if not header_validation["valid"]:
                return header_validation
            
            # 4. Validate query parameters
            query_validation = self._validate_query_params(request.query_params)
            if not query_validation["valid"]:
                return query_validation
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"❌ Request validation error: {e}")
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}"
            }
    
    def _validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL for malicious patterns."""
        for pattern in self.suspicious_patterns:
            if pattern.search(url):
                return {
                    "valid": False,
                    "reason": f"Suspicious pattern in URL: {pattern.pattern}"
                }
        
        # Check for path traversal
        if "../" in url or "..%2F" in url:
            return {
                "valid": False,
                "reason": "Path traversal attempt detected"
            }
        
        return {"valid": True}
    
    def _validate_headers(self, headers) -> Dict[str, Any]:
        """Validate HTTP headers."""
        # Check for suspicious user agents
        user_agent = headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "masscan", "zap"]
        
        for agent in suspicious_agents:
            if agent in user_agent:
                return {
                    "valid": False,
                    "reason": f"Suspicious user agent: {agent}"
                }
        
        # Check for header injection
        for name, value in headers.items():
            if any(char in value for char in ['\r', '\n', '\0']):
                return {
                    "valid": False,
                    "reason": "Header injection attempt"
                }
        
        return {"valid": True}
    
    def _validate_query_params(self, params) -> Dict[str, Any]:
        """Validate query parameters."""
        for key, value in params.items():
            # Check for XSS attempts
            for pattern in self.suspicious_patterns:
                if pattern.search(value):
                    return {
                        "valid": False,
                        "reason": f"Suspicious pattern in parameter {key}"
                    }
        
        return {"valid": True}

class SecurityHeaders:
    """
    Security headers management.
    """
    
    def add_headers(self, response):
        """Add security headers to response."""
        # Prevent XSS attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "object-src 'none'; "
            "media-src 'self'; "
            "frame-src 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        # HSTS (HTTPS Strict Transport Security)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Remove server information
        response.headers.pop("Server", None)
        
        return response

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

# Initialize security monitor
security_monitor = SecurityMonitor()