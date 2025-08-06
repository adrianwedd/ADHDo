"""
Playwright configuration for MCP ADHD Server Phase 0 beta testing.
Optimized for ADHD-specific testing requirements.
"""

from playwright.sync_api import expect
import os

# Test configuration
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8000')
HEADLESS = os.getenv('HEADLESS', 'false').lower() == 'true'

# ADHD-specific test timeouts (longer due to processing needs)
DEFAULT_TIMEOUT = 10000  # 10 seconds for ADHD-friendly patience
NAVIGATION_TIMEOUT = 15000  # 15 seconds for page loads
EXPECT_TIMEOUT = 5000  # 5 seconds for element expectations

# Browser configuration for ADHD testing
BROWSERS = [
    {
        'name': 'chromium',
        'use': {
            'baseURL': BASE_URL,
            'headless': HEADLESS,
            'viewport': {'width': 1920, 'height': 1080},
            'ignoreHTTPSErrors': True,
            'screenshot': 'only-on-failure',
            'video': 'retain-on-failure',
            'trace': 'retain-on-failure',
            # ADHD-friendly settings
            'slow_mo': 100,  # Slow down for human-like interaction
            'args': [
                '--disable-web-security',
                '--disable-features=TranslateUI',
                '--no-first-run',
                '--disable-default-apps',
            ]
        }
    }
]

# Test directories
TEST_DIR = 'tests/playwright'
OUTPUT_DIR = 'test-results'

# Reporting configuration
HTML_REPORT_DIR = f'{OUTPUT_DIR}/html-report'
JUNIT_REPORT_FILE = f'{OUTPUT_DIR}/junit-report.xml'

# ADHD-specific test markers
PYTEST_MARKERS = [
    'adhd_critical: Tests critical for ADHD user success',
    'performance: Tests for ADHD performance requirements (<3s)',
    'accessibility: Tests for cognitive accessibility',
    'ux: Tests for ADHD-friendly user experience',
    'crisis: Tests for overwhelm and crisis detection'
]