---
name: system-admin
description: >
  Automate system administration tasks including managing services, monitoring
  system health, handling user accounts, configuring firewalls, managing backups,
  and diagnosing network issues. Use when managing servers, deploying services,
  troubleshooting infrastructure, performing security audits, or automating
  operations tasks.
---

# System Administration Toolkit

This skill provides automated system administration capabilities through production-grade utility scripts. You can manage services, monitor resources, handle users, configure security, perform backups, and diagnose issues on Linux/Unix systems.

## Core Capabilities

### Service Management

Manage systemd/init services with `scripts/manage_service.py`:

```bash
# Check service status
python3 scripts/manage_service.py status nginx

# Restart service
python3 scripts/manage_service.py restart nginx

# Enable at boot
python3 scripts/manage_service.py enable nginx
```

Supported operations: start, stop, restart, status, enable, disable, is-active, is-enabled

### System Monitoring

Monitor system resources with `scripts/monitor_system.py`:

```bash
# Check all resources
python3 scripts/monitor_system.py --all

# Memory usage only
python3 scripts/monitor_system.py --memory

# Set alert thresholds
python3 scripts/monitor_system.py --all --cpu-threshold 80 --memory-threshold 90
```

Monitors: CPU usage, memory, disk space, load average, network I/O

### User Management

Manage user accounts with `scripts/manage_users.py`:

```bash
# Create user
python3 scripts/manage_users.py create alice --groups sudo,docker

# List all users
python3 scripts/manage_users.py list

# Delete user (keeps home directory)
python3 scripts/manage_users.py delete bob --keep-home
```

Operations: create, delete, modify, list users and groups

### Network Diagnostics

Diagnose network issues with `scripts/network_diagnostics.py`:

```bash
# Check connectivity
python3 scripts/network_diagnostics.py ping 8.8.8.8

# Full network report
python3 scripts/network_diagnostics.py check-all

# Test specific port
python3 scripts/network_diagnostics.py port-check example.com 443
```

Features: ping, DNS resolution, port scanning, traceroute, interface info

### Firewall Management

Configure firewall rules with `scripts/configure_firewall.py`:

```bash
# Allow port
python3 scripts/configure_firewall.py allow 8080 --protocol tcp

# Block IP
python3 scripts/configure_firewall.py block 192.168.1.100

# List rules
python3 scripts/configure_firewall.py list
```

Supports: ufw, firewalld, iptables

### Backup Operations

Automate backups with `scripts/backup_system.py`:

```bash
# Backup directory
python3 scripts/backup_system.py create /var/www /backup/www

# Restore from backup
python3 scripts/backup_system.py restore /backup/www-2026-01-03.tar.gz /var/www

# List backups
python3 scripts/backup_system.py list /backup
```

Features: compression, verification, incremental backups, retention policies

## Additional Tools

All scripts support `--help` for detailed usage:

- **Update System**: `scripts/update_system.py` - Package updates and security patches
- **Disk Management**: `scripts/disk_management.py` - Partition info, usage reports, cleanup
- **Process Management**: `scripts/process_management.py` - Monitor and manage processes
- **Schedule Tasks**: `scripts/schedule_tasks.py` - Cron job management
- **Log Rotation**: `scripts/log_rotation.py` - Configure log rotation policies
- **Security Audit**: `scripts/audit_compliance.py` - Security scans and compliance checks
- **Incident Response**: `scripts/incident_response.py` - Automated incident handling
- **Remote Access**: `scripts/remote_access.py` - SSH and remote access configuration
- **Virtualization**: `scripts/virtualization_management.py` - VM and container management
- **Software Inventory**: `scripts/software_inventory.py` - Track installed software
- **Install Software**: `scripts/install_software.py` - Automated software installation

## Usage Guidelines

### Safety First

- Scripts require appropriate permissions (use sudo when needed)
- Destructive operations prompt for confirmation (bypass with `--yes`)
- Always backup critical data before major changes
- Test in non-production environments first

### Common Patterns

**Check before acting:**

```bash
# Check service status before restarting
python3 scripts/manage_service.py status nginx
python3 scripts/manage_service.py restart nginx
```

**Chain operations:**

```bash
# Update system and restart services
python3 scripts/update_system.py --security-only
python3 scripts/manage_service.py restart nginx postgresql
```

**Monitor after changes:**

```bash
# Deploy and monitor
python3 scripts/manage_service.py restart app
python3 scripts/monitor_system.py --all
python3 scripts/network_diagnostics.py check-all
```

### System Context Integration

This skill works with hooks that inject system information:

- Current OS and distribution
- Init system (systemd, launchctl, etc.)
- Running services
- Resource usage (CPU, memory, disk)
- Network configuration
- Accumulated knowledge from previous sessions

Use this context to provide accurate, system-specific commands without querying.

### Output Formats

Most scripts support multiple output formats:

```bash
# Human-readable (default)
python3 scripts/monitor_system.py --all

# JSON for parsing
python3 scripts/monitor_system.py --all --output json

# CSV for reports
python3 scripts/monitor_system.py --all --output csv
```

## Advanced Usage

For complete tool documentation and advanced scenarios:

- **[reference.md](reference.md)** - Complete documentation for all scripts
- **[examples.md](examples.md)** - Common scenarios and workflows

## Script Execution Notes

All scripts:

