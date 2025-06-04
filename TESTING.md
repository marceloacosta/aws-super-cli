# AWS Super CLI Testing Guide

This document describes the testing infrastructure for AWS Super CLI, including how to run tests, what they cover, and how to add new tests.

## 🎯 Testing Philosophy

Our testing approach focuses on:

1. **Regression Prevention** - Catch issues like the Rich markup bug we fixed
2. **CLI Functionality** - Ensure all commands work as expected
3. **Output Quality** - Verify clean, professional output
4. **Integration Safety** - Test AWS integrations without requiring credentials
5. **Release Confidence** - Comprehensive pre-release validation

## 📁 Test Structure

```
tests/
├── __init__.py                 # Test package marker
├── test_cli.py                 # Main CLI functionality tests
├── test_regression.py          # Regression tests for known issues
run_tests.py                    # Test runner with multiple options
test_before_release.py          # Comprehensive pre-release test suite
pytest.ini                     # Pytest configuration
requirements-dev.txt            # Development dependencies
```

## 🚀 Quick Start

### Install Test Dependencies

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Or install specific test packages
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

### Run Tests

```bash
# Run all tests
python run_tests.py

# Run only regression tests
python run_tests.py --regression

# Run with coverage report
python run_tests.py --coverage

# Run quick smoke tests
python run_tests.py --smoke

# Pre-release comprehensive testing
python test_before_release.py
```

## 📋 Test Categories

### 1. CLI Command Tests (`test_cli.py`)

Tests core CLI functionality:

- **Help System**: Ensures help commands work and are clean
- **Command Parsing**: Tests argument and option handling
- **Service Aliases**: Verifies service name aliases work
- **Error Handling**: Tests graceful error handling
- **Multi-account Support**: Tests account discovery and selection
- **Rich Formatting**: Ensures proper output formatting

**Example**:
```python
def test_help_command_no_markup_leakage(self):
    """Regression test: Ensure Rich markup is rendered, not shown as literal text"""
    result = self.runner.invoke(app, ["help"])
    assert result.exit_code == 0
    
    # Should NOT contain literal markup
    assert "[cyan]" not in result.stdout
    assert "[bold]" not in result.stdout
```

### 2. Regression Tests (`test_regression.py`)

Tests for specific bugs that have been fixed:

- **Rich Markup Bug**: Ensures `[cyan]` tags don't appear literally
- **Empty Error Box**: Validates clean CLI help output
- **Messy Help Text**: Confirms simplified help descriptions
- **Service Handling**: Tests graceful invalid service handling

**Example**:
```python
def test_rich_markup_literal_display_bug(self):
    """
    REGRESSION TEST: Rich markup showing as literal text instead of colors
    
    Issue: help command was using print() instead of rprint()
    Fix: Changed print() to rprint() in help command
    """
    result = self.runner.invoke(app, ["help"])
    assert "[cyan]" not in result.stdout, "Rich markup should be rendered, not shown literally"
```

### 3. Integration Tests (Mocked)

Tests AWS service integrations using mocks:

- **Service Calls**: Tests EC2, S3, RDS, etc. service calls
- **Multi-account**: Tests multi-account functionality
- **Error Scenarios**: Tests AWS credential and permission errors

### 4. Smoke Tests

Quick validation tests:

- **Import Integrity**: All modules import successfully
- **Basic CLI**: Core commands respond correctly
- **Help System**: Help commands work

## 🎨 Output Format Testing

We specifically test output formatting to prevent regressions:

### Rich Markup Validation

```python
# BAD: Literal markup showing
assert "[cyan]aws-super-cli ls ec2[/cyan]" not in output

# GOOD: Clean rendered output
assert "aws-super-cli ls ec2" in output
```

### CLI Response Testing

```python
# Commands should be helpful, not just fail
result = self.runner.invoke(app, ["ls"])
assert "Which AWS service would you like to list?" in result.stdout
assert "Available services:" in result.stdout
```

## 🔧 Running Specific Tests

### Individual Test Files

```bash
# Run only CLI tests
pytest tests/test_cli.py -v

# Run only regression tests
pytest tests/test_regression.py -v

# Run specific test
pytest tests/test_cli.py::TestCLICommands::test_help_command_no_markup_leakage -v
```

### Test Categories with Markers

```bash
# Run only regression tests
pytest -m regression

# Run only unit tests (no AWS dependencies)
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

### With Coverage

```bash
# Generate HTML coverage report
pytest --cov=awsx --cov-report=html

# View coverage in terminal
pytest --cov=awsx --cov-report=term-missing
```

## 📊 Pre-Release Testing

Before releasing a new version, run the comprehensive test suite:

```bash
python test_before_release.py
```

This runs:

1. **Import Integrity** - All modules import correctly
2. **CLI Basic Functionality** - All commands work
3. **Rich Formatting** - No markup leakage
4. **Service Aliases** - Aliases work correctly
5. **Full Pytest Suite** - All unit and regression tests

Expected output:
```
🚀 AWS Super CLI Pre-Release Test Suite
============================================================

