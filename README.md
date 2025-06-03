# AWS Super CLI

[![PyPI version](https://badge.fury.io/py/aws-super-cli.svg)](https://badge.fury.io/py/aws-super-cli)

## What is AWS Super CLI?

AWS Super CLI is a command-line tool for AWS resource discovery and cost analysis across multiple accounts. It solves two key problems:

1. **Multi-account resource visibility**: See all your AWS resources across accounts in unified tables
2. **Service-level cost intelligence**: Get detailed cost analysis with credit allocation per service

Unlike the AWS CLI which requires manual profile switching and outputs verbose JSON, AWS Super CLI provides clean tables and can query multiple accounts simultaneously.

**Unique feature**: Service-level credit usage analysis - see exactly which AWS services consume your promotional credits and at what percentage.

## Installation

```bash
pip install aws-super-cli
```

## Quick Start

```bash
# List EC2 instances across all accounts
aws-super-cli ls ec2 --all-accounts

# Get cost summary with credit analysis
aws-super-cli cost summary
aws-super-cli cost credits-by-service

# List available AWS profiles
aws-super-cli accounts
```

## Cost Analysis

AWS Super CLI provides comprehensive cost analysis using AWS Cost Explorer API:

### Basic Cost Commands

```bash
aws-super-cli cost summary                # Overview with trends and credit breakdown
aws-super-cli cost top-spend              # Top spending services (gross costs)
aws-super-cli cost with-credits           # Top spending services (net costs after credits)
aws-super-cli cost month                  # Current month costs (matches AWS console)
aws-super-cli cost daily --days 7         # Daily cost trends
aws-super-cli cost by-account             # Multi-account cost breakdown
```

### Credit Analysis

```bash
aws-super-cli cost credits               # Credit usage trends and burn rate
aws-super-cli cost credits-by-service    # Service-level credit breakdown
```

### Key Features

- **Gross vs Net costs**: Separate "what you'd pay" from "what you actually pay"
- **Console accuracy**: Matches AWS Billing console exactly (fixes API/console discrepancy)
- **Credit transparency**: See exactly where promotional credits are applied
- **Service-level breakdown**: Which services consume most credits with coverage percentages
- **Trend analysis**: Historical patterns and monthly forecasting

### Example Output

```
💰 Cost Summary
Period: Last 30 days
Gross Cost (without credits): $665.75
Net Cost (with credits):      $-0.05
Credits Applied:              $665.79
Daily Average (gross):        $22.19
Trend: ↗ +123.7%
```

```
Top Services by Credit Usage
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Service                                ┃   Gross Cost ┃ Credits Applied ┃     Net Cost ┃  Coverage  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Amazon Relational Database Service     │      $366.62 │         $366.62 │       <$0.01 │   100.0%   │
│ Amazon Elastic Compute Cloud - Compute │       $89.65 │          $89.65 │        $0.00 │   100.0%   │
│ Amazon Virtual Private Cloud           │       $83.05 │          $83.05 │        $0.00 │   100.0%   │
└────────────────────────────────────────┴──────────────┴─────────────────┴──────────────┴────────────┘
```

## Supported Services

| Service | Command | Multi-Account | Filters |
|---------|---------|---------------|---------|
| EC2 | `aws-super-cli ls ec2` | ✅ | `--state`, `--instance-type`, `--tag` |
| S3 | `aws-super-cli ls s3` | | `--match` |
| VPC | `aws-super-cli ls vpc` | | `--match` |
| RDS | `aws-super-cli ls rds` | | `--engine` |
| Lambda | `aws-super-cli ls lambda` | | `--runtime` |
| ELB | `aws-super-cli ls elb` | | `--type` |
| IAM | `aws-super-cli ls iam` | | `--iam-type` |

## Multi-Account Support

aws-super-cli automatically discovers AWS profiles and queries them in parallel:

```bash
# Query all accessible accounts
aws-super-cli ls ec2 --all-accounts

# Query specific accounts
aws-super-cli ls s3 --accounts "prod-account,staging-account"

# Pattern matching
aws-super-cli ls rds --accounts "prod-*"

# List available profiles
aws-super-cli accounts
```

## Usage Examples

**Resource discovery:**
```bash
# Find all running production instances
aws-super-cli ls ec2 --all-accounts --state running --match prod

# Audit IAM users across production accounts
aws-super-cli ls iam --accounts "prod-*" --iam-type users

# Find PostgreSQL databases
aws-super-cli ls rds --engine postgres --all-accounts
```

**Cost analysis:**
```bash
# Monthly financial review
aws-super-cli cost summary
aws-super-cli cost month
aws-super-cli cost credits

# Cost optimization research
aws-super-cli cost top-spend --days 7
aws-super-cli cost credits-by-service
aws-super-cli cost daily --days 30

# Multi-account cost breakdown
aws-super-cli cost by-account
```

## Why AWS Super CLI?

| Feature | AWS CLI v2 | AWS Super CLI | Other Tools |
|---------|------------|------|-------------|
| Multi-account queries | Manual switching | Automatic parallel | Varies |
| Output format | JSON only | Rich tables | Varies |
| Cost analysis | None | Advanced | Basic |
| Credit tracking | None | Service-level | None |
| Setup complexity | Medium | Zero config | High |

**AWS Super CLI is the only tool that provides service-level credit usage analysis.**

## Technical Details

### Cost Explorer Integration

AWS Super CLI fixes a major discrepancy between AWS Cost Explorer API and the AWS Console. The console excludes credits by default, but the API includes them, causing confusion. AWS Super CLI handles this correctly and provides both views.

### Multi-Account Architecture

- Automatically discovers profiles from `~/.aws/config` and `~/.aws/credentials`
- Executes API calls in parallel across accounts and regions
- Handles AWS SSO, IAM roles, and standard credentials
- Respects rate limits and implements proper error handling

### Performance

- Parallel API calls across accounts/regions
- Efficient data aggregation and formatting
- Minimal API requests (most resource listing is free)
- Cost Explorer API usage: ~$0.01 per cost analysis command

## Configuration

AWS Super CLI uses your existing AWS configuration. No additional setup required.

Supports:
- AWS profiles
- AWS SSO
- IAM roles
- Environment variables
- EC2 instance profiles

## Requirements

- Python 3.8+
- AWS credentials configured
- Permissions:
  - Resource listing: `ec2:Describe*`, `s3:List*`, `rds:Describe*`, `lambda:List*`, `elasticloadbalancing:Describe*`, `iam:List*`, `sts:GetCallerIdentity`
  - Cost analysis: `ce:GetCostAndUsage`, `ce:GetDimensionValues`

## API Costs

| Operation | Cost | Commands |
|-----------|------|----------|
| Resource listing | Free | All `aws-super-cli ls` commands |
| Cost Explorer API | $0.01/request | `aws-super-cli cost` commands |

Monthly cost estimate: $0.50-2.00 for typical usage.

## Advanced Usage

**Debugging:**
```bash
aws-super-cli cost summary --debug
aws-super-cli ls ec2 --all-accounts --debug
aws-super-cli test
```

**Filtering:**
```bash
# Fuzzy matching
aws-super-cli ls ec2 --match "web"

# Specific filters
aws-super-cli ls ec2 --state running --instance-type "t3.*"
aws-super-cli ls ec2 --tag "Environment=prod"

# Time-based cost analysis
aws-super-cli cost daily --days 14
aws-super-cli cost summary --days 90
```

## Contributing

Contributions welcome. Areas of interest:

- Additional AWS service support
- Enhanced cost analysis features
- Multi-account support for more services
- Performance optimizations

## License

Apache 2.0

---

**AWS Super CLI** - Multi-account AWS resource discovery with service-level cost intelligence.