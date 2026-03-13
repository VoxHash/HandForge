# Security Policy

## Reporting a Vulnerability

Email **contact@voxhash.dev** with details and reproduction steps.

Please include:
- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- The location of the affected code
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability

We will respond to your report within 48 hours and work with you to address the issue.

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.3.x   | :white_check_mark: |
| 1.2.x   | :white_check_mark: |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Security Best Practices

When using HandForge:

1. **Keep FFmpeg Updated**: Ensure you're using the latest version of FFmpeg
2. **Verify Media Files**: Be cautious when processing files from untrusted sources
3. **Check Output Files**: Verify converted files before using them
4. **Secure Settings**: Keep your settings and presets files secure if they contain sensitive information

## Known Security Considerations

- HandForge processes media files using FFmpeg, which executes system commands
- Settings and presets are stored in JSON files in the user's home directory (`~/.handforge/`)
- The application has file system access for reading input and writing output files

## Security Updates

Security updates will be released as patch versions (e.g., 1.3.1, 1.3.2) and will be documented in the [CHANGELOG.md](CHANGELOG.md).

Thank you for helping keep HandForge and its users safe!