- Use Python 3.6+ (check with `python3 --version`)
- Include comprehensive `--help` documentation
- Support dry-run mode where applicable (`--dry-run`)
- Provide detailed logging (use `--verbose` for debug output)
- Return appropriate exit codes (0 = success, non-zero = failure)
- Handle errors gracefully with informative messages

## Quick Reference

| Task | Script | Example |
|------|--------|---------|
| Service status | manage_service.py | `python3 scripts/manage_service.py status nginx` |
| System health | monitor_system.py | `python3 scripts/monitor_system.py --all` |
| Create user | manage_users.py | `python3 scripts/manage_users.py create alice` |
| Network test | network_diagnostics.py | `python3 scripts/network_diagnostics.py ping 8.8.8.8` |
| Open firewall port | configure_firewall.py | `python3 scripts/configure_firewall.py allow 80` |
| Backup directory | backup_system.py | `python3 scripts/backup_system.py create /var/www /backup` |
| Update packages | update_system.py | `python3 scripts/update_system.py --security-only` |
| Check disk usage | disk_management.py | `python3 scripts/disk_management.py usage` |
| Manage processes | process_management.py | `python3 scripts/process_management.py list` |

## Troubleshooting

**Script not found:**

```bash
# Ensure you're in the skill directory or use full path
cd /path/to/skills/system-admin
python3 scripts/manage_service.py --help
```

**Permission denied:**

```bash
# Use sudo for privileged operations
sudo python3 scripts/manage_service.py restart nginx
```

**Command not available:**

```bash
# Scripts check for required tools and report missing dependencies
# Install missing tools based on error messages
```

## Architecture: Tools Own State

**Critical Pattern**: All scripts in this skill are the source of truth for system operations.

- **Scripts EXECUTE operations** and return structured output (JSON where possible)
- **LLM ORCHESTRATES** by calling scripts with appropriate parameters
- **LLM READS output** to understand results and report to user
- **LLM NEVER** runs system commands directly (e.g., `systemctl`, `useradd`, `iptables`)

This pattern ensures:
- Consistent error handling and logging
- Proper permission management
- Audit trails and safety checks
- Reliable, repeatable operations

## Available Commands

All scripts have corresponding slash commands for user invocation:

| Command | Script | Purpose |
|---------|--------|---------|
| `/manage-service` | manage_service.py | Start, stop, restart services |
| `/monitor-system` | monitor_system.py | Check CPU, memory, disk |
| `/manage-users` | manage_users.py | Create, delete, modify users |
| `/network-diagnostics` | network_diagnostics.py | Ping, DNS, port checks |
| `/update-system` | update_system.py | Apply system updates |
| `/configure-firewall` | configure_firewall.py | Manage firewall rules |
| `/audit-compliance` | audit_compliance.py | CIS, PCI-DSS, HIPAA audits |
| `/incident-response` | incident_response.py | Security incident handling |
| `/remote-access` | remote_access.py | SSH configuration |
| `/backup-system` | backup_system.py | Create and restore backups |
| `/disk-management` | disk_management.py | Disk usage and cleanup |
| `/virtualization` | virtualization_management.py | VM and container management |
| `/process-management` | process_management.py | Process monitoring and control |
| `/schedule-tasks` | schedule_tasks.py | Cron job management |
| `/log-rotation` | log_rotation.py | Log rotation policies |
| `/software-inventory` | software_inventory.py | Track installed packages |
| `/install-software` | install_software.py | Install/remove packages |

## Integration with Agent

When using the system-admin agent, it will:

1. Parse your natural language request
2. Identify the appropriate script(s) to use
3. **Execute the script** (not direct system commands)
4. **Read the output** to understand results
5. Chain multiple operations when needed
6. Provide rich output with diagnostics and recommendations

You don't need to remember script names - just describe what you want to accomplish.

---

**See also:**

- [Complete Tool Reference](reference.md)
- [Common Scenarios & Examples](examples.md)

## System-Specific Context

This section contains knowledge learned from previous sessions. It helps the system-admin skill provide more context-aware assistance.

### System Facts

The following system information has been learned during previous sessions:

**Operating System:**

```json
{
  "type": "darwin",
  "version": "25.0.0",
  "kernel": "Darwin",
  "architecture": "arm64"
}
```

**Services:**

```json
{
  "test-service": {
    "status": "running",
    "description": "Example service for testing"
  },
  "nginx": {
    "status": "active",
    "port": 80
  }
}
```

**Network Configuration:**

```json
{
  "hostname": "macbook-pro.local"
}
```

**Installed Packages:**

```json
{
  "jq": "1.6",
  "bash": "5.0"
}
```

**Recent Command Results:**

```json
[
  {
    "commands": [
      "ls -la",
      "uname -a"
    ],
    "notable_outputs": [
      "System is darwin/macOS"
    ],
    "errors_resolved": [],
    "timestamp": "2026-01-04T00:10:20Z"
  }
]
```

### User Preferences

The following preferences have been learned from previous interactions:

**Preferred Tools:**

```json
[
  "curl",
  "git",
  "htop",
  "tmux",
  "vim"
]
```

**Workflow Preferences:**

```json
{
  "test_before_deploy": true,
  "use_strict_mode": true
}
```

**Coding Style:**

```json
{
  "indent": "2 spaces"
}
```

### Domain Knowledge

The following patterns and practices have been learned:

---

*Last updated: 2026-01-03 18:10:58*
*This section is automatically generated from context files in `context/`*
