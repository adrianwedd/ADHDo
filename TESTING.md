# MCP ADHD Server - Testing Suite

This document describes the comprehensive testing strategy and implementation for the MCP ADHD Server project.

## Testing Philosophy

Our testing approach is specifically designed for ADHD users and optimized systems:

- **Response Time Focus**: All tests validate that responses meet ADHD-optimized targets (<3 seconds)
- **Cognitive Load Testing**: Tests verify that cognitive load calculations and optimizations work correctly
- **Reliability First**: Tests ensure consistent, predictable behavior for users with executive function challenges
- **Performance Regression Detection**: Continuous monitoring to prevent performance degradation

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── utils.py                    # Test utilities and helper functions
├── unit/                       # Unit tests (fast, isolated)
│   ├── database/              # Database layer tests
│   ├── health/                # Health monitoring tests
│   ├── metrics/               # Metrics collection tests
│   ├── alerting/              # Alert management tests
│   └── auth/                  # Authentication tests
├── integration/               # Integration tests (API endpoints)
│   ├── api/                   # API endpoint tests
│   └── workflows/             # Cross-component workflows
├── e2e/                       # End-to-end tests (complete workflows)
├── performance/               # Performance and ADHD optimization tests
└── adhd_features/            # ADHD-specific feature tests
```

## Test Categories

### 1. Unit Tests
- **Purpose**: Test individual components in isolation
- **Speed**: Very fast (<1s per test)
- **Coverage**: 80%+ code coverage required
- **Focus Areas**:
  - Database models, repositories, services
  - Health monitoring logic
  - Metrics calculations
  - Alert management
  - Authentication flows

### 2. Integration Tests
- **Purpose**: Test API endpoints and component interactions
- **Speed**: Fast (<3s per test)
- **Focus Areas**:
  - Health endpoint responses
  - Metrics endpoint functionality
  - Authentication middleware
  - Database integration

### 3. End-to-End Tests
- **Purpose**: Test complete user workflows
- **Speed**: Moderate (5-10s per test)
- **Focus Areas**:
  - User onboarding flow
  - Task management workflow
  - ADHD support interactions
  - System monitoring workflows

### 4. Performance Tests
- **Purpose**: Validate ADHD-specific performance requirements
- **Speed**: Variable (depends on load)
- **Key Metrics**:
  - Response times <3000ms (ADHD target)
  - Cognitive load processing <1000ms
  - Task suggestions <800ms
  - Pattern matching <1500ms
  - Context building <600ms

### 5. ADHD-Specific Tests
- **Purpose**: Test ADHD-optimized features
- **Focus Areas**:
  - Cognitive load calculation accuracy
  - Pattern recognition for ADHD states
  - Dopamine reward system
  - Focus session management
  - Context adaptation

## Key Features

### ADHD Optimization Testing
- **Cognitive Load Headers**: Verify X-Cognitive-Load headers are accurate
- **Response Time Monitoring**: Ensure all responses meet ADHD targets
- **Pattern Recognition**: Test detection of ADHD-specific user states
- **Adaptive Responses**: Verify system adapts to user cognitive load

### Performance Assertions
- **Response Time Assertions**: Built-in helpers for timing validation
- **Cognitive Load Validation**: Ensure values are in valid ranges (0.0-1.0)
- **ADHD Scenario Testing**: Predefined scenarios for common ADHD situations

### Test Data Factories
- **Realistic Test Data**: Factories generate ADHD-relevant test scenarios
- **User Personas**: Different ADHD user types for comprehensive testing
- **Workflow Simulation**: End-to-end user journey simulation

## Running Tests

### Local Development

```bash
# Run all tests
./scripts/run_tests.sh

# Run specific test categories
pytest tests/unit                    # Unit tests only
pytest tests/integration             # Integration tests only
pytest tests/e2e -m "not slow"      # E2E tests (excluding slow tests)
pytest tests/performance             # Performance tests only

# Run with coverage
pytest tests/unit --cov=src/mcp_server --cov-report=html

# Run ADHD-specific tests
pytest -m adhd

