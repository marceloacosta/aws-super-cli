# AWS Super CLI (awsx)

See your AWS empire in one command—beautiful, fast, across all accounts with **revolutionary cost and credit analysis**.

## What is awsx?

awsx is the most comprehensive AWS cost and resource discovery tool ever built. While other tools struggle with basic resource listing, awsx gives you:

🔥 **Multi-account resource discovery** across 7 AWS services  
💰 **Advanced cost analysis** with gross/net cost separation  
💳 **Revolutionary credit tracking** showing exactly where your credits go  
📊 **Trend analysis** with daily patterns and monthly forecasting  
🚀 **Production-ready speed** with parallel account queries  

**Game-changing differentiator**: The only tool that shows **credit usage by service** - see exactly which AWS services consume your promotional credits and at what percentage coverage.

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
# Complete cost overview with credit analysis
awsx cost summary

# See which services are eating your credits
awsx cost credits-by-service

# Find expensive resources across all accounts
awsx ls ec2 --all-accounts --match prod

# Track current month spending (matches AWS console exactly)
awsx cost month

# See available AWS profiles
awsx accounts
```

## Cost & Credit Analysis 💰

The most advanced AWS cost analysis system available:

### Core Cost Commands

```bash
# Complete financial overview
awsx cost summary                    # Gross/net costs, trends, credit impact

# Service breakdown  
awsx cost top-spend                  # Top spending services (without credits)
awsx cost with-credits               # Top spending services (after credits)

# Time-based analysis
awsx cost month                      # Current month (matches AWS console)
awsx cost daily --days 7             # Daily trends and cost spikes

# Multi-account analysis
awsx cost by-account                 # Costs across multiple AWS accounts
```

### Revolutionary Credit Analysis 💳

**World's first** service-level credit breakdown:

```bash
# Credit usage patterns and trends
awsx cost credits                    # 3-month credit usage trends, burn rate

# Service-level credit breakdown  
awsx cost credits-by-service         # Which services consume most credits
```

**Sample Credit Analysis Output:**
```
💳 Top Services by Credit Usage (Last 30 days)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Service                                ┃   Gross Cost ┃ Credits Applied ┃     Net Cost ┃  Coverage  ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ Amazon Relational Database Service     │      $366.62 │         $366.62 │       <$0.01 │   100.0%   │
│ Amazon Elastic Compute Cloud - Compute │       $89.65 │          $89.65 │        $0.00 │   100.0%   │
│ Amazon Virtual Private Cloud           │       $83.05 │          $83.05 │        $0.00 │   100.0%   │
└────────────────────────────────────────┴──────────────┴─────────────────┴──────────────┴────────────┘

💯 Services with >90% credit coverage: RDS, EC2, VPC
```

### Cost Intelligence Features

✅ **Gross vs Net Costs**: See both "what you'd pay" vs "what you actually pay"  
✅ **Credit Transparency**: Exact credit usage by service with coverage percentages  
✅ **Trend Analysis**: Monthly consumption patterns and daily variations  
✅ **Console Accuracy**: Matches AWS Billing console exactly (credits filter fix)  
✅ **Budget Planning**: Separate planning costs from actual cash flow  
✅ **Multi-Account**: Cost analysis across multiple AWS accounts  

## Supported Services

| Service | Command | Multi-Account | Filters |
|---------|---------|---------------|---------|
| EC2 | `ls ec2` | ✅ | `--state`, `--instance-type`, `--tag` |
| S3 | `ls s3` | ➖ | `--match` |
| VPC | `ls vpc` | ➖ | `--match` |
| RDS | `ls rds` | ➖ | `--engine` |
| Lambda | `ls lambda` | ➖ | `--runtime` |
| ELB | `ls elb` | ➖ | `--type` |
| IAM | `ls iam` | ➖ | `--iam-type` |

## Multi-Account Support

awsx automatically discovers AWS profiles and can query multiple accounts in parallel:

```bash
# Query all accessible accounts
awsx ls ec2 --all-accounts

# Query specific accounts
awsx ls s3 --accounts "prod-account,staging-account"

# Pattern matching
awsx ls rds --accounts "prod-*"

# List available profiles and test access
awsx accounts
```

## Real-World Examples

### Cost Management

**Monthly financial review:**
```bash
awsx cost summary                    # Overview with trends
awsx cost month                      # Current month tracking
awsx cost credits                    # Credit burn rate analysis
```

**Cost optimization research:**
```bash
awsx cost top-spend --days 7         # Find weekly cost drivers
awsx cost credits-by-service         # See credit-subsidized services
awsx cost daily --days 30            # Spot cost anomalies
```

**Budget planning session:**
```bash
awsx cost summary --days 90          # Quarterly cost trends
awsx cost by-account                 # Multi-account breakdown
```

### Resource Discovery

**Security audit across accounts:**
```bash
awsx ls ec2 --all-accounts --match "public\|dmz"
awsx ls iam --accounts "prod-*" --iam-type users
```

**Architecture inventory:**
```bash
awsx ls rds --engine postgres --all-accounts
awsx ls lambda --runtime python --all-accounts
```

**Cost-focused resource review:**
```bash
# Find expensive running instances
awsx ls ec2 --all-accounts --state running --instance-type "m5.*\|c5.*"
```

## Revolutionary Credit Insights

### Credit Usage Patterns 📈

```bash
💳 AWS Credits Analysis
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric                    ┃ Value                ┃ Notes                                              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Total Credits (3 months)  │ $996.82              │ Credits consumed in analysis period               │
│ Average Monthly Usage     │ $489.66              │ Based on complete months only                     │
│ Current Month Usage       │ $17.51               │ Month-to-date credit consumption                  │
│ Projected Month Total     │ $175.10              │ Estimated total for current month                 │
└───────────────────────────┴──────────────────────┴────────────────────────────────────────────────────┘

