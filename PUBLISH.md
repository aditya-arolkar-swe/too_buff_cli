# Publishing to PyPI

## Prerequisites

1. Create a PyPI account at https://pypi.org/account/register/
2. Create an API token at https://pypi.org/manage/account/token/
   - Scope: "Entire account" or "Project: toobuff"
   - Save the token (starts with `pypi-`)

## Publishing Steps

### 1. Configure Poetry with your PyPI token

```bash
poetry config pypi-token.pypi your-pypi-token-here
```

Or set it as an environment variable:
```bash
export POETRY_PYPI_TOKEN_PYPI=your-pypi-token-here
```

### 2. Build the package

```bash
poetry build
```

This creates `dist/toobuff-0.1.0.tar.gz` and a wheel file.

### 3. Publish to PyPI

```bash
poetry publish
```

This will upload to PyPI. The package will be available at:
https://pypi.org/project/toobuff/

### 4. Test the installation

After publishing, test that it works:

```bash
pipx install toobuff
toobuff --version
```

### 5. Update the install script URL

Once published, the install script at `install.sh` will work. Make sure it's committed to your main branch so the curl command works:

```bash
curl -fsSL https://raw.githubusercontent.com/aditya-arolkar-swe/too_buff_cli/main/install.sh | bash
```

## Updating Versions

When you want to release a new version:

1. Update `version` in `pyproject.toml`
2. Build and publish:
   ```bash
   poetry build
   poetry publish
   ```

## Notes

- Test your package locally first: `pip install dist/toobuff-*.whl`
- The first publish creates the project on PyPI
- Subsequent publishes update the existing project
- PyPI doesn't allow re-uploading the same version, so increment version for each release

