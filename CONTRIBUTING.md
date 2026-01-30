# Contributing to Weekly Status Report Agent

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/weekly-status-agent.git`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit: `git commit -m "Add: description of your changes"`
7. Push: `git push origin feature/your-feature-name`
8. Create a Pull Request

## Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest pytest-cov black flake8

# Run tests
pytest tests/

# Format code
black src/

# Lint code
flake8 src/
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for all public functions
- Keep functions focused and single-purpose
- Maximum line length: 100 characters

## Testing

- Write unit tests for new features
- Ensure existing tests pass
- Aim for >80% code coverage
- Test both success and failure cases

## Commit Messages

Format: `Type: Brief description`

Types:
- `Add`: New feature
- `Fix`: Bug fix
- `Update`: Enhance existing feature
- `Refactor`: Code restructuring
- `Docs`: Documentation changes
- `Test`: Test additions or changes

Examples:
- `Add: Support for Slack notifications`
- `Fix: Gmail collector date range filtering`
- `Update: Improve AI summarization prompts`

## Pull Request Guidelines

1. Provide a clear description of changes
2. Link to related issues
3. Include screenshots for UI changes
4. Ensure CI passes
5. Request review from maintainers

## Feature Requests

- Open an issue with the "enhancement" label
- Describe the use case and benefits
- Provide examples if possible

## Bug Reports

Include:
- Description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python version)
- Relevant log output

## Areas for Contribution

- Additional data sources (Slack, Calendar, etc.)
- Report templates and customization
- Performance optimizations
- Documentation improvements
- Example configurations
- Integration with other tools

## Questions?

Open an issue with the "question" label or reach out to maintainers.
