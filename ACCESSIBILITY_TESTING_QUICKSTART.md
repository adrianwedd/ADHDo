# Accessibility Testing Quick Start Guide

## 🚀 Quick Start (5 minutes)

### 1. Prerequisites
```bash
# Install dependencies
pip install -e ".[dev]"

# Install Playwright browsers
playwright install chromium

# Optional: Install Lighthouse for comprehensive audits
npm install -g lighthouse
```

### 2. Start the Server
```bash
# Start development server
python -m uvicorn src.mcp_server.main:app --reload --port 8000

# Verify server is running
curl http://localhost:8000/health
```

### 3. Run Accessibility Tests
```bash
# Run all accessibility tests (comprehensive)
./scripts/run_accessibility_tests.sh

# Or run specific test categories
pytest tests/accessibility/test_wcag_compliance.py -v           # WCAG compliance
pytest tests/accessibility/test_adhd_accessibility.py -v       # ADHD-specific
pytest tests/accessibility/test_multi_disability.py -v         # Multi-disability
```

### 4. View Results
```bash
# Results are saved to test-results/
ls test-results/
# - accessibility-summary.json (CI/CD summary)
# - accessibility-detailed-report.json (full analysis)
# - HTML reports for each test suite
```

## 🎯 Test Categories

### Critical Tests (Must Pass)
```bash
# Crisis features (life-critical)
pytest tests/accessibility/ -m "crisis" -v

# ADHD-critical features
pytest tests/accessibility/ -m "adhd_critical" -v

# WCAG compliance
pytest tests/accessibility/ -m "wcag" -v
```

### Specific Disability Testing
```bash
# Screen reader + ADHD
pytest tests/accessibility/test_multi_disability.py::TestMultiDisabilityAccessibility::test_screen_reader_plus_adhd -v

# Motor impairment + ADHD
pytest tests/accessibility/test_multi_disability.py::TestMultiDisabilityAccessibility::test_motor_impairment_plus_adhd -v

# Visual impairment + ADHD
pytest tests/accessibility/test_multi_disability.py::TestMultiDisabilityAccessibility::test_visual_impairment_plus_adhd -v
```

### Performance for ADHD
```bash
# Attention span and load time tests
pytest tests/accessibility/ -k "attention_span or performance" -v
```

## 🔧 Debug Mode

```bash
# Run with visible browser for debugging
HEADLESS=false pytest tests/accessibility/test_adhd_accessibility.py::TestADHDAccessibility::test_cognitive_load_management -s -v

# Save screenshots on failure
pytest tests/accessibility/ --screenshot=on-failure -v
```

## 📊 Understanding Results

### Exit Codes
- **0**: All tests passed ✅
- **1**: Critical failures (blocks deployment) ❌ 
- **2**: Non-critical failures (fix when possible) ⚠️

### Critical Failure Triggers
- Crisis features not accessible
- WCAG 2.1 AA violations
- Cognitive load exceeding ADHD thresholds
- Page load times > 5 seconds

### Test Markers
- `@pytest.mark.crisis`: Life-critical crisis support features
- `@pytest.mark.adhd_critical`: Essential for ADHD users
- `@pytest.mark.wcag`: Standard accessibility compliance
- `@pytest.mark.multi_disability`: Multiple disability support

## ⚡ Quick Commands

```bash
# Full test suite (recommended for CI/CD)
./scripts/run_accessibility_tests.sh

# Quick WCAG check
pytest tests/accessibility/test_wcag_compliance.py::TestWCAGCompliance::test_homepage_wcag_compliance -v

# Crisis features validation
pytest tests/accessibility/test_adhd_accessibility.py::TestADHDAccessibility::test_crisis_features_accessibility -v

# Cognitive load check
pytest tests/accessibility/test_adhd_accessibility.py::TestADHDAccessibility::test_cognitive_load_management -v

# Performance check
pytest tests/accessibility/test_adhd_accessibility.py::TestADHDAccessibility::test_attention_span_considerations -v
```

## 🚨 Emergency Procedures

### If Crisis Features Fail Tests
```bash
# Immediately run crisis-specific tests
pytest tests/accessibility/ -m "crisis" -v --tb=short

# Check specific crisis elements
grep -r "crisis" tests/accessibility/ --include="*.py"
```

### If WCAG Compliance Fails
```bash
# Run detailed WCAG analysis
pytest tests/accessibility/test_wcag_compliance.py -v --tb=long

# Check specific violation details in test-results/accessibility/
cat test-results/accessibility/*wcag_results.json | jq '.violations'
```

### If Performance Issues Found
```bash
# Run performance-specific tests
pytest tests/accessibility/ -k "performance or attention_span" -v

# Check load times
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/
```

## 📝 Development Workflow

### Before Committing
```bash
# Run quick accessibility check
pytest tests/accessibility/test_wcag_compliance.py::TestWCAGCompliance::test_homepage_wcag_compliance -v

# Check ADHD cognitive load impact
pytest tests/accessibility/test_adhd_accessibility.py::TestADHDAccessibility::test_cognitive_load_management -v
```

### Before Deploying
```bash
# Full accessibility test suite
./scripts/run_accessibility_tests.sh

# Verify no critical issues
echo $?  # Should be 0
```

### Adding New Features
1. Add accessibility tests alongside feature tests
2. Use appropriate markers (`@pytest.mark.adhd_critical` for ADHD features)
3. Test with screen reader if interactive
4. Verify keyboard navigation
5. Check cognitive load impact

## 🏥 Health Checks

```bash
# Verify test infrastructure is working
pytest tests/accessibility/ --collect-only

# Check server accessibility
curl -f http://localhost:8000/health

# Verify Playwright setup
playwright --version
```

## 🔗 Quick Links

- **Full Documentation**: [docs/ACCESSIBILITY_TESTING.md](docs/ACCESSIBILITY_TESTING.md)
- **Checklist**: [docs/ACCESSIBILITY_CHECKLIST.md](docs/ACCESSIBILITY_CHECKLIST.md)
- **CI/CD Workflow**: [.github/workflows/accessibility-testing.yml](.github/workflows/accessibility-testing.yml)
- **Report Generator**: [scripts/generate_accessibility_report.py](scripts/generate_accessibility_report.py)

---

**Need Help?** 
- Check test results in `test-results/` directory
- Review accessibility documentation in `docs/`
- Run tests with `-v` flag for verbose output
- Use `--tb=short` for concise error messages