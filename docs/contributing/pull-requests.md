# Pull Request Guidelines

This document outlines the process for submitting pull requests to the YAML Workflow Engine project.

## Before Creating a Pull Request

1. **Check Existing Issues/PRs**
   - Search for existing issues or pull requests
   - Create an issue for discussion if needed
   - Link your PR to relevant issues

2. **Update Your Fork**
   ```bash
   # Add the upstream remote if not already done
   git remote add upstream https://github.com/orieg/yaml-workflow.git
   
   # Fetch upstream changes
   git fetch upstream
   
   # Rebase your branch on upstream main
   git checkout your-feature-branch
   git rebase upstream/main
   ```

3. **Run Local Checks**
   ```bash
   # Install development dependencies
   pip install -e ".[dev]"
   
   # Format code
   black src/ tests/
   isort --profile black src/ tests/
   
   # Run type checking
   mypy src/
   
   # Run tests
   pytest tests/
   
   # Check documentation
   mkdocs serve
   ```

## Creating a Pull Request

### Branch Naming

Follow these conventions:
- `feature/description` for new features
- `fix/description` for bug fixes
- `docs/description` for documentation changes
- `refactor/description` for code refactoring
- `test/description` for test improvements

Example: `feature/add-http-retry`

### Commit Messages

Use conventional commit format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat(tasks): add HTTP request retry mechanism

- Implement exponential backoff retry logic
- Add retry configuration options
- Include retry count in task output

Closes #123
```

### Pull Request Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code follows style guide
- [ ] All tests passing
- [ ] Type hints added/updated
- [ ] Docstrings updated

## Related Issues
Fixes #123

## Additional Notes
Any additional information that reviewers should know
```

## Review Process

### Requesting Reviews

1. **Choose Reviewers**
   - Request review from maintainers
   - Tag relevant stakeholders
   - Consider domain expertise

2. **Draft PRs**
   - Use draft PRs for work in progress
   - Mark as ready when complete

### Addressing Feedback

1. **Review Comments**
   - Respond to all comments
   - Explain your changes
   - Link to relevant documentation

2. **Making Changes**
   ```bash
   # Make requested changes
   git add .
   git commit -m "fix: address review feedback"
   
   # Update PR
   git push origin your-feature-branch
   ```

3. **Resolving Discussions**
   - Mark resolved when addressed
   - Request re-review when ready

## After Merge

1. **Clean Up**
   ```bash
   # Switch to main
   git checkout main
   
   # Update main
   git pull upstream main
   
   # Delete local branch
   git branch -d your-feature-branch
   
   # Delete remote branch
   git push origin --delete your-feature-branch
   ```

2. **Follow Up**
   - Close related issues
   - Update project documentation
   - Monitor CI/CD pipeline

## Tips for Success

1. **Keep PRs Focused**
   - One feature/fix per PR
   - Split large changes into smaller PRs
   - Link related PRs

2. **Quality Checks**
   - Run all tests locally
   - Check code coverage
   - Verify documentation

3. **Communication**
   - Be responsive to feedback
   - Ask questions if unclear
   - Update PR description as needed

4. **Documentation**
   - Update relevant docs
   - Add inline comments
   - Include examples

## Common Issues

### PR Too Large
Split into smaller, logical chunks:
1. Core functionality
2. Additional features
3. Documentation
4. Tests

### Failed Checks
Common fixes:
```bash
# Code style
black src/ tests/
isort --profile black src/ tests/

# Type checking
mypy src/

# Fix test failures
pytest tests/ -v
```

### Merge Conflicts
```bash
# Update main
git fetch upstream
git checkout main
git merge upstream/main

# Rebase your branch
git checkout your-feature-branch
git rebase main

# Force push if needed
git push origin your-feature-branch --force-with-lease
``` 