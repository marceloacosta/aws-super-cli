# AWS Super CLI

[![PyPI](https://img.shields.io/pypi/v/aws-super-cli.svg)](https://pypi.org/project/aws-super-cli/) [![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

A single command‑line tool for inspecting AWS accounts: list resources, check security posture, and understand spend across one or many accounts.

---

## Table of contents

1. [Why use it](#why-use-it)
2. [Installation](#installation)
3. [Quick start](#quick-start)
4. [First‑look workflow](#first-look-workflow)
5. [Command map](#command-map)
6. [Common examples](#common-examples)
7. [Arguments cheat sheet](#arguments-cheat-sheet)
8. [Costs and prerequisites](#costs-and-prerequisites)
9. [Contributing](#contributing)
10. [License](#license)

---

## Why use it

* **One binary:** no need to stitch multiple AWS utilities together.
* **Multi‑account aware:** works across named profiles, AWS SSO, or entire Organizations.
* **Readable output:** rich tables or HTML reports instead of raw JSON.
* **Opinionated defaults:** safe flags like `--all‑regions` and `--summary` help newcomers avoid blind spots.

## Installation

```bash
pip install aws-super-cli
```

Python 3.8+ and pre‑configured AWS credentials are required. No extra setup.

## Quick start

Inspect the current profile in three commands:

```bash
aws-super-cli accounts          # basic account info
aws-super-cli audit --summary   # security hot spots
aws-super-cli cost summary      # 30‑day spend overview
```

## First‑look workflow

Running the script below gives a safe, high‑level tour of any new AWS environment.

```bash
#!/usr/bin/env bash
# first-look.sh
set -euo pipefail

aws-super-cli accounts-health --details
aws-super-cli audit --summary --all-regions
aws-super-cli cost summary
aws-super-cli optimization-readiness
```

```bash
chmod +x first-look.sh
./first-look.sh   # review the outputs in your terminal
```

## Command map

| Area                   | Primary command                                                                                    | Subcommands or key flags                              |
| ---------------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| Resource discovery     | `ls [service]`                                                                                     | ec2, s3, vpc, rds, lambda, elb, iam                   |
| Security auditing      | `audit`                                                                                            | `--services`, `--summary`, `--export`                 |
| Cost insight           | `cost`                                                                                             | summary, top‑spend, by‑account, daily, month, credits |
| One‑shot cost snapshot | `cost-snapshot`                                                                                    | `--days`, `--export`                                  |
| Optimization advisor   | `optimization-readiness`, `optimization-recommendations`                                           | `--service`                                           |
| Account utilities      | `accounts`, `accounts-health`, `accounts-dashboard`, `accounts-organizations`, `accounts-nickname` | `--category`, `--details`, `--show-ous`               |
| ARN helper             | `explain [ARN]`                                                                                    | -                                                     |
| Reports                | `executive-report`                                                                                 | `--title`, `--days`                                   |
| Meta                   | `help`, `version`, `test`                                                                          | -                                                     |

Full usage for any command is available with `--help`.

## Common examples

### 1. List running EC2 instances tagged `Environment=prod` across all accounts

```bash
aws-super-cli ls ec2 --all-accounts --state running --tag Environment=prod
```

**Note**: Multi-account support (`--all-accounts`) is currently available for EC2 only. Other services will fall back to single-account queries with a warning message.

### 2. Audit S3 and IAM only, export to HTML

```bash
aws-super-cli audit --services s3,iam --export html -o s3-iam-report.html
```

### 3. Show last 7 days of daily cost trends

```bash
aws-super-cli cost daily --days 7
```

### 4. Fetch optimization tips from Compute Optimizer only

```bash
aws-super-cli optimization-recommendations --service compute-optimizer
```

## Arguments cheat sheet

* **Global:** `--region`, `--all-regions`, `--all-accounts`, `--accounts pattern`, `--match`, `--columns`, `--show-full-arns`
* **EC2‑only:** `--state`, `--instance-type`, `--tag`
* **RDS‑only:** `--engine`
* **Lambda:** `--runtime`
* **ELB:** `--type`
* **IAM:** `--iam-type`
* **Cost/Audit:** `--days`, `--services`, `--export`, `--summary`, `--output`

Refer to `aws-super-cli help` for detailed examples and usage patterns.

## Confidence scoring

Many cost commands return a **confidence** column so you can focus on easy wins first.

| Source                | High                              | Medium               | Low                     |
| --------------------- | --------------------------------- | -------------------- | ----------------------- |
| Cost Optimization Hub | Low effort, quick savings         | Moderate complexity  | Major changes needed    |
| Compute Optimizer     | Clearly over or under provisioned | General guidance     | Already tuned resources |
| Trusted Advisor       | Idle or unused resources          | Standard cost checks | Minor impact items      |

High confidence items usually deliver the best return for minimal work. Review medium items next and schedule low items only when time permits.

## Report locations & file naming

| Command                               | Default directory         | Auto‑generated name                        | `-o/--output` override |
| ------------------------------------- | ------------------------- | ------------------------------------------ | ---------------------- |
| `audit`                               | current working directory | `aws_security_audit_YYYYMMDD_HHMMSS.<ext>` | yes                    |
| `executive-report`                    | `~/aws-savings/`          | `executive-report-YYYY-MM-DD.html`         | yes                    |
| `cost-snapshot`                       | `~/aws-savings/`          | `cost-snapshot-YYYY-MM-DD.<ext>`           | yes                    |
| `optimization-recommendations`        | `~/aws-savings/`          | `{service}-YYYY-MM-DD.<ext>`               | yes                    |
| `accounts-organizations --export-csv` | current working directory | user‑supplied                              | n/a                    |

**Notes**

* `~/aws-savings/` is created automatically the first time you run any cost‑related command.
* Every file name carries a date stamp to avoid overwrites; older files are cleaned up after 90 days (configurable).
* The CLI echoes the exact path each time a report is generated.
* Supported extensions vary by command (`csv`, `html`, `json`, `txt`).

## Costs and prerequisites

| Requirement | Notes                                                                                      |
| ----------- | ------------------------------------------------------------------------------------------ |
| Python      | 3.8 or newer                                                                               |
| IAM access  | STS, EC2 Describe, S3 List\*, RDS Describe\*, etc. Grant the principle of least privilege. |
| API charges | Cost Explorer calls cost about $0.01 each. Trusted Advisor requires Business/Enterprise support plan. Typical usage under $2/month. |

## Contributing

Bug reports, features, and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License 2.0 Marcelo Acosta
