# Contributing to AWS Super CLI

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
- `audit`: Security audit features
- `docs`: Documentation
- `test`: Testing

## README.md Update Guidelines

The README.md must be updated when implementing features that change the user experience. **Always include README.md updates in the same commit as the feature implementation.**

### When to Update README.md

**REQUIRED Updates:**
- New commands or CLI options
- New service support
- Changes to existing command behavior
- New security audit features
- Installation requirement changes
- New configuration options

**Optional Updates:**
- Internal refactoring (no user-visible changes)
- Test improvements
- Documentation fixes

### What to Update in README.md

1. **Quick Start section** - Add new commands to basic examples
2. **Supported Services table** - Add new services with their commands and filters
3. **Usage Examples** - Include realistic examples of new features
4. **Command reference** - Document new flags and options
5. **Feature descriptions** - Explain what the new functionality does

### README.md Update Process

1. **During feature development**: Update README.md as you build
2. **Test examples**: Ensure all README.md examples actually work
3. **Single commit**: Include README.md changes in the same commit as the feature
4. **Commit message**: Use `feat(scope): description` (not separate `docs:` commit)

### Example: Adding Security Audit Features

**Bad approach:**
```bash
# Separate commits
git commit -m "feat(audit): add security audit command"
git commit -m "docs: update README with audit examples"
```

**Good approach:**
```bash
# Single commit with README updates included
git commit -m "feat(audit): add comprehensive security audit command

- Implement S3 bucket security scanning
- Add IAM user privilege analysis  
- Include security scoring system (0-100)
- Add --summary flag for quick overview
- Update README.md with audit examples and documentation"
```

### README.md Sections to Maintain

Keep these sections current:
- **Quick Start**: Basic commands that work immediately
- **Supported Services**: Accurate table with current services
- **Usage Examples**: Real-world scenarios that demonstrate value
- **Multi-Account Support**: Current account selection options
- **Cost Analysis**: Current cost command functionality
- **Security Audit**: Current audit capabilities (when implemented)

### Quality Standards

- **Test all examples**: Every command in README.md must work
- **Keep it current**: Remove outdated information
- **Be specific**: Use real service names, not placeholders
- **Show value**: Examples should demonstrate actual use cases
- **Professional tone**: Match the enterprise-grade standard

### Pull Request Guidelines

- All commits in a PR must follow these standards
- Use meaningful branch names (`feat/rds-filtering`, `fix/cost-api-dates`)
- Include tests for new features
- Update documentation as needed
- **Include README.md updates for user-facing changes**

### Why These Standards?

Professional commit messages:
- Make the project suitable for enterprise adoption
- Enable proper automated changelog generation
- Improve code review efficiency
- Demonstrate technical maturity to potential contributors
- Build trust with developers evaluating the tool

Updated README.md ensures:
- Users can immediately use new features
- Documentation matches actual functionality
- Examples work out of the box
- Professional presentation for enterprise evaluation

### Enforcement

These guidelines apply to:
- All new commits
- All pull requests
- All contributor submissions

Commits that don't follow these standards may be rejected or require amendments.

### Commit History

We maintain a clean, professional commit history. All future commits must follow these guidelines to ensure the repository maintains enterprise-grade standards. 