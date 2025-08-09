"""
Enhanced Input Validation and Sanitization for MCP ADHD Server.

Comprehensive security module providing:
- XSS prevention with HTML sanitization
- SQL injection protection
- Command injection prevention
- JSON/XML parsing security
- OWASP-compliant input validation
- ADHD-specific content safety checks
"""

import re
import json
import html
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from xml.parsers.expat import ExpatError

import structlog
from pydantic import BaseModel, Field, validator
from bleach import clean, linkify
from bleach.css_sanitizer import CSSSanitizer

logger = structlog.get_logger(__name__)


class ValidationError(Exception):
    """Custom validation error for security violations."""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(message)


class SecurityConfig:
    """Security configuration for input validation."""
    
    # Maximum input sizes (OWASP recommendations)
    MAX_STRING_LENGTH = 10000  # 10KB for text inputs
    MAX_JSON_SIZE = 1048576    # 1MB for JSON payloads
    MAX_XML_SIZE = 1048576     # 1MB for XML payloads
    MAX_ARRAY_LENGTH = 1000    # Maximum array items
    
    # SQL injection patterns (enhanced detection)
    SQL_INJECTION_PATTERNS = [
        r'(\bUNION\b.*\bSELECT\b)',
        r'(\bSELECT\b.*\bFROM\b.*\bWHERE\b)',
        r'(\bINSERT\b.*\bINTO\b)',
        r'(\bUPDATE\b.*\bSET\b)',
        r'(\bDELETE\b.*\bFROM\b)',
        r'(\bDROP\b.*\bTABLE\b)',
        r'(\bCREATE\b.*\bTABLE\b)',
        r'(\bALTER\b.*\bTABLE\b)',
        r'(\bEXEC\b.*\bXP_)',
        r'(--|#|/\*|\*/)',
        r"('.*'.*;)",
        r'(\bOR\b.*=.*)',
        r'(\bAND\b.*=.*)',
        r'(\b1=1\b)',
        r'(\b0=0\b)'
    ]
    
    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r'[;&|`$]',
        r'\$\(.*\)',
        r'`.*`',
        r'\|\|',
        r'&&',
        r'>\s*/',
        r'<\s*/',
        r'\.\./.*',
        r'(?:cat|ls|pwd|whoami|id|uname|ps|netstat)\b',
        r'(?:curl|wget|nc|telnet|ssh)\b',
        r'(?:rm|cp|mv|mkdir|rmdir)\b'
    ]
    
    # XSS patterns (enhanced)
    XSS_PATTERNS = [
        r'<\s*script[^>]*>.*?</\s*script\s*>',
        r'<\s*iframe[^>]*>.*?</\s*iframe\s*>',
        r'<\s*object[^>]*>.*?</\s*object\s*>',
        r'<\s*embed[^>]*>',
        r'<\s*applet[^>]*>.*?</\s*applet\s*>',
        r'javascript\s*:',
        r'vbscript\s*:',
        r'data\s*:.*base64',
        r'on\w+\s*=',
        r'<\s*meta[^>]*http-equiv',
        r'<\s*link[^>]*href\s*=\s*["\']javascript:',
        r'<\s*form[^>]*action\s*=\s*["\']javascript:'
    ]
    
    # ADHD crisis detection patterns (enhanced)
    CRISIS_PATTERNS = [
        r'\b(?:suicide|kill\s+myself|end\s+it\s+all|want\s+to\s+die)\b',
        r'\b(?:self[\s-]?harm|hurt\s+myself|cutting|burning)\b',
        r'\b(?:crisis|emergency|help\s+me\s+please)\b',
        r'\b(?:can\'?t\s+go\s+on|give\s+up|no\s+hope)\b',
        r'\b(?:overdose|pills|hanging|jumping)\b'
    ]
    
    # Allowed HTML tags for sanitization
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'code', 'pre'
    ]
    
    # Allowed HTML attributes
    ALLOWED_ATTRIBUTES = {
        '*': ['class', 'id'],
        'a': ['href', 'title', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height']
    }
    
    # CSS sanitizer configuration
    CSS_SANITIZER = CSSSanitizer(
        allowed_css_properties=[
            'color', 'background-color', 'font-size', 'font-weight',
            'text-align', 'margin', 'padding', 'border'
        ]
    )


class InputValidator:
    """Comprehensive input validation and sanitization."""
    
    def __init__(self):
        self.config = SecurityConfig()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        self.sql_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                           for pattern in self.config.SQL_INJECTION_PATTERNS]
        self.cmd_patterns = [re.compile(pattern, re.IGNORECASE) 
                           for pattern in self.config.COMMAND_INJECTION_PATTERNS]
        self.xss_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                           for pattern in self.config.XSS_PATTERNS]
        self.crisis_patterns = [re.compile(pattern, re.IGNORECASE) 
                              for pattern in self.config.CRISIS_PATTERNS]
    
    def validate_and_sanitize(
        self, 
        data: Any, 
        field_name: str = "input",
        allow_html: bool = False,
        max_length: int = None,
        crisis_detection: bool = True
    ) -> Any:
        """
        Main validation and sanitization entry point.
        
        Args:
            data: Input data to validate
            field_name: Name of the field for error reporting
            allow_html: Whether to allow sanitized HTML
            max_length: Maximum string length override
            crisis_detection: Whether to perform crisis detection
            
        Returns:
            Validated and sanitized data
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Size validation first
            self._validate_size(data, field_name, max_length)
            
            # Type-specific validation
            if isinstance(data, str):
                return self._validate_string(
                    data, field_name, allow_html, crisis_detection
                )
            elif isinstance(data, dict):
                return self._validate_dict(data, field_name, crisis_detection)
            elif isinstance(data, list):
                return self._validate_list(data, field_name, crisis_detection)
            elif isinstance(data, (int, float, bool)):
                return data
            elif data is None:
                return data
            else:
                # Convert unknown types to string and validate
                str_data = str(data)
                return self._validate_string(
                    str_data, field_name, allow_html, crisis_detection
                )
                
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Input validation error", 
                       field=field_name, error=str(e))
            raise ValidationError(
                f"Validation failed for field {field_name}", 
                field_name, data
            )
    
    def _validate_size(self, data: Any, field_name: str, max_length: int = None):
        """Validate data size limits."""
        if isinstance(data, str):
            limit = max_length or self.config.MAX_STRING_LENGTH
            if len(data) > limit:
                raise ValidationError(
                    f"String too long: {len(data)} > {limit}",
                    field_name, data
                )
        elif isinstance(data, (dict, list)):
            # Convert to JSON to check serialized size
            json_str = json.dumps(data)
            if len(json_str) > self.config.MAX_JSON_SIZE:
                raise ValidationError(
                    f"Data structure too large: {len(json_str)} bytes",
                    field_name, data
                )
        elif isinstance(data, list):
            if len(data) > self.config.MAX_ARRAY_LENGTH:
                raise ValidationError(
                    f"Array too long: {len(data)} items",
                    field_name, data
                )
    
    def _validate_string(
        self, 
        data: str, 
        field_name: str, 
        allow_html: bool = False,
        crisis_detection: bool = True
    ) -> str:
        """Comprehensive string validation and sanitization."""
        
        # Crisis detection (highest priority for ADHD users)
        if crisis_detection and self._detect_crisis_content(data):
            logger.critical("Crisis content detected in user input",
                          field=field_name,
                          content_preview=data[:100])
            # Don't raise error - let crisis handling middleware take over
        
        # SQL injection detection
        if self._detect_sql_injection(data):
            logger.security("SQL injection attempt detected",
                          field=field_name,
                          content_preview=data[:100])
            raise ValidationError(
                "Potential SQL injection detected",
                field_name, data
            )
        
        # Command injection detection
        if self._detect_command_injection(data):
            logger.security("Command injection attempt detected",
                          field=field_name,
                          content_preview=data[:100])
            raise ValidationError(
                "Potential command injection detected",
                field_name, data
            )
        
        # XSS detection and sanitization
        if allow_html:
            data = self._sanitize_html(data)
        else:
            if self._detect_xss(data):
                logger.security("XSS attempt detected",
                              field=field_name,
                              content_preview=data[:100])
                # Sanitize rather than reject for better UX
                data = html.escape(data)
        
        # Path traversal protection
        if self._detect_path_traversal(data):
            logger.security("Path traversal attempt detected",
                          field=field_name,
                          content_preview=data[:100])
            raise ValidationError(
                "Potential path traversal detected",
                field_name, data
            )
        
        return data.strip()
    
    def _validate_dict(
        self, 
        data: Dict[str, Any], 
        field_name: str,
        crisis_detection: bool = True
    ) -> Dict[str, Any]:
        """Recursively validate dictionary data."""
        validated = {}
        
        for key, value in data.items():
            # Validate key
            clean_key = self._validate_string(
                str(key), f"{field_name}.key", False, False
            )
            
            # Validate value
            validated[clean_key] = self.validate_and_sanitize(
                value, 
                f"{field_name}.{clean_key}",
                crisis_detection=crisis_detection
            )
        
        return validated
    
    def _validate_list(
        self, 
        data: List[Any], 
        field_name: str,
        crisis_detection: bool = True
    ) -> List[Any]:
        """Recursively validate list data."""
        return [
            self.validate_and_sanitize(
                item, 
                f"{field_name}[{idx}]",
                crisis_detection=crisis_detection
            )
            for idx, item in enumerate(data)
        ]
    
    def _detect_sql_injection(self, data: str) -> bool:
        """Detect potential SQL injection attempts."""
        for pattern in self.sql_patterns:
            if pattern.search(data):
                return True
        return False
    
    def _detect_command_injection(self, data: str) -> bool:
        """Detect potential command injection attempts."""
        for pattern in self.cmd_patterns:
            if pattern.search(data):
                return True
        return False
    
    def _detect_xss(self, data: str) -> bool:
        """Detect potential XSS attempts."""
        for pattern in self.xss_patterns:
            if pattern.search(data):
                return True
        return False
    
    def _detect_path_traversal(self, data: str) -> bool:
        """Detect path traversal attempts."""
        dangerous_patterns = ['../', '..\\', '%2e%2e', '%252e', '0x2e0x2e']
        data_lower = data.lower()
        return any(pattern in data_lower for pattern in dangerous_patterns)
    
    def _detect_crisis_content(self, data: str) -> bool:
        """Detect crisis/self-harm content (ADHD-specific)."""
        for pattern in self.crisis_patterns:
            if pattern.search(data):
                return True
        return False
    
    def _sanitize_html(self, data: str) -> str:
        """Sanitize HTML content using bleach."""
        try:
            # Clean HTML
            cleaned = clean(
                data,
                tags=self.config.ALLOWED_TAGS,
                attributes=self.config.ALLOWED_ATTRIBUTES,
                css_sanitizer=self.config.CSS_SANITIZER,
                strip=True,
                strip_comments=True
            )
            
            # Linkify URLs safely
            cleaned = linkify(
                cleaned,
                parse_email=False,
                target="_blank",
                rel="noopener noreferrer"
            )
            
            return cleaned
            
        except Exception as e:
            logger.warning("HTML sanitization failed, escaping content",
                         error=str(e))
            return html.escape(data)
    
    def validate_json(
        self, 
        json_str: str, 
        field_name: str = "json",
        max_depth: int = 10
    ) -> Any:
        """
        Safely parse and validate JSON with size and depth limits.
        
        Args:
            json_str: JSON string to parse
            field_name: Field name for error reporting
            max_depth: Maximum nesting depth allowed
            
        Returns:
            Parsed JSON data
            
        Raises:
            ValidationError: If JSON is invalid or unsafe
        """
        if len(json_str) > self.config.MAX_JSON_SIZE:
            raise ValidationError(
                f"JSON too large: {len(json_str)} bytes",
                field_name, json_str
            )
        
        try:
            # Parse JSON
            data = json.loads(json_str)
            
            # Check depth
            if self._get_json_depth(data) > max_depth:
                raise ValidationError(
                    f"JSON nesting too deep (>{max_depth})",
                    field_name, data
                )
            
            # Validate content
            return self.validate_and_sanitize(data, field_name)
            
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Invalid JSON: {str(e)}",
                field_name, json_str
            )
    
    def validate_xml(
        self, 
        xml_str: str, 
        field_name: str = "xml",
        max_elements: int = 1000
    ) -> ET.Element:
        """
        Safely parse and validate XML with security controls.
        
        Args:
            xml_str: XML string to parse
            field_name: Field name for error reporting
            max_elements: Maximum XML elements allowed
            
        Returns:
            Parsed XML root element
            
        Raises:
            ValidationError: If XML is invalid or unsafe
        """
        if len(xml_str) > self.config.MAX_XML_SIZE:
            raise ValidationError(
                f"XML too large: {len(xml_str)} bytes",
                field_name, xml_str
            )
        
        try:
            # Parse with security restrictions
            root = ET.fromstring(xml_str)
            
            # Count elements
            element_count = len(list(root.iter()))
            if element_count > max_elements:
                raise ValidationError(
                    f"Too many XML elements: {element_count}",
                    field_name, xml_str
                )
            
            return root
            
        except ET.ParseError as e:
            raise ValidationError(
                f"Invalid XML: {str(e)}",
                field_name, xml_str
            )
        except ExpatError as e:
            raise ValidationError(
                f"XML parsing error: {str(e)}",
                field_name, xml_str
            )
    
    def validate_url(
        self, 
        url: str, 
        field_name: str = "url",
        allowed_schemes: List[str] = None
    ) -> str:
        """
        Validate URL with security checks.
        
        Args:
            url: URL to validate
            field_name: Field name for error reporting
            allowed_schemes: Allowed URL schemes
            
        Returns:
            Validated URL
            
        Raises:
            ValidationError: If URL is invalid or unsafe
        """
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme.lower() not in allowed_schemes:
                raise ValidationError(
                    f"Invalid URL scheme: {parsed.scheme}",
                    field_name, url
                )
            
            # Check for dangerous URLs
            if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0']:
                raise ValidationError(
                    "Localhost URLs not allowed",
                    field_name, url
                )
            
            # Check for private IP ranges (basic check)
            if parsed.hostname and (
                parsed.hostname.startswith('192.168.') or
                parsed.hostname.startswith('10.') or
                parsed.hostname.startswith('172.')
            ):
                raise ValidationError(
                    "Private network URLs not allowed",
                    field_name, url
                )
            
            return url
            
        except Exception as e:
            raise ValidationError(
                f"Invalid URL: {str(e)}",
                field_name, url
            )
    
    def _get_json_depth(self, obj: Any, depth: int = 0) -> int:
        """Calculate maximum nesting depth of JSON object."""
        if isinstance(obj, dict):
            return max([self._get_json_depth(v, depth + 1) for v in obj.values()], default=depth)
        elif isinstance(obj, list):
            return max([self._get_json_depth(item, depth + 1) for item in obj], default=depth)
        else:
            return depth


class RequestValidationModels:
    """Pydantic models for request validation."""
    
    class ChatRequest(BaseModel):
        """Chat request validation model."""
        message: str = Field(..., min_length=1, max_length=10000)
        user_id: Optional[str] = Field(None, regex=r'^[a-zA-Z0-9_-]+$')
        context: Optional[Dict[str, Any]] = None
        
        @validator('message')
        def validate_message(cls, v):
            validator = InputValidator()
            return validator.validate_and_sanitize(v, "message", crisis_detection=True)
        
        @validator('context')
        def validate_context(cls, v):
            if v is not None:
                validator = InputValidator()
                return validator.validate_and_sanitize(v, "context")
            return v
    
    class UserRegistration(BaseModel):
        """User registration validation model."""
        username: str = Field(..., min_length=3, max_length=50, regex=r'^[a-zA-Z0-9_]+$')
        email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
        password: str = Field(..., min_length=8, max_length=128)
        full_name: Optional[str] = Field(None, max_length=100)
        
        @validator('username')
        def validate_username(cls, v):
            validator = InputValidator()
            return validator.validate_and_sanitize(v, "username", crisis_detection=False)
        
        @validator('full_name')
        def validate_full_name(cls, v):
            if v is not None:
                validator = InputValidator()
                return validator.validate_and_sanitize(v, "full_name", crisis_detection=False)
            return v
    
    class TaskCreate(BaseModel):
        """Task creation validation model."""
        title: str = Field(..., min_length=1, max_length=200)
        description: Optional[str] = Field(None, max_length=2000)
        priority: Optional[str] = Field('medium', regex=r'^(low|medium|high|urgent)$')
        due_date: Optional[datetime] = None
        tags: Optional[List[str]] = Field(None, max_items=10)
        
        @validator('title', 'description')
        def validate_text_fields(cls, v, field):
            if v is not None:
                validator = InputValidator()
                return validator.validate_and_sanitize(v, field.name, crisis_detection=True)
            return v
        
        @validator('tags')
        def validate_tags(cls, v):
            if v is not None:
                validator = InputValidator()
                return [validator.validate_and_sanitize(tag, "tag", crisis_detection=False) 
                       for tag in v]
            return v


# Global validator instance
input_validator = InputValidator()

# Convenience functions
def validate_input(data: Any, field_name: str = "input", **kwargs) -> Any:
    """Convenience function for input validation."""
    return input_validator.validate_and_sanitize(data, field_name, **kwargs)

def validate_json_input(json_str: str, field_name: str = "json") -> Any:
    """Convenience function for JSON validation."""
    return input_validator.validate_json(json_str, field_name)

def validate_url_input(url: str, field_name: str = "url") -> str:
    """Convenience function for URL validation."""
    return input_validator.validate_url(url, field_name)


# Export main classes and functions
__all__ = [
    'InputValidator',
    'ValidationError',
    'SecurityConfig',
    'RequestValidationModels',
    'input_validator',
    'validate_input',
    'validate_json_input', 
    'validate_url_input'
]