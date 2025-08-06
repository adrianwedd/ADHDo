"""
Intelligent Feature Detection System

Advanced code analysis and pattern matching system for detecting feature
completions with high accuracy and confidence scoring.
"""

import ast
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class FeaturePattern:
    """Pattern definition for feature detection."""
    name: str
    category: str
    required_files: List[str]
    optional_files: List[str]
    required_classes: List[str]
    required_methods: List[str]
    required_imports: List[str]
    test_patterns: List[str]
    documentation_patterns: List[str]
    commit_patterns: List[str]
    completion_indicators: Dict[str, float]  # indicator -> weight


@dataclass
class DetectionResult:
    """Result of feature detection analysis."""
    feature_name: str
    confidence_score: float
    completion_status: str
    evidence: Dict[str, Any]
    false_positive_score: float
    detection_method: str


class FeatureDetector:
    """
    Intelligent feature completion detection system.
    
    Uses multi-factor analysis to determine if features are completed:
    - Code structure analysis
    - Test coverage detection  
    - Documentation presence
    - Commit message analysis
    - File system patterns
    """
    
    def __init__(self, repository_root: Optional[str] = None):
        """Initialize feature detector."""
        self.repository_root = Path(repository_root) if repository_root else Path.cwd()
        self.patterns = self._load_feature_patterns()
        self.analysis_cache: Dict[str, Any] = {}
        
        logger.info(
            "Feature detector initialized",
            repository_root=str(self.repository_root),
            pattern_count=len(self.patterns)
        )
    
    def _load_feature_patterns(self) -> Dict[str, FeaturePattern]:
        """Load feature detection patterns for the ADHDo project."""
        patterns = {
            'mcp_client': FeaturePattern(
                name='MCP Client Implementation',
                category='integration',
                required_files=[
                    'src/mcp_client/__init__.py',
                    'src/mcp_client/client.py',
                    'src/mcp_client/auth.py'
                ],
                optional_files=[
                    'src/mcp_client/browser_auth.py',
                    'src/mcp_client/workflow.py',
                    'src/mcp_client/models.py',
                    'src/mcp_client/registry.py'
                ],
                required_classes=[
                    'MCPClient',
                    'AuthManager'
                ],
                required_methods=[
                    'connect',
                    'authenticate',
                    'list_tools',
                    'call_tool'
                ],
                required_imports=[
                    'mcp',
                    'anthropic',
                    'httpx'
                ],
                test_patterns=[
                    'test*mcp*client*',
                    'test*integration*mcp*'
                ],
                documentation_patterns=[
                    'mcp*.md',
                    'client*.md'
                ],
                commit_patterns=[
                    r'mcp.?client',
                    r'implement.*mcp',
                    r'complete.*client'
                ],
                completion_indicators={
                    'all_files_present': 0.3,
                    'classes_implemented': 0.3,
                    'methods_implemented': 0.2,
                    'tests_present': 0.1,
                    'documentation_present': 0.1
                }
            ),
            
            'gmail_integration': FeaturePattern(
                name='Gmail Integration',
                category='integration',
                required_files=[
                    'src/mcp_tools/gmail_tool.py'
                ],
                optional_files=[
                    'src/mcp_tools/__init__.py'
                ],
                required_classes=[
                    'GmailTool'
                ],
                required_methods=[
                    'invoke',
                    'get_emails',
                    'send_email'
                ],
                required_imports=[
                    'google.auth',
                    'google.oauth2',
                    'googleapiclient'
                ],
                test_patterns=[
                    'test*gmail*',
                    'test*email*'
                ],
                documentation_patterns=[
                    'gmail*.md',
                    'email*.md'
                ],
                commit_patterns=[
                    r'gmail',
                    r'email.?integration',
                    r'implement.*gmail'
                ],
                completion_indicators={
                    'all_files_present': 0.4,
                    'classes_implemented': 0.3,
                    'methods_implemented': 0.3
                }
            ),
            
            'nest_integration': FeaturePattern(
                name='Google Nest Integration',
                category='integration',
                required_files=[
                    'src/mcp_tools/nest_tool.py'
                ],
                optional_files=[
                    'src/mcp_tools/__init__.py'
                ],
                required_classes=[
                    'NestTool'
                ],
                required_methods=[
                    'invoke',
                    'get_devices',
                    'control_device'
                ],
                required_imports=[
                    'google.auth',
                    'nest'
                ],
                test_patterns=[
                    'test*nest*',
                    'test*home*'
                ],
                documentation_patterns=[
                    'nest*.md',
                    'google*home*.md'
                ],
                commit_patterns=[
                    r'nest',
                    r'google.?home',
                    r'implement.*nest'
                ],
                completion_indicators={
                    'all_files_present': 0.4,
                    'classes_implemented': 0.3,
                    'methods_implemented': 0.3
                }
            ),
            
            'telegram_bot': FeaturePattern(
                name='Telegram Bot Integration',
                category='integration',
                required_files=[
                    'src/mcp_server/telegram_bot.py'
                ],
                optional_files=[
                    'src/mcp_server/__init__.py'
                ],
                required_classes=[
                    'TelegramBot'
                ],
                required_methods=[
                    'start',
                    'send_message',
                    'handle_update'
                ],
                required_imports=[
                    'telegram',
                    'telegram.ext'
                ],
                test_patterns=[
                    'test*telegram*',
                    'test*bot*'
                ],
                documentation_patterns=[
                    'telegram*.md',
                    'bot*.md'
                ],
                commit_patterns=[
                    r'telegram',
                    r'bot',
                    r'implement.*telegram'
                ],
                completion_indicators={
                    'all_files_present': 0.4,
                    'classes_implemented': 0.3,
                    'methods_implemented': 0.3
                }
            ),
            
            'web_interface': FeaturePattern(
                name='Web Interface',
                category='frontend',
                required_files=[
                    'static/index.html',
                    'static/dashboard.html'
                ],
                optional_files=[
                    'static/mcp_setup.html',
                    'static/css/style.css',
                    'static/js/app.js'
                ],
                required_classes=[],
                required_methods=[],
                required_imports=[],
                test_patterns=[
                    'test*web*',
                    'test*interface*',
                    'playwright*'
                ],
                documentation_patterns=[
                    'web*.md',
                    'interface*.md',
                    'ui*.md'
                ],
                commit_patterns=[
                    r'web.?interface',
                    r'frontend',
                    r'ui',
                    r'dashboard'
                ],
                completion_indicators={
                    'all_files_present': 0.5,
                    'tests_present': 0.2,
                    'documentation_present': 0.3
                }
            ),
            
            'authentication': FeaturePattern(
                name='Authentication System',
                category='backend',
                required_files=[
                    'src/mcp_server/auth.py',
                    'src/mcp_client/auth.py'
                ],
                optional_files=[
                    'src/mcp_client/browser_auth.py',
                    'src/mcp_server/middleware.py'
                ],
                required_classes=[
                    'AuthManager',
                    'AuthMiddleware'
                ],
                required_methods=[
                    'login',
                    'register',
                    'authenticate',
                    'create_session'
                ],
                required_imports=[
                    'bcrypt',
                    'jwt',
                    'passlib'
                ],
                test_patterns=[
                    'test*auth*',
                    'test*login*',
                    'test*registration*'
                ],
                documentation_patterns=[
                    'auth*.md',
                    'login*.md'
                ],
                commit_patterns=[
                    r'auth',
                    r'login',
                    r'registration',
                    r'implement.*auth'
                ],
                completion_indicators={
                    'all_files_present': 0.3,
                    'classes_implemented': 0.3,
                    'methods_implemented': 0.2,
                    'tests_present': 0.2
                }
            ),
            
            'onboarding': FeaturePattern(
                name='User Onboarding System',
                category='backend',
                required_files=[
                    'src/mcp_server/onboarding.py'
                ],
                optional_files=[
                    'src/mcp_server/beta_onboarding.py'
                ],
                required_classes=[
                    'OnboardingManager'
                ],
                required_methods=[
                    'start_onboarding',
                    'process_step',
                    'complete_onboarding'
                ],
                required_imports=[
                    'pydantic',
                    'fastapi'
                ],
                test_patterns=[
                    'test*onboard*',
                    'test*welcome*'
                ],
                documentation_patterns=[
                    'onboard*.md',
                    'welcome*.md'
                ],
                commit_patterns=[
                    r'onboard',
                    r'welcome',
                    r'user.?setup'
                ],
                completion_indicators={
                    'all_files_present': 0.4,
                    'classes_implemented': 0.3,
                    'methods_implemented': 0.3
                }
            ),
            
            'testing_suite': FeaturePattern(
                name='Comprehensive Testing Suite',
                category='quality',
                required_files=[
                    'tests/conftest.py',
                    'pytest.ini'
                ],
                optional_files=[
                    'tests/unit/__init__.py',
                    'tests/integration/__init__.py',
                    'tests/e2e/__init__.py',
                    'tests/performance/__init__.py'
                ],
                required_classes=[],
                required_methods=[],
                required_imports=[
                    'pytest',
                    'asyncio'
                ],
                test_patterns=[
                    'test_*.py'
                ],
                documentation_patterns=[
                    'testing*.md',
                    'test*.md'
                ],
                commit_patterns=[
                    r'test',
                    r'testing.?suite',
                    r'pytest',
                    r'ci.?cd'
                ],
                completion_indicators={
                    'test_directories_present': 0.3,
                    'test_files_present': 0.4,
                    'configuration_present': 0.3
                }
            )
        }
        
        return patterns
    
    async def analyze_issue_completion(
        self,
        issue: Any,  # GitHubIssue model
        repository_owner: str,
        repository_name: str
    ) -> Dict[str, Any]:
        """
        Analyze an issue to determine if its associated feature is completed.
        
        Returns comprehensive analysis with confidence scores and evidence.
        """
        logger.info(
            "Analyzing issue for feature completion",
            issue_number=issue.github_issue_number,
            issue_title=issue.title
        )
        
        analysis_start = time.time()
        
        # Extract potential feature names from issue
        potential_features = self._extract_features_from_issue(issue)
        
        if not potential_features:
            return {
                'features_detected': 0,
                'detections': [],
                'analysis_duration_ms': (time.time() - analysis_start) * 1000
            }
        
        detections = []
        
        for feature_name in potential_features:
            if feature_name in self.patterns:
                detection = await self._analyze_feature_pattern(
                    self.patterns[feature_name],
                    issue,
                    repository_owner,
                    repository_name
                )
                if detection:
                    detections.append(detection)
        
        analysis_duration = (time.time() - analysis_start) * 1000
        
        result = {
            'features_detected': len(detections),
            'detections': [
                {
                    'feature_name': d.feature_name,
                    'confidence_score': d.confidence_score,
                    'completion_status': d.completion_status,
                    'evidence': d.evidence,
                    'false_positive_score': d.false_positive_score,
                    'detection_method': d.detection_method
                } for d in detections
            ],
            'analysis_duration_ms': analysis_duration
        }
        
        logger.info(
            "Issue analysis completed",
            issue_number=issue.github_issue_number,
            features_detected=len(detections),
            analysis_duration_ms=analysis_duration
        )
        
        return result
    
    def _extract_features_from_issue(self, issue: Any) -> List[str]:
        """Extract potential feature names from issue title and description."""
        text = f"{issue.title} {issue.description or ''}".lower()
        
        extracted_features = []
        
        # Pattern matching for feature identification
        feature_mappings = {
            'mcp_client': ['mcp', 'client', 'protocol'],
            'gmail_integration': ['gmail', 'email', 'mail'],
            'nest_integration': ['nest', 'google home', 'smart home'],
            'telegram_bot': ['telegram', 'bot', 'messaging'],
            'web_interface': ['web', 'interface', 'frontend', 'ui', 'dashboard'],
            'authentication': ['auth', 'login', 'registration', 'user'],
            'onboarding': ['onboarding', 'welcome', 'setup'],
            'testing_suite': ['test', 'testing', 'pytest', 'quality']
        }
        
        for feature, keywords in feature_mappings.items():
            if any(keyword in text for keyword in keywords):
                extracted_features.append(feature)
        
        return extracted_features
    
    async def _analyze_feature_pattern(
        self,
        pattern: FeaturePattern,
        issue: Any,
        repository_owner: str,
        repository_name: str
    ) -> Optional[DetectionResult]:
        """Analyze a specific feature pattern for completion."""
        evidence = {
            'code_files': [],
            'test_files': [],
            'documentation_files': [],
            'commits': [],
            'classes_found': [],
            'methods_found': [],
            'imports_found': []
        }
        
        completion_scores = {}
        
        # Check file presence
        files_present = self._check_file_presence(pattern.required_files + pattern.optional_files)
        evidence['code_files'] = [f for f in files_present if files_present[f]]
        required_files_score = sum(
            1 for f in pattern.required_files if files_present.get(f, False)
        ) / max(len(pattern.required_files), 1)
        
        if 'all_files_present' in pattern.completion_indicators:
            completion_scores['all_files_present'] = required_files_score
        
        # Analyze code structure if files exist
        if evidence['code_files']:
            code_analysis = self._analyze_code_structure(
                evidence['code_files'],
                pattern.required_classes,
                pattern.required_methods,
                pattern.required_imports
            )
            
            evidence.update({
                'classes_found': code_analysis['classes_found'],
                'methods_found': code_analysis['methods_found'],
                'imports_found': code_analysis['imports_found']
            })
            
            if 'classes_implemented' in pattern.completion_indicators:
                completion_scores['classes_implemented'] = code_analysis['class_score']
            
            if 'methods_implemented' in pattern.completion_indicators:
                completion_scores['methods_implemented'] = code_analysis['method_score']
        
        # Check test presence
        test_files = self._find_test_files(pattern.test_patterns)
        evidence['test_files'] = test_files
        
        if 'tests_present' in pattern.completion_indicators:
            completion_scores['tests_present'] = 1.0 if test_files else 0.0
        
        if 'test_directories_present' in pattern.completion_indicators:
            test_dirs = ['tests/unit', 'tests/integration', 'tests/e2e', 'tests/performance']
            present_dirs = [d for d in test_dirs if Path(d).exists()]
            completion_scores['test_directories_present'] = len(present_dirs) / len(test_dirs)
        
        if 'test_files_present' in pattern.completion_indicators:
            all_test_files = list(Path('tests').rglob('test_*.py')) if Path('tests').exists() else []
            completion_scores['test_files_present'] = min(len(all_test_files) / 10, 1.0)  # Normalize to max 10
        
        if 'configuration_present' in pattern.completion_indicators:
            config_files = ['pytest.ini', 'pyproject.toml', 'tox.ini']
            present_config = [f for f in config_files if Path(f).exists()]
            completion_scores['configuration_present'] = len(present_config) / len(config_files)
        
        # Check documentation
        doc_files = self._find_documentation_files(pattern.documentation_patterns)
        evidence['documentation_files'] = doc_files
        
        if 'documentation_present' in pattern.completion_indicators:
            completion_scores['documentation_present'] = 1.0 if doc_files else 0.0
        
        # Analyze recent commits
        commits = self._analyze_commits(pattern.commit_patterns, days=30)
        evidence['commits'] = commits
        
        # Calculate overall confidence score
        confidence_score = 0.0
        for indicator, weight in pattern.completion_indicators.items():
            if indicator in completion_scores:
                confidence_score += completion_scores[indicator] * weight
        
        # Determine completion status
        if confidence_score >= 0.9:
            completion_status = 'verified'
        elif confidence_score >= 0.7:
            completion_status = 'completed'
        elif confidence_score >= 0.3:
            completion_status = 'in_progress'
        else:
            completion_status = 'not_started'
        
        # Calculate false positive score
        false_positive_score = self._calculate_false_positive_score(
            pattern, evidence, completion_scores
        )
        
        return DetectionResult(
            feature_name=pattern.name,
            confidence_score=confidence_score,
            completion_status=completion_status,
            evidence=evidence,
            false_positive_score=false_positive_score,
            detection_method='multi_factor_analysis'
        )
    
    def _check_file_presence(self, file_paths: List[str]) -> Dict[str, bool]:
        """Check which files exist in the repository."""
        presence = {}
        for file_path in file_paths:
            full_path = self.repository_root / file_path
            presence[file_path] = full_path.exists()
        return presence
    
    def _analyze_code_structure(
        self,
        file_paths: List[str],
        required_classes: List[str],
        required_methods: List[str],
        required_imports: List[str]
    ) -> Dict[str, Any]:
        """Analyze code structure using AST parsing."""
        found_classes = set()
        found_methods = set()
        found_imports = set()
        
        for file_path in file_paths:
            try:
                full_path = self.repository_root / file_path
                if full_path.suffix == '.py' and full_path.exists():
                    with open(full_path, 'r', encoding='utf-8') as f:
                        try:
                            tree = ast.parse(f.read())
                            
                            for node in ast.walk(tree):
                                if isinstance(node, ast.ClassDef):
                                    found_classes.add(node.name)
                                elif isinstance(node, ast.FunctionDef):
                                    found_methods.add(node.name)
                                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                                    if isinstance(node, ast.Import):
                                        for alias in node.names:
                                            found_imports.add(alias.name)
                                    elif isinstance(node, ast.ImportFrom) and node.module:
                                        found_imports.add(node.module)
                        except SyntaxError:
                            logger.warning(f"Syntax error parsing {file_path}")
            except Exception as e:
                logger.warning(f"Error analyzing {file_path}: {str(e)}")
        
        class_score = len(found_classes & set(required_classes)) / max(len(required_classes), 1)
        method_score = len(found_methods & set(required_methods)) / max(len(required_methods), 1)
        
        return {
            'classes_found': list(found_classes),
            'methods_found': list(found_methods),
            'imports_found': list(found_imports),
            'class_score': class_score,
            'method_score': method_score
        }
    
    def _find_test_files(self, patterns: List[str]) -> List[str]:
        """Find test files matching patterns."""
        test_files = []
        tests_dir = self.repository_root / 'tests'
        
        if tests_dir.exists():
            for pattern in patterns:
                # Use glob pattern matching
                matches = list(tests_dir.rglob(pattern))
                test_files.extend([str(m.relative_to(self.repository_root)) for m in matches])
        
        return list(set(test_files))  # Remove duplicates
    
    def _find_documentation_files(self, patterns: List[str]) -> List[str]:
        """Find documentation files matching patterns."""
        doc_files = []
        
        # Check common documentation directories
        doc_dirs = [self.repository_root, self.repository_root / 'docs', self.repository_root / 'doc']
        
        for doc_dir in doc_dirs:
            if doc_dir.exists():
                for pattern in patterns:
                    matches = list(doc_dir.glob(pattern))
                    doc_files.extend([str(m.relative_to(self.repository_root)) for m in matches])
        
        return list(set(doc_files))  # Remove duplicates
    
    def _analyze_commits(self, patterns: List[str], days: int = 30) -> List[Dict[str, Any]]:
        """Analyze recent commits for feature-related messages."""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get commit messages
            result = subprocess.run([
                'git', 'log',
                '--since', since_date,
                '--pretty=format:%H|%s|%ad|%an',
                '--date=iso',
                '--no-merges'
            ], capture_output=True, text=True, check=True, cwd=self.repository_root)
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('|')
                    if len(parts) >= 4:
                        commit_hash, message, date, author = parts[:4]
                        
                        # Check if commit message matches any pattern
                        message_lower = message.lower()
                        matches = [p for p in patterns if re.search(p, message_lower)]
                        
                        if matches:
                            commits.append({
                                'hash': commit_hash,
                                'message': message,
                                'date': date,
                                'author': author,
                                'matched_patterns': matches
                            })
            
            return commits[:10]  # Return most recent 10 matching commits
            
        except subprocess.CalledProcessError:
            logger.warning("Failed to analyze git commits")
            return []
    
    def _calculate_false_positive_score(
        self,
        pattern: FeaturePattern,
        evidence: Dict[str, Any],
        completion_scores: Dict[str, float]
    ) -> float:
        """Calculate likelihood that this is a false positive."""
        false_positive_indicators = 0.0
        total_indicators = 0.0
        
        # Check for incomplete implementations
        if evidence['code_files']:
            total_indicators += 1
            # If we have files but no classes/methods, might be incomplete
            if not evidence['classes_found'] and pattern.required_classes:
                false_positive_indicators += 0.5
            if not evidence['methods_found'] and pattern.required_methods:
                false_positive_indicators += 0.5
        
        # Check for missing tests
        if pattern.test_patterns:
            total_indicators += 1
            if not evidence['test_files']:
                false_positive_indicators += 0.3
        
        # Check for stale files (no recent commits)
        if evidence['commits']:
            total_indicators += 1
            recent_commits = [c for c in evidence['commits'] 
                            if (datetime.now() - datetime.fromisoformat(c['date'].replace('Z', '+00:00'))).days < 7]
            if not recent_commits:
                false_positive_indicators += 0.2
        
        return false_positive_indicators / max(total_indicators, 1.0)
    
    def get_feature_patterns(self) -> Dict[str, FeaturePattern]:
        """Get all configured feature patterns."""
        return self.patterns.copy()
    
    def add_custom_pattern(self, name: str, pattern: FeaturePattern) -> None:
        """Add a custom feature detection pattern."""
        self.patterns[name] = pattern
        logger.info(f"Added custom feature pattern: {name}")
    
    def get_analysis_cache_stats(self) -> Dict[str, Any]:
        """Get analysis cache statistics."""
        return {
            'cache_size': len(self.analysis_cache),
            'cache_hit_rate': getattr(self, '_cache_hits', 0) / max(getattr(self, '_cache_attempts', 1), 1)
        }