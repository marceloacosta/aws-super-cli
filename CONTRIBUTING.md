# Contributing to awsx

## Commit Message Guidelines

We follow strict commit message standards to maintain a professional repository suitable for enterprise use.

### Format

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring without feature changes
- `test`: Adding or modifying tests
- `chore`: Maintenance tasks, dependency updates
- `perf`: Performance improvements

### Rules

**DO:**
- Use present tense ("add feature" not "added feature")
- Use imperative mood ("move cursor to..." not "moves cursor to...")
- Keep first line under 72 characters
- Be specific and technical
- Reference issue numbers when applicable

```bash
feat(rds): add PostgreSQL engine filtering support
fix(cost): resolve Cost Explorer API date range handling
docs: update installation requirements
refactor(aws): improve multi-account session management
test(ec2): add integration tests for instance filtering
chore: update boto3 to version 1.34.0
```

**DON'T:**
- Use emojis (🚀, 💰, ✨, etc.)
- Use marketing language ("Revolutionary", "Amazing", "Game-changing")
- Use excessive punctuation or hype
- Write vague messages ("fix stuff", "updates", "changes")
- Use executive buzzwords ("World's first", "Cutting-edge", "Next-generation")

### Examples

**Good:**
```
feat(lambda): add runtime filtering with --runtime flag
fix(cost): handle Cost Explorer API rate limiting
docs: add multi-account setup instructions
refactor(cli): extract common table formatting logic
```

**Bad:**
```
🚀 Revolutionary Lambda Support - Game-changing runtime filters!!!
Fix some cost stuff 💰
Update docs with AMAZING new features ✨
Big refactor that changes everything!!!
```

### Scope Guidelines

Common scopes for this project:
- `ec2`, `s3`, `rds`, `lambda`, `elb`, `iam`, `vpc`: Service-specific changes
- `cost`: Cost analysis features
- `cli`: Command-line interface changes
- `aws`: AWS integration and authentication
- `multi-account`: Multi-account functionality
- `docs`: Documentation
- `test`: Testing

### Pull Request Guidelines

- All commits in a PR must follow these standards
- Use meaningful branch names (`feat/rds-filtering`, `fix/cost-api-dates`)
- Include tests for new features
- Update documentation as needed

### Why These Standards?

Professional commit messages:
- Make the project suitable for enterprise adoption
- Enable proper automated changelog generation
- Improve code review efficiency
- Demonstrate technical maturity to potential contributors
- Build trust with developers evaluating the tool

### Enforcement

These guidelines apply to:
- All new commits
- All pull requests
- All contributor submissions

Commits that don't follow these standards may be rejected or require amendments. 