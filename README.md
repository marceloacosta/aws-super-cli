# AWS Super CLI (awsx)

Multi-account AWS resource discovery with advanced cost analysis and service-level credit tracking.

## What is awsx?

awsx is a command-line tool for AWS resource discovery and cost analysis across multiple accounts. It solves two key problems:

1. **Multi-account resource visibility** - Query resources across all your AWS accounts in parallel
2. **Cost transparency** - Separate actual costs from credit-subsidized costs with service-level breakdown

Unlike the AWS CLI which requires manual profile switching and outputs verbose JSON, awsx provides clean tables and can query multiple accounts simultaneously.

**Unique feature**: Service-level credit usage analysis - see exactly which AWS services consume your promotional credits and at what percentage.

## Installation

```bash
pip install aws-super-cli
```

## Quick Start

```bash
# List EC2 instances across all accounts
awsx ls ec2 --all-accounts

# Cost analysis
awsx cost summary
awsx cost credits-by-service

# See available AWS profiles
awsx accounts
```

## Cost Analysis

awsx provides comprehensive cost analysis using AWS Cost Explorer API:

### Basic Cost Commands

```bash
awsx cost summary                # Overview with trends and credit breakdown
awsx cost top-spend              # Top spending services (gross costs)
awsx cost with-credits           # Top spending services (net costs after credits)
awsx cost month                  # Current month costs (matches AWS console)
awsx cost daily --days 7         # Daily cost trends
awsx cost by-account             # Multi-account cost breakdown
```

### Credit Analysis

```bash
awsx cost credits               # Credit usage trends and burn rate
awsx cost credits-by-service    # Service-level credit breakdown
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
| EC2 | `awsx ls ec2` | ✅ | `--state`, `--instance-type`, `--tag` |
| S3 | `awsx ls s3` | | `--match` |
| VPC | `awsx ls vpc` | | `--match` |
| RDS | `awsx ls rds` | | `--engine` |
| Lambda | `awsx ls lambda` | | `--runtime` |
| ELB | `awsx ls elb` | | `--type` |
| IAM | `awsx ls iam` | | `--iam-type` |

## Multi-Account Support

awsx automatically discovers AWS profiles and queries them in parallel:

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

## Usage Examples

**Resource discovery:**
```bash
# Find all running production instances
awsx ls ec2 --all-accounts --state running --match prod

# Audit IAM users across production accounts
awsx ls iam --accounts "prod-*" --iam-type users

# Find PostgreSQL databases
awsx ls rds --engine postgres --all-accounts
```

**Cost analysis:**
```bash
# Monthly financial review
awsx cost summary
awsx cost month
awsx cost credits

# Cost optimization research
awsx cost top-spend --days 7
awsx cost credits-by-service
awsx cost daily --days 30

# Multi-account cost breakdown
awsx cost by-account
```

## Why awsx?

| Feature | AWS CLI v2 | awsx | Other Tools |
|---------|------------|------|-------------|
| Multi-account queries | Manual switching | Automatic parallel | Varies |
| Output format | JSON only | Rich tables | Varies |
| Cost analysis | None | Advanced | Basic |
| Credit tracking | None | Service-level | None |
| Setup complexity | Medium | Zero config | High |

**awsx is the only tool that provides service-level credit usage analysis.**

## Technical Details

### Cost Explorer Integration

awsx fixes a major discrepancy between AWS Cost Explorer API and the AWS Console. The console excludes credits by default, but the API includes them, causing confusion. awsx handles this correctly and provides both views.

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

awsx uses your existing AWS configuration. No additional setup required.

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
| Resource listing | Free | All `awsx ls` commands |
| Cost Explorer API | $0.01/request | `awsx cost` commands |

Monthly cost estimate: $0.50-2.00 for typical usage.

## Advanced Usage

**Debugging:**
```bash
awsx cost summary --debug
awsx ls ec2 --all-accounts --debug
awsx test
```

**Filtering:**
```bash
# Fuzzy matching
awsx ls ec2 --match "web"

# Specific filters
awsx ls ec2 --state running --instance-type "t3.*"
awsx ls ec2 --tag "Environment=prod"

# Time-based cost analysis
awsx cost daily --days 14
awsx cost summary --days 90
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

**awsx** - Multi-account AWS resource discovery with service-level cost intelligence.