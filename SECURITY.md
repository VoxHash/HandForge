# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please **do not** open a public issue. Instead, please report it via email to **contact@voxhash.dev**.

Please include the following information:

- Type of vulnerability
- Full paths of source file(s) related to the vulnerability
- The location of the affected code
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the vulnerability

We will respond to your report within 48 hours and work with you to address the issue.

## Security Best Practices

When using HandForge:

1. **Keep FFmpeg Updated**: Ensure you're using the latest version of FFmpeg
2. **Verify Audio Files**: Be cautious when processing audio files from untrusted sources
3. **Check Output Files**: Verify converted files before using them
4. **Secure Settings**: Keep your settings and presets files secure if they contain sensitive information

## Known Security Considerations

- HandForge processes audio files using FFmpeg, which executes system commands
- Settings and presets are stored in JSON files in the user's home directory
- The application has file system access for reading input and writing output files

## Security Updates

Security updates will be released as patch versions (e.g., 1.0.1, 1.0.2) and will be documented in the [CHANGELOG.md](CHANGELOG.md).

Thank you for helping keep HandForge and its users safe!

