# Accessibility Testing Infrastructure for MCP ADHD Server

## Overview

This document outlines the comprehensive accessibility testing infrastructure for the MCP ADHD Server, designed to ensure WCAG 2.1 AA compliance and optimal support for neurodivergent users with diverse accessibility needs.

## Table of Contents

1. [Testing Philosophy](#testing-philosophy)
2. [Test Categories](#test-categories)
3. [Running Tests](#running-tests)
4. [CI/CD Integration](#cicd-integration)
5. [Test Results and Reports](#test-results-and-reports)
6. [Adding New Tests](#adding-new-tests)
7. [Troubleshooting](#troubleshooting)
8. [Resources](#resources)

## Testing Philosophy

Our accessibility testing follows these core principles:

### 1. **ADHD-First Design**
- Tests prioritize ADHD-specific accessibility needs
- Crisis features receive highest testing priority (life-critical)
- Cognitive load management is continuously monitored
- Performance thresholds are stricter for attention management

### 2. **Multi-Disability Intersections**
- Tests consider users with ADHD plus additional disabilities
- Screen reader + ADHD combinations
- Motor impairment + ADHD considerations
- Visual/hearing impairment + cognitive support needs

### 3. **Automated + Manual Testing**
- Automated tests catch regressions quickly
- Manual testing procedures for nuanced accessibility
- User testing protocols for real-world validation
- Continuous monitoring and improvement

### 4. **Safety-First Approach**
- Critical accessibility failures fail the build
- Crisis features must be fully accessible
- Emergency paths receive extra testing attention

## Test Categories

### 1. WCAG 2.1 AA Compliance Tests (`test_wcag_compliance.py`)

**Purpose**: Ensure standard accessibility compliance across all interfaces.

**Key Areas**:
- Color contrast ratios (minimum 4.5:1 for normal text)
- Keyboard navigation functionality
- Screen reader compatibility (ARIA labels, landmarks, heading structure)
- Form accessibility and error handling
- Image alternative text and media accessibility

**Critical Tests**:
```python
# Example: Homepage WCAG compliance
def test_homepage_wcag_compliance()
# Example: Chat interface accessibility
def test_chat_interface_wcag_compliance()
# Example: Authentication modal accessibility
def test_authentication_wcag_compliance()
```

### 2. ADHD-Specific Accessibility Tests (`test_adhd_accessibility.py`)

**Purpose**: Test features specifically designed for ADHD and neurodivergent users.

**Key Areas**:
- **Cognitive Load Management**: Limit information density, avoid choice overload
- **Focus Management**: Clear focus indicators, logical tab order, focus traps
- **Motion Sensitivity**: Respect `prefers-reduced-motion`, minimal animations
- **Crisis Features**: Emergency buttons, overwhelm support, safety overrides
- **Attention Span**: Fast load times (<3s), chunked content, progress indicators
- **Sensory Considerations**: No auto-playing media, color alternatives

**Critical Tests**:
```python
# Example: Cognitive load validation
def test_cognitive_load_management()
# Example: Crisis button accessibility
def test_crisis_features_accessibility()
# Example: Quick actions for executive function
def test_quick_actions_adhd_accessibility()
```

### 3. Multi-Disability Intersection Tests (`test_multi_disability.py`)

**Purpose**: Ensure accessibility for users with ADHD plus additional disabilities.

**Key Areas**:
- **Screen Reader + ADHD**: Concise labels, manageable information density
- **Motor + ADHD**: Larger touch targets, adequate spacing, emergency access
- **Visual + ADHD**: Enhanced contrast, zoom compatibility, non-color coding
- **Hearing + ADHD**: Visual alternatives, notification accessibility
- **Cognitive + ADHD**: Simple language, clear navigation, error prevention

**Critical Tests**:
```python
# Example: Screen reader + ADHD compatibility
def test_screen_reader_plus_adhd()
# Example: Motor impairment + ADHD usability
def test_motor_impairment_plus_adhd()
```

### 4. Lighthouse Accessibility Audits (`test_lighthouse_audit.py`)

**Purpose**: Comprehensive automated auditing using Google Lighthouse.

**Key Areas**:
- Automated WCAG compliance scanning
- Performance optimization for ADHD attention spans
- Mobile accessibility validation
- Best practices enforcement

## Running Tests

### Prerequisites

```bash
# Install dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium

# Install Lighthouse (optional, for Lighthouse tests)
npm install -g lighthouse
```

### Local Testing

```bash
# Start the development server
python -m uvicorn src.mcp_server.main:app --reload --port 8000

# Run all accessibility tests
pytest tests/accessibility/ -v

# Run specific test categories
pytest tests/accessibility/test_wcag_compliance.py -v
pytest tests/accessibility/test_adhd_accessibility.py -v
pytest tests/accessibility/test_multi_disability.py -v

# Run with specific markers
pytest tests/accessibility/ -m "adhd_critical" -v
pytest tests/accessibility/ -m "crisis" -v
pytest tests/accessibility/ -m "wcag" -v
```

### Test Configuration

Tests can be configured via environment variables:

```bash
# Server URL
export BASE_URL=http://localhost:8000

# Browser settings
export HEADLESS=true  # For CI/CD
export HEADLESS=false # For debugging

# Test parallelization
export PYTEST_WORKERS=2
```

### Running Specific Viewport Tests

```bash
# Test different screen sizes
pytest tests/accessibility/ -k "responsive" -v

# Mobile-specific tests
pytest tests/accessibility/ -k "mobile" -v
```

## CI/CD Integration

### GitHub Actions Workflow

The `.github/workflows/accessibility-testing.yml` workflow:

1. **Sets up test environment** with PostgreSQL and Redis
2. **Installs dependencies** including Playwright and Lighthouse
3. **Starts test server** with proper configuration
4. **Runs accessibility test suites** in parallel
5. **Generates comprehensive reports**
6. **Posts results to Pull Requests**
7. **Fails build on critical issues**

### Trigger Conditions

- **Push to main/develop branches**
- **Pull requests** affecting UI/frontend code
- **Manual workflow dispatch** for ad-hoc testing

### Critical Failure Conditions

The build fails on:
- WCAG 2.1 AA compliance violations
- Crisis features not fully accessible
- Cognitive load exceeding ADHD thresholds (8.0/10)
- Page load times exceeding ADHD attention spans (5s)

## Test Results and Reports

### Report Generation

```bash
# Generate accessibility report from test results
python scripts/generate_accessibility_report.py \
  --results-dir test-results/accessibility \
  --output test-results/accessibility-summary.json
```

### Report Structure

**Summary Report** (`accessibility-summary.json`):
```json
{
  "overall_accessibility_score": 95.2,
  "wcag_compliance": true,
  "adhd_accessibility": true,
  "crisis_features_accessible": true,
  "cognitive_load_score": 4.2,
  "critical_issues": [],
  "pages_tested": 5
}
```

**Detailed Report** (`accessibility-detailed-report.json`):
- Complete WCAG analysis with violation details
- ADHD-specific accessibility breakdown
- Multi-disability intersection analysis
- Performance metrics for attention management
- Raw test results and screenshots

### Interpreting Results

**Accessibility Scores**:
- **90-100**: Excellent accessibility, meets all requirements
- **80-89**: Good, minor improvements needed
- **70-79**: Acceptable, but requires attention
- **Below 70**: Failing, significant issues present

**Critical Issues**:
- Any issue marked as "critical" must be resolved immediately
- Crisis features accessibility issues are always critical
- WCAG violations affecting screen readers are critical

## Adding New Tests

### 1. WCAG Compliance Tests

```python
# Add to test_wcag_compliance.py
@pytest.mark.accessibility
@pytest.mark.wcag
def test_new_feature_wcag_compliance(
    page: Page, 
    axe_builder: Axe,
    accessibility_results_dir: Path
):
    """Test new feature WCAG compliance."""
    page.goto("/new-feature")
    
    # Run axe scan
    results = axe_builder.analyze(page, {
        "tags": ["wcag2a", "wcag2aa", "wcag21aa"]
    })
    
    # Save results
    results_file = accessibility_results_dir / "new_feature_wcag_results.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Assert compliance
    violations = results.get("violations", [])
    assert len(violations) == 0, f"WCAG violations: {[v['id'] for v in violations]}"
```

### 2. ADHD-Specific Tests

```python
# Add to test_adhd_accessibility.py
@pytest.mark.accessibility
@pytest.mark.adhd_critical
def test_new_feature_adhd_accessibility(
    page: Page,
    adhd_accessibility_tester,
    accessibility_results_dir: Path
):
    """Test new feature ADHD accessibility."""
    page.goto("/new-feature")
    
    tester = adhd_accessibility_tester(page)
    
    # Check cognitive load
    cognitive_results = tester.check_cognitive_load()
    assert cognitive_results["cognitive_load_score"] <= 6.0, \
        "Cognitive load too high for ADHD users"
    
    # Additional ADHD-specific checks...
```

### 3. Multi-Disability Tests

```python
# Add to test_multi_disability.py
@pytest.mark.accessibility
@pytest.mark.multi_disability
def test_new_feature_screen_reader_adhd(
    page: Page,
    screen_reader_tester,
    adhd_accessibility_tester
):
    """Test new feature for screen reader + ADHD users."""
    # Combined testing logic...
```

## Testing Best Practices

### 1. Test Naming Conventions

- **WCAG tests**: `test_{feature}_wcag_compliance`
- **ADHD tests**: `test_{feature}_adhd_accessibility`
- **Multi-disability**: `test_{feature}_{disability1}_{disability2}`
- **Crisis features**: Always include `@pytest.mark.crisis`

### 2. Assertion Guidelines

- **Use descriptive assertion messages** that explain the accessibility requirement
- **Reference specific ADHD needs** in failure messages
- **Include context** about why the requirement is important

```python
# Good assertion
assert cognitive_load <= 6.0, \
    f"Cognitive load ({cognitive_load}) exceeds ADHD threshold - may overwhelm users"

# Poor assertion
assert cognitive_load <= 6.0
```

### 3. Test Data Management

- **Save test results** to JSON files for analysis
- **Include metadata** (timestamps, test configurations)
- **Clean up temporary files** after tests

### 4. Error Handling

```python
# Handle missing dependencies gracefully
try:
    from axe_playwright_python import Axe
except ImportError:
    pytest.skip("axe-playwright-python not available")

# Handle server connectivity issues
try:
    page.goto("/")
    page.wait_for_load_state("networkidle")
except Exception as e:
    pytest.skip(f"Server not available: {e}")
```

## Manual Testing Procedures

### 1. Screen Reader Testing

**Tools**: NVDA (Windows), JAWS (Windows), VoiceOver (Mac), Orca (Linux)

**Procedure**:
1. Navigate using only screen reader
2. Test all interactive elements
3. Verify ARIA labels and descriptions
4. Check heading structure and landmarks
5. Test form completion and error handling

### 2. Keyboard Navigation Testing

**Procedure**:
1. Disconnect mouse/trackpad
2. Navigate using only Tab, Shift+Tab, Enter, Space, Arrow keys
3. Verify all functionality is accessible
4. Check focus indicators are visible
5. Test modal focus traps

### 3. High Contrast Testing

**Procedure**:
1. Enable high contrast mode (Windows/Mac)
2. Check all content is visible and readable
3. Verify color contrast ratios meet WCAG AA
4. Test with different contrast themes

### 4. Zoom Testing

**Procedure**:
1. Test at 150%, 200%, 250%, 400% zoom
2. Verify no horizontal scrolling required
3. Check all functionality remains available
4. Ensure content reflows properly

## Troubleshooting

### Common Issues

#### 1. Playwright Browser Issues

```bash
# Reinstall browsers
playwright install --force chromium

# Check browser installation
playwright install-deps chromium
```

#### 2. Server Connection Issues

```bash
# Check server is running
curl -f http://localhost:8000/health

# Start server with specific config
DATABASE_URL=sqlite:///test.db REDIS_URL=redis://localhost:6379 \
python -m uvicorn src.mcp_server.main:app --port 8000
```

#### 3. Test Timeout Issues

```python
# Increase timeouts for slow environments
page.set_default_timeout(30000)  # 30 seconds
page.wait_for_load_state("networkidle", timeout=20000)
```

#### 4. Lighthouse Installation Issues

```bash
# Install Lighthouse globally
npm install -g lighthouse

# Or skip Lighthouse tests
pytest tests/accessibility/ -m "not lighthouse"
```

### Debug Mode

```bash
# Run tests in visible browser for debugging
HEADLESS=false pytest tests/accessibility/test_adhd_accessibility.py::test_cognitive_load_management -s -v

# Save screenshots on failure
pytest tests/accessibility/ --screenshot=on-failure
```

## Resources

### ADHD Accessibility Guidelines

- [ADHD-Friendly Web Design Principles](https://webaim.org/articles/cognitive/adhd/)
- [Cognitive Accessibility Guidelines](https://www.w3.org/WAI/cognitive/)
- [Neurodiversity-Affirming Design](https://neurodiversityhub.org/design-guidelines)

### Testing Tools Documentation

- [Axe Accessibility Testing](https://github.com/dequelabs/axe-core)
- [Playwright Testing Framework](https://playwright.dev/)
- [Google Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

### Screen Reader Resources

- [NVDA Screen Reader](https://www.nvaccess.org/)
- [Screen Reader Testing Guide](https://webaim.org/articles/screenreader_testing/)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)

### Color and Contrast Tools

- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Colour Contrast Analyser](https://www.tpgi.com/color-contrast-checker/)
- [Stark Figma Plugin](https://www.getstark.co/)

## Contributing

When contributing to accessibility testing:

1. **Follow the testing philosophy** and prioritize ADHD needs
2. **Add appropriate test markers** (`@pytest.mark.accessibility`, `@pytest.mark.adhd_critical`)
3. **Include descriptive docstrings** explaining the accessibility requirement
4. **Save test results** for analysis and reporting
5. **Update documentation** when adding new test categories
6. **Consider multi-disability intersections** in new tests

## Support

For questions about accessibility testing:

- **Issues**: Create GitHub issues with the `accessibility` label
- **Discussions**: Use GitHub Discussions for testing questions
- **Documentation**: Refer to this guide and linked resources
- **Code Review**: All accessibility tests require review by accessibility team members

---

*This accessibility testing infrastructure ensures the MCP ADHD Server provides excellent support for all neurodivergent users, with special attention to ADHD needs and multi-disability considerations.*