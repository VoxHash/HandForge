# Contributing to HandForge

Thank you for your interest in contributing to HandForge! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/VoxHash/HandForge/issues)
2. If not, create a new issue using the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)
3. Provide as much detail as possible:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - System information (OS, Python version, FFmpeg version)

### Suggesting Features

1. Check if the feature has already been suggested
2. Create a new issue using the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md)
3. Describe the feature and its use case

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test your changes thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/VoxHash/HandForge.git
cd HandForge

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m handforge.app
```

### Coding Standards

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Write clear commit messages

### Testing

- Test your changes on both Windows and Linux if possible
- Test with various audio formats
- Verify UI changes work correctly
- Check for any regressions

## Questions?

If you have questions, please open an issue or contact contact@voxhash.dev.

Thank you for contributing to HandForge!