📈 Monthly Credit Usage Trend
  2025-04: $293.40 credits applied
  2025-05: $685.91 credits applied  ← Peak usage month
  2025-06: $17.51 credits applied   ← Current month projection
```

### Business Value

🎯 **For Finance Teams:**
- **Budget Accuracy**: Separate gross costs (for budgeting) from net costs (for cash flow)
- **Credit Runway**: Track promotional credit consumption rates
- **Vendor Negotiations**: Understand true AWS usage patterns

💡 **For Engineering Teams:**  
- **Cost Optimization**: Identify highest-impact services for optimization
- **Architecture Decisions**: Credit coverage analysis for service selection
- **Resource Planning**: Daily cost trends for capacity planning

📊 **For Management:**
- **Executive Dashboards**: Professional cost summaries with trends
- **ROI Analysis**: Credit value vs. actual infrastructure investment
- **Strategic Planning**: Consumption forecasting for AWS negotiations

## Output Format

Beautiful, professional tables that executives love:

```
💰 Cost Summary
Period: Last 30 days
Gross Cost (without credits): $665.75
Net Cost (with credits):      $-0.05
Credits Applied:              $665.79
Daily Average (gross):        $22.19
Daily Average (net):          <$0.01
Trend: ↗ +123.7%
```

## Why awsx vs alternatives?

| Tool | Multi-Account | Rich Output | Cost Analysis | Credit Analysis | AWS Native |
|------|---------------|-------------|---------------|-----------------|------------|
| AWS CLI v2 | Manual switching | JSON only | No | No | Yes |
| **awsx** | **Automatic parallel** | **Rich tables** | **Advanced** | **Revolutionary** | **Yes** |
| Steampipe | Complex setup | SQL required | Limited | No | Yes |
| aws-vault | Credential helper | No listing | No | No | Partial |
| Third-party tools | Varies | Varies | Basic | No | No |

**awsx is the only tool with service-level credit analysis.**

## Configuration

awsx uses your existing AWS configuration (`~/.aws/config` and `~/.aws/credentials`). It supports:

- AWS profiles
- AWS SSO  
- IAM roles
- Environment variables
- EC2 instance profiles

**Zero additional configuration required.**

## Requirements

- Python 3.8+
- Valid AWS credentials
- **Resource listing**: `ec2:Describe*`, `s3:List*`, `rds:Describe*`, `lambda:List*`, `elasticloadbalancing:Describe*`, `iam:List*`, `sts:GetCallerIdentity`
- **Cost analysis**: `ce:GetCostAndUsage`, `ce:GetDimensionValues`

## Cost Information

### Tool Cost
**awsx is completely free** - open source with Apache 2.0 license.

### AWS API Costs
**Most operations are FREE:**

| Operation | Cost | Used By |
|-----------|------|---------|
| `describe_instances`, `list_buckets`, etc. | **FREE** | All `awsx ls` commands |
| `sts:GetCallerIdentity` | **FREE** | Authentication |
| Cost Explorer API | **$0.01 per request** | `awsx cost` commands |

### Typical Usage Costs
```bash
# Resource listing (always free)
awsx ls ec2 --all-accounts    # $0.00
awsx ls s3 --all-regions      # $0.00

# Cost analysis (minimal charges)
awsx cost summary             # $0.01
awsx cost credits             # $0.01  
awsx cost top-spend           # $0.01
```

**Monthly cost estimate: $0.50-2.00** for typical usage

The cost is **negligible compared to engineer time saved** - typically less than a cup of coffee per month while saving hours of manual AWS console work and providing insights unavailable anywhere else.

## Advanced Features

### Debugging & Troubleshooting
```bash
# Debug mode for API troubleshooting
awsx cost summary --debug
awsx ls ec2 --all-accounts --debug

# Test AWS connectivity
awsx test
```

### Filtering & Search
```bash
# Fuzzy matching across names, tags, and other fields
awsx ls ec2 --match "web"        # Finds "web-server", "webapp", etc.

# Specific filters for precise results
awsx ls ec2 --state running --instance-type "t3.*"
awsx ls rds --engine postgres
awsx ls lambda --runtime python

# Tag filtering
awsx ls ec2 --tag "Environment=prod"

# Time-based cost analysis
awsx cost daily --days 14
awsx cost summary --days 90
```

## Contributing

Contributions welcome! We're especially interested in:

- Additional AWS service support
- Enhanced cost analysis features  
- Multi-account support for more services
- Performance optimizations

Please ensure your code:
- Follows existing patterns in `/awsx/services/`
- Includes appropriate error handling
- Works with multi-account infrastructure
- Maintains consistent table formatting

## License

Apache 2.0

## Roadmap

- ✅ **Multi-account resource discovery**
- ✅ **Revolutionary credit analysis**  
- ✅ **Advanced cost intelligence**
- 🔄 **Security audit commands**
- 🔄 **Plugin system for custom services**
- 🔄 **Export to JSON/CSV**
- 🔄 **Real-time resource monitoring**
- 🔄 **AI-powered cost optimization recommendations**

---

**awsx** - The only AWS tool with revolutionary credit intelligence. See your AWS empire in one command. 🚀