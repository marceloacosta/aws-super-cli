# AWS Super CLI (awsx)

See your AWS resources across all accounts in one command with beautiful, readable output.

## What is awsx?

awsx is a command-line tool that makes AWS resource discovery fast and painless. Instead of wrestling with verbose JSON output and switching between AWS profiles, awsx gives you clean tables showing exactly what you need to know.

**Key differentiator**: Query multiple AWS accounts simultaneously. Most tools require you to switch profiles manually - awsx discovers and queries all your accessible accounts in parallel.

## Installation

```bash
# Install from PyPI (recommended)
pip install awsx

# Or install from source
git clone https://github.com/marceloacosta/awsx.git
cd awsx
pip install .
```

## Quick Start

```bash
# List EC2 instances across all accounts
awsx ls ec2 --all-accounts

# Find production resources across all accounts
awsx ls ec2 --all-accounts --match prod

# List RDS instances with specific engine
awsx ls rds --engine postgres

# See available AWS profiles
awsx accounts
```

## Supported Services

| Service | Command | Filters |
|---------|---------|---------|
| EC2 | `ls ec2` | `--state`, `--instance-type`, `--tag` |
| S3 | `ls s3` | `--match` |
| VPC | `ls vpc` | `--match` |
| RDS | `ls rds` | `--engine` |
| Lambda | `ls lambda` | `--runtime` |
| ELB | `ls elb` | `--type` |
| IAM | `ls iam` | `--iam-type` |

## Multi-Account Support

awsx automatically discovers AWS profiles and can query multiple accounts in parallel:

```bash
# Query all accessible accounts
awsx ls ec2 --all-accounts

# Query specific accounts
awsx ls s3 --accounts "prod-account,staging-account"

# Pattern matching
awsx ls rds --accounts "prod-*"

# List available profiles
awsx accounts
```

## Examples

**Find all running EC2 instances across accounts:**
```bash
awsx ls ec2 --all-accounts --state running
```

**Audit IAM users across production accounts:**
```bash
awsx ls iam --accounts "prod-*" --iam-type users
```

**Find PostgreSQL databases:**
```bash
awsx ls rds --engine postgres --all-accounts
```

**Security audit - find resources matching pattern:**
```bash
awsx ls ec2 --all-accounts --match "public\|dmz"
```

## Output Format

awsx produces clean, readable tables instead of verbose JSON:

```
                                    EC2 Instances                                    
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Instance ID         ┃ Name                   ┃ State      ┃ Type         ┃ Account      ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ i-0123456789abcdef0 │ prod-web-server        │ running    │ t3.medium    │ 123456789012 │
│ i-0abcdef1234567890 │ staging-api            │ stopped    │ t2.small     │ 123456789012 │
└─────────────────────┴────────────────────────┴────────────┴──────────────┴──────────────┘

Found 2 EC2 instances across 1 accounts and 2 regions
```

## Configuration

awsx uses your existing AWS configuration (`~/.aws/config` and `~/.aws/credentials`). It supports:

- AWS profiles
- AWS SSO
- IAM roles
- Environment variables
- EC2 instance profiles

No additional configuration required.

## Filtering and Search

**Fuzzy matching** across names, tags, and other fields:
```bash
awsx ls ec2 --match "web"        # Finds "web-server", "webapp", etc.
```

**Specific filters** for precise results:
```bash
awsx ls ec2 --state running --instance-type "t3.*"
awsx ls rds --engine postgres
awsx ls lambda --runtime python
```

**Tag filtering**:
```bash
awsx ls ec2 --tag "Environment=prod"
```

## Why awsx vs alternatives?

| Tool | Multi-Account | Rich Output | AWS Native |
|------|---------------|-------------|------------|
| AWS CLI v2 | Manual switching | JSON only | Yes |
| awsx | Automatic parallel | Rich tables | Yes |
| Steampipe | Complex setup | SQL required | Yes |
| aws-vault | Credential helper | No listing | Partial |

## Requirements

- Python 3.8+
- Valid AWS credentials
- Required permissions: `ec2:Describe*`, `s3:List*`, `rds:Describe*`, `lambda:List*`, `elasticloadbalancing:Describe*`, `iam:List*`, `sts:GetCallerIdentity`

## Contributing

Contributions welcome. Please ensure your code:
- Follows existing patterns in `/awsx/services/`
- Includes appropriate error handling
- Works with multi-account infrastructure
- Maintains consistent table formatting

## License

Apache 2.0

## Roadmap

- Cost analysis commands
- Security audit commands  
- Plugin system for custom services
- Export to JSON/CSV
- Real-time resource monitoring