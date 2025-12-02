# Contributing to BinaApp

Thank you for considering contributing to BinaApp! This document outlines the process and guidelines.

## Code of Conduct

Be respectful, inclusive, and professional. We aim to create a welcoming environment for all contributors.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/yassirar77-cloud/binaapp/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots (if applicable)
   - Environment details (OS, browser, versions)

### Suggesting Features

1. Check existing feature requests
2. Create a new issue with:
   - Clear description of the feature
   - Use cases and benefits
   - Possible implementation approach

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/yassirar77-cloud/binaapp.git
   cd binaapp
   git remote add upstream https://github.com/yassirar77-cloud/binaapp.git
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow the code style guidelines
   - Write tests for new features
   - Update documentation as needed

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add: Brief description of your changes"
   ```

   Commit message format:
   - `Add: new feature`
   - `Fix: bug description`
   - `Update: what was updated`
   - `Refactor: what was refactored`
   - `Docs: documentation changes`

5. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill in the PR template

## Development Guidelines

### Backend (Python/FastAPI)

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for functions
- Add tests for new endpoints
- Run tests before submitting: `pytest`

```python
async def example_function(param: str) -> dict:
    """
    Brief description of what this function does

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    pass
```

### Frontend (Next.js/TypeScript)

- Use TypeScript strictly
- Follow React best practices
- Use functional components and hooks
- Add proper TypeScript types
- Run type check: `npm run type-check`

```typescript
interface Props {
  title: string
  onClick: () => void
}

export function Component({ title, onClick }: Props) {
  // Component logic
}
```

### Code Style

**Backend:**
- Use `ruff` for linting: `ruff check .`
- Use `black` for formatting: `black .`
- Line length: 100 characters

**Frontend:**
- Use ESLint: `npm run lint`
- Use Prettier (if configured)
- Indentation: 2 spaces

### Testing

**Backend:**
```bash
cd backend
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest --cov=app          # With coverage
```

**Frontend:**
```bash
cd frontend
npm test                  # Run tests
npm run type-check        # TypeScript check
```

### Documentation

- Update README.md if changing setup process
- Update SETUP.md for deployment changes
- Add inline comments for complex logic
- Update API documentation for new endpoints

## Project Structure

```
binaapp/
├── backend/           # FastAPI application
│   ├── app/
│   │   ├── api/      # API endpoints
│   │   ├── core/     # Config & security
│   │   ├── models/   # Data models
│   │   └── services/ # Business logic
│   └── tests/        # Backend tests
├── frontend/         # Next.js application
│   └── src/
│       ├── app/      # Pages (App Router)
│       ├── components/ # React components
│       └── lib/      # Utilities
├── database/         # DB schemas
└── templates/        # HTML templates
```

## Areas for Contribution

### High Priority
- [ ] Improve AI generation prompts
- [ ] Add more template designs
- [ ] Enhance error handling
- [ ] Add comprehensive tests
- [ ] Improve documentation

### Features
- [ ] Multi-language support (Chinese, Tamil)
- [ ] Custom domain support
- [ ] Advanced analytics
- [ ] Website themes/customization
- [ ] Mobile app

### Infrastructure
- [ ] Performance optimization
- [ ] Caching improvements
- [ ] Monitoring and logging
- [ ] Security enhancements

## Getting Help

- **Documentation**: Check README.md and SETUP.md
- **Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact maintainers at dev@binaapp.my

## Review Process

1. Automated tests must pass
2. Code review by maintainers
3. Changes may be requested
4. Once approved, PR will be merged

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to BinaApp! 🚀