📦 Testing Import Integrity
==================================================
  ✅ from aws_super_cli.cli import app
  ✅ from aws_super_cli.aws import aws_session
  ✅ from aws_super_cli.services import ec2, s3, vpc, rds, elb, iam
  ✅ from aws_super_cli.services import cost, audit

📋 Testing CLI Basic Functionality
==================================================
  ✅ Help flag
  ✅ Help command
  ✅ LS help
  ✅ Cost help
  ✅ Audit help
  ✅ Version command
  ✅ LS without args
  ✅ Cost without args
  ✅ Invalid service
  ✅ Invalid cost command

📊 CLI Tests: 10 passed, 0 failed

🎨 Testing Rich Output Formatting
==================================================
  ✅ Rich markup properly rendered
  ✅ Help content present

🔄 Testing Service Aliases
==================================================
  ✅ Alias 'instances' recognized
  ✅ Alias 'buckets' recognized
  ✅ Alias 'databases' recognized
  ✅ Alias 'functions' recognized

📊 Alias Tests: 4/4 passed

🧪 Running Pytest Suite
==================================================
  ✅ All pytest tests passed

============================================================
📋 PRE-RELEASE TEST REPORT
============================================================
Timestamp: 2024-01-20 15:30:45
Overall Status: PASS

  ✅ PASS Import Integrity
  ✅ PASS CLI Basic Functionality
  ✅ PASS Rich Formatting
  ✅ PASS Service Aliases
  ✅ PASS Pytest Suite

Summary: 5/5 test categories passed

🎉 All tests passed! Ready for release.
```

## 🐛 Adding New Tests

### For Bug Fixes (Regression Tests)

When fixing a bug, add a regression test:

```python
def test_your_bug_fix(self):
    """
    REGRESSION TEST: Brief description of the bug
    
    Issue: Detailed description of what was wrong
    Fix: Description of how it was fixed
    """
    result = self.runner.invoke(app, ["command"])
    
    # Test that the bug is fixed
    assert "expected_behavior" in result.stdout
    assert "old_broken_behavior" not in result.stdout
```

### For New Features

Add tests in `test_cli.py`:

```python
class TestNewFeature:
    """Test the new feature functionality"""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    @patch('aws_super_cli.services.new_service.new_function')
    def test_new_feature_success(self, mock_function):
        """Test successful new feature usage"""
        mock_function.return_value = expected_result
        
        result = self.runner.invoke(app, ["new-command"])
        assert result.exit_code == 0
        assert "expected output" in result.stdout
```

## 🔍 Test Configuration

### pytest.ini

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    regression: regression tests for specific bugs
    integration: integration tests (may require AWS credentials)
    unit: unit tests (no external dependencies)
    slow: slow tests (skip with -m "not slow")

asyncio_mode = auto
```

### Development Dependencies

```txt
# Testing
pytest>=7.0.0
pytest-asyncio>=0.20.0
pytest-cov>=4.0.0
pytest-mock>=3.8.0

# Development tools
black>=22.0.0
flake8>=5.0.0
mypy>=0.990
```

## 🚨 CI/CD Integration

For automated testing in CI/CD pipelines:

```bash
# In GitHub Actions, etc.
pip install -r requirements-dev.txt
python test_before_release.py

# Exit with non-zero code if tests fail
echo $?  # Should be 0 for success
```

## 💡 Best Practices

1. **Test User-Facing Behavior**: Focus on what users experience
2. **Mock AWS Calls**: Don't require real AWS credentials for tests
3. **Test Error Cases**: Ensure graceful failure handling
4. **Validate Output**: Check both content and formatting
5. **Document Issues**: Include clear regression test descriptions
6. **Run Before Release**: Always run full test suite before deployment

## 🔧 Troubleshooting

### Common Issues

**Import Errors**: Ensure you're in the project root and have installed dependencies

**Test Failures**: Check if you have the latest code and dependencies

**Coverage Issues**: Some files may need `# pragma: no cover` for untestable code

**Async Tests**: Use `pytest-asyncio` for async function testing

### Getting Help

If tests fail unexpectedly:

1. Run `python test_before_release.py` for a comprehensive report
2. Check for environment issues (Python version, dependencies)
3. Review the specific test failure messages
4. Ensure you're testing against the correct CLI version

## 📈 Continuous Improvement

The test suite should grow with the project:

- Add regression tests for every bug fix
- Add feature tests for every new feature
- Update tests when CLI behavior changes
- Maintain high coverage on critical paths
- Keep tests fast and reliable 