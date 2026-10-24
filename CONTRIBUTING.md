# Contributing to HandForge

Thanks for helping improve HandForge!

## Code of Conduct

Please read and follow our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Development Setup

```bash
# Clone the repository
git clone https://github.com/VoxHash/HandForge.git
cd HandForge

# Install dependencies
pip install -r requirements.txt

# Ensure FFmpeg is installed and on PATH
# Windows: winget install ffmpeg
# Linux: sudo apt install ffmpeg

# Run the application
python -m handforge.app
```

## Testing

Install test dependencies and run the suite from the repo root:

```bash
pip install -r requirements.txt pytest pytest-cov
# FFmpeg must be on PATH for integration tests (lavfi-generated clips)
ffmpeg -version
pytest
# Or: python -m pytest tests/ -v
```

What the suite covers:

- **Unit**: progress tracking, adaptive scheduler metrics, settings I/O, Job model, FFmpeg command construction, orchestrator concurrency caps
- **Integration** (`@pytest.mark.ffmpeg`): real encode/extract/trim pipelines and a Worker conversion when FFmpeg/ffprobe are available (auto-skipped otherwise)

Also when contributing:

- Test UI changes manually on your platform
- Prefer adding or extending pytest coverage for core conversion logic
- Check for regressions on large batches and invalid inputs

## Branching & Commit Style

- **Branches**: `feature/...`, `fix/...`, `docs/...`, `chore/...`
- **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

Examples:
- `feat: add hardware acceleration support`
- `fix: resolve progress bar stuck at 99%`
- `docs: update installation guide`

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test your changes thoroughly
5. Commit your changes with clear messages
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### PR Guidelines

- Link related issues
- Add tests if applicable
- Update documentation as needed
- Follow the PR template
- Keep diffs focused and reviewable
- Ensure code follows PEP 8 style guidelines

## Coding Standards

- Follow **PEP 8** style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and small
- Write clear commit messages
- Use type hints where appropriate

## Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/VoxHash/HandForge/issues)
2. If not, create a new issue using the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)
3. Provide as much detail as possible:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - System information (OS, Python version, FFmpeg version)

## Suggesting Features

1. Check if the feature has already been suggested
2. Create a new issue using the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md)
3. Describe the feature and its use case

## Release Process

- We use **Semantic Versioning** (MAJOR.MINOR.PATCH)
- Update [CHANGELOG.md](CHANGELOG.md) with all changes
- Tag releases with version numbers
- Release notes are generated from the changelog

## Questions?

If you have questions, please open an issue or contact contact@voxhash.dev.

Thank you for contributing to HandForge!
