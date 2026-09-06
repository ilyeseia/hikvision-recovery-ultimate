# Contributing to Hikvision Recovery

Thank you for your interest in contributing to Hikvision Recovery! This guide will help you get started.

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Making Changes](#making-changes)
5. [Testing](#testing)
6. [Code Style](#code-style)
7. [Commit Guidelines](#commit-guidelines)
8. [Pull Request Process](#pull-request-process)
9. [Release Process](#release-process)

---

## 🤝 Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold this code.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Git
- Hikvision device for testing (optional but recommended)

### Fork & Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/hikvision-recovery-ultimate.git
cd hikvision-recovery-ultimate
```

---

## 🛠️ Development Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
```

### 2. Install in Development Mode

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

This installs the package with all development dependencies:
- `pytest` - Testing
- `ruff` - Fast linting
- `black` - Code formatting
- `mypy` - Type checking
- `bandit` - Security analysis
- `safety` - Dependency vulnerability scanning

### 3. Verify Installation

```bash
# Run tests
pytest tests/ -v

# Check CLI
hikvision --help

# Import test
python -c "import hikvision_recovery; print(hikvision_recovery.__version__)"
```

---

## 🔧 Making Changes

### Branching Strategy

- `main` - Stable releases only
- `develop` - Integration branch for features
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Urgent production fixes

### Create a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

### Types of Contributions

1. **Bug Fixes** - Fix issues in ISAPI client, SDK wrapper, or CLI
2. **New Features** - Add new functionality (search, download, PTZ, etc.)
3. **Documentation** - Improve README, docstrings, CLI help
4. **Tests** - Add unit/integration tests
5. **Refactoring** - Code improvements without behavior changes
6. **Performance** - Optimize slow operations
6. **Security** - Fix vulnerabilities

---

## ✅ Testing

### Run All Tests

```bash
# Run with coverage
pytest tests/ -v --cov=hikvision_recovery --cov-report=term-missing

# Run specific test file
pytest tests/test_models.py -v

# Run with specific marker
pytest tests/ -v -k "not integration"
```

### Test Requirements

- **Unit tests** for all new functions/methods
- **Integration tests** for device communication (if device available)
- **Coverage target**: ≥80% for new code
- **All tests must pass** before PR

### Manual Testing

If you have a Hikvision device:

```bash
# Test ISAPI client
hikvision --host 192.168.1.100 --user admin --pass "***" info

# Test search
hikvision --host 192.168.1.100 --user admin --pass "***" search --days 7

# Test SDK wrapper (requires HCNetSDK libraries)
python -c "
from hikvision_recovery.core.sdk import SDKClient, LoginConfig
client = SDKClient()
client.login(LoginConfig(host='192.168.1.100', username='admin', password='***'))
print('SDK OK')
"
```

---

## 🎨 Code Style

We use automated tools to enforce consistent style:

### Formatting (Black)

```bash
# Format code
black hikvision_recovery tests

# Check formatting
black --check hikvision_recovery tests
```

### Linting (Ruff)

```bash
# Lint
ruff check hikvision_recovery tests

# Auto-fix
ruff check --fix hikvision_recovery tests
```

### Type Checking (MyPy)

```bash
mypy hikvision_recovery --ignore-missing-imports
```

### Pre-commit Hooks (Recommended)

```bash
pip install pre-commit
pre-commit install
```

This runs all checks automatically on commit.

---

## 📝 Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style (formatting, etc.) |
| `refactor` | Code refactoring |
| `perf` | Performance improvement |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |
| `ci` | CI/CD changes |
| `security` | Security fixes |
| `breaking` | Breaking changes |

### Examples

```bash
feat(sdk): add playback speed control
fix(isapi): handle timeout in download_recording
docs(readme): add Docker installation instructions
test(models): add tests for RecordingInfo duration
refactor(core): simplify search_criteria.to_isapi_params
perf(sdk): optimize file search pagination
security(deps): update requests to fix CVE-2024-XXXXX
breaking(api): rename download_recording to download_file
```

### Scope

Use scopes to indicate affected component:
- `isapi` - ISAPI client
- `sdk` - HCNetSDK wrapper
- `cli` - Command line interface
- `models` - Data models
- `tests` - Tests
- `docs` - Documentation
- `ci` - CI/CD
- `deps` - Dependencies

---

## 🔄 Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines (run `black`, `ruff`, `mypy`)
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] Coverage ≥80% for new code
- [ ] Documentation updated if needed
- [ ] No breaking changes without discussion
- [ ] Changelog entry added (if applicable)

### PR Title

Follow conventional commits format:
```
feat(sdk): add smart search for face detection
```

### PR Description Template

```markdown
## Description
What does this PR do? Why is it needed?

## Related Issues
Fixes #123
Related to #456

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass (if applicable)
- [ ] Manual testing done on device

## Breaking Changes
- [ ] No breaking changes
- [ ] Breaking changes documented

## Screenshots/Logs
(if applicable)
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainers
3. **Approval** from at least 1 maintainer
4. **Merge** after approval

---

## 📦 Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)
- **Major** - Breaking changes
- **Minor** - New features (backward compatible)
- **Patch** - Bug fixes (backward compatible)

### Release Steps

1. **Create release branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/v1.2.0
   ```

2. **Update version** in:
   - `hikvision_recovery/__init__.py`
   - `setup.py`
   - `pyproject.toml`

4. **Run full test suite**
   ```bash
   pytest tests/ -v --cov=hikvision_recovery --cov-fail-under=80
   ```

5. **Create PR to main**
   - Title: `release: v1.2.0`
   - Get approvals

5. **Tag and push**
   ```bash
   git checkout main
   git merge release/v1.2.0
   git tag -a v1.2.0 -m "Release v1.2.0"
   git push origin main --tags
   ```

6. **GitHub Actions** automatically:
   - Runs full test suite
   - Builds package
   - Publishes to PyPI (trusted publishing)
   - Creates GitHub Release
   - Builds Docker image

7. **Cleanup**
   ```bash
   git branch -d release/v1.2.0
   ```

---

## 🏷️ Issue Labels

| Label | Description |
|-------|-------------|
| `bug` | Something isn't working |
| `enhancement` | New feature request |
| `documentation` | Documentation improvement |
| `good first issue` | Good for newcomers |
| `help wanted` | Extra attention needed |
| `security` | Security related |
| `breaking` | Breaking change |
| `needs-triage` | Needs initial review |
| `needs-review` | Ready for code review |
| `dependencies` | Dependency updates |
| `ci/cd` | CI/CD related |

---

## 🤔 Need Help?

- Check existing [Issues](https://github.com/hikvision-recovery-ultimate/issues)
- Read the [Documentation](README.md)
- Ask in [Discussions](https://github.com/hikvision-recovery-ultimate/discussions)
- Contact maintainers

---

## 🙏 Recognition

Contributors will be recognized in:
- `CHANGELOG.md`
- Release notes
- GitHub Contributors page

Thank you for contributing to Hikvision Recovery! 🎉