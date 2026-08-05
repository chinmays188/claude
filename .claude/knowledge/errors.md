# Errors

## Git push via HTTPS failed
- Error: `fatal: could not read Username for 'https://github.com': Device not configured`
- Cause: HTTPS remotes require stored credentials, not configured on this machine
- Resolution: Generated SSH key, added to GitHub, switched remotes to SSH

## pip/python not found
- Error: `zsh: command not found: pip` and `zsh: command not found: python`
- Cause: Python 3.9.6 was installed (system) but `pip` and `python` aliases not set
- Resolution: Use `pip3` and `python3` instead