# Run performance tests
pytest -m performance
```

### Test Configuration

```bash
# Environment variables for testing
export DATABASE_URL="sqlite:///tmp/test_mcp_adhd.db"
export REDIS_URL="redis://localhost:6379/1"
export OPENAI_API_KEY="test-api-key"
```

### Continuous Integration

The CI/CD pipeline runs:
1. **Matrix Testing**: Python 3.9, 3.10, 3.11, 3.12
2. **Test Categories**: Unit, Integration, E2E in parallel
3. **Code Quality**: Black, Ruff, MyPy, Bandit
4. **Performance Validation**: ADHD performance requirements
5. **Coverage Reporting**: Minimum 80% coverage

## Test Utilities

### Assertion Helpers
- `PerformanceAssertions`: Response time and ADHD optimization validation
- `HealthCheckAssertions`: Health endpoint response validation
- `MetricsAssertions`: Prometheus metrics validation
- `DatabaseAssertions`: Database state validation
- `ADHDTestHelpers`: ADHD-specific test scenarios

### Mock Objects
- **Redis Mock**: In-memory Redis simulation
- **OpenAI Mock**: LLM response simulation
- **Telegram Mock**: Bot message simulation
- **Database Mock**: SQLite in-memory testing

### Test Fixtures
- **User Fixtures**: Test users with different ADHD profiles
- **Task Fixtures**: Various task types and priorities
- **Session Fixtures**: Authentication sessions and API keys
- **Performance Fixtures**: Timing thresholds and benchmarks

## ADHD-Specific Testing

### Cognitive Load Testing
```python
@pytest.mark.adhd
async def test_cognitive_load_calculation():
    # Test high cognitive load scenario
    response = await client.post("/api/chat", json={
        "message": "I have 10 tasks and don't know where to start"
    })
    
    cognitive_load = float(response.headers["X-Cognitive-Load"])
    assert cognitive_load >= 0.7  # High load expected
```

### Performance Testing
```python
@pytest.mark.performance
async def test_adhd_response_time():
    start_time = time.time()
    response = await client.get("/api/tasks/suggest")
    duration_ms = (time.time() - start_time) * 1000
    
    # ADHD target: <3 seconds
    assert duration_ms < 3000
```

### Pattern Recognition Testing
```python
@pytest.mark.adhd
def test_pattern_matching():
    scenarios = ADHDTestHelpers.get_high_cognitive_load_inputs()
    
    for scenario in scenarios:
        result = pattern_matcher.analyze(scenario)
        assert result.cognitive_load >= 0.5
```

## Performance Benchmarks

### ADHD Requirements
- **Maximum Response Time**: 3000ms (critical for ADHD users)
- **Cognitive Load Processing**: <1000ms
- **Task Suggestions**: <800ms  
- **Pattern Matching**: <1500ms
- **Context Building**: <600ms
- **Database Queries**: <100ms
- **Cache Hit Rate**: >70%

### Performance Monitoring
- Automated performance regression detection
- ADHD-specific performance alerts
- Response time trend analysis
- Cognitive load processing optimization

## CI/CD Integration

### GitHub Actions Pipeline
```yaml
# Key pipeline features:
- Matrix testing across Python versions
- Parallel test execution by category
- Performance regression detection
- ADHD optimization validation
- Coverage reporting with Codecov
- Security scanning with Bandit
```

### Pre-commit Hooks
```bash
# Automated quality checks:
- Code formatting (Black)
- Linting (Ruff)
- Type checking (MyPy)  
- Security scanning (Bandit)
- ADHD performance validation
```

## Test Development Guidelines

### Writing ADHD-Optimized Tests
1. **Always test response times** against ADHD targets
2. **Validate cognitive load calculations** for accuracy
3. **Test with realistic ADHD scenarios** from test helpers
4. **Ensure consistent behavior** across multiple runs
5. **Mock external dependencies** for reliable testing

### Performance Test Guidelines
1. **Set realistic thresholds** based on ADHD requirements
2. **Test under load** to validate scalability
3. **Monitor for regressions** in CI/CD pipeline
4. **Document performance assumptions** and constraints

### Best Practices
- Use descriptive test names that explain ADHD context
- Group related ADHD features with pytest markers
- Provide clear failure messages with performance context
- Test both success and failure scenarios
- Validate accessibility and usability features

## Troubleshooting

### Common Issues
- **Slow Tests**: Check database/Redis connections, use mocks
- **Flaky Tests**: Ensure proper cleanup, avoid timing dependencies
- **Coverage Issues**: Add tests for missing ADHD optimizations
- **Performance Failures**: Review ADHD requirements, optimize code

### Debug Tools
- `pytest -v` for verbose output
- `pytest --pdb` for debugging failures  
- `pytest --lf` to run only failed tests
- `pytest --durations=10` for performance analysis

## Monitoring and Alerts

### Test Metrics
- Test execution time trends
- Coverage percentage over time
- Performance regression alerts
- ADHD optimization status

### Alerts
- Performance degradation below ADHD targets
- Coverage drops below 80%
- Security vulnerabilities detected
- Test failure rate increases

## Contributing

When adding new features:
1. **Write tests first** (TDD approach)
2. **Include ADHD optimizations** in test scenarios
3. **Validate performance impact** with benchmarks
4. **Update test documentation** with new patterns
5. **Ensure CI/CD passes** all quality gates

For ADHD-specific features:
1. **Test cognitive load impact** of new features
2. **Validate response time targets** are maintained
3. **Include accessibility testing** for neurodiversity
4. **Document ADHD-specific behaviors** thoroughly

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [ADHD UX Guidelines](./docs/ADHD_UX_GUIDELINES.md)
- [Performance Targets](./docs/PERFORMANCE_TARGETS.md)
- [CI/CD Pipeline](../.github/workflows/ci.yml)