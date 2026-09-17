---
name: ansible-dev
description: Ansible Development
---

# Ansible Development Skill

## Overview
This skill helps you create, debug, and manage Ansible playbooks, roles, collections, and automation workflows. It provides best practices for infrastructure as code, proper YAML formatting, idempotent task design, and effective use of Ansible's features.

## When to Use This Skill
Use this skill when you need to:
- Create new Ansible playbooks or roles
- Debug failing Ansible tasks or playbooks
- Refactor existing automation for better idempotency
- Design inventory structures and variable hierarchies
- Work with Ansible modules, filters, and plugins
- Develop custom Ansible modules or plugins
- Implement CI/CD for infrastructure automation
- Troubleshoot connectivity or authentication issues

## Core Ansible Concepts

### Directory Structure
Standard Ansible project layout:
```
ansible-project/
├── ansible.cfg
├── inventory/
│   ├── production/
│   │   ├── hosts.yml
│   │   └── group_vars/
│   └── staging/
│       ├── hosts.yml
│       └── group_vars/
├── playbooks/
│   ├── site.yml
│   ├── webservers.yml
│   └── databases.yml
├── roles/
│   ├── common/
│   │   ├── tasks/
│   │   ├── handlers/
│   │   ├── templates/
│   │   ├── files/
│   │   ├── vars/
│   │   ├── defaults/
│   │   └── meta/
│   └── nginx/
└── group_vars/
    ├── all.yml
    └── webservers.yml
```

## Best Practices

### 1. Idempotency
**Critical Rule:** Every task should be idempotent - running it multiple times should produce the same result without unintended side effects.

**Good Examples:**
```yaml
# ✅ Idempotent - uses ansible.builtin.package
- name: Ensure nginx is installed
  ansible.builtin.package:
    name: nginx
    state: present

# ✅ Idempotent - uses creates parameter
- name: Download application
  ansible.builtin.command: wget https://example.com/app.tar.gz
  args:
    creates: /opt/app.tar.gz

# ✅ Idempotent - checks state before acting
- name: Ensure service is running
  ansible.builtin.service:
    name: nginx
    state: started
    enabled: yes
```

**Bad Examples:**
```yaml
# ❌ Not idempotent - always executes
- name: Download application
  ansible.builtin.command: wget https://example.com/app.tar.gz

# ❌ Not idempotent - always restarts
- name: Restart nginx
  ansible.builtin.command: systemctl restart nginx

# ❌ Not idempotent - always appends
- name: Add line to file
  ansible.builtin.shell: echo "config=value" >> /etc/app.conf
```

### 2. YAML Formatting
```yaml
# ✅ Good - clear, readable, properly structured
---
- name: Configure web servers
  hosts: webservers
  become: yes
  
  vars:
    nginx_port: 80
    app_user: webapp
  
  tasks:
    - name: Install nginx
      ansible.builtin.package:
        name: nginx
        state: present
      notify: Restart nginx
    
    - name: Copy nginx configuration
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
        owner: root
        group: root
        mode: '0644'
      notify: Restart nginx
  
  handlers:
    - name: Restart nginx
      ansible.builtin.service:
        name: nginx
        state: restarted
```

### 3. Module Usage
Always use Fully Qualified Collection Names (FQCNs):
```yaml
# ✅ Good - FQCN format
- name: Create directory
  ansible.builtin.file:
    path: /opt/app
    state: directory
    mode: '0755'

# ⚠️ Acceptable but not recommended
- name: Create directory
  file:
    path: /opt/app
    state: directory
```

### 4. Variable Precedence
Understand Ansible's variable precedence (lowest to highest):
1. role defaults
2. inventory file/script group vars
3. inventory group_vars/all
4. playbook group_vars/all
5. inventory group_vars/*
6. playbook group_vars/*
7. inventory file/script host vars
8. inventory host_vars/*
9. playbook host_vars/*
10. host facts / cached set_facts
11. play vars
12. play vars_prompt
13. play vars_files
14. role vars
15. block vars
16. task vars
17. include_vars
18. set_facts / registered vars
19. role params
20. include params
21. extra vars (always win)

### 5. Error Handling
```yaml
# Ignore errors when acceptable
- name: Check if file exists
  ansible.builtin.stat:
    path: /tmp/myfile
  register: file_check
  ignore_errors: yes

# Use failed_when for custom failure conditions
- name: Run command
  ansible.builtin.command: /usr/bin/mycommand
  register: result
  failed_when: "'ERROR' in result.stderr"

# Use changed_when to control change status
- name: Check configuration
  ansible.builtin.command: /usr/bin/check_config
  register: config_check
  changed_when: false

# Use blocks for error handling
- name: Handle errors with blocks
  block:
    - name: Risky task
      ansible.builtin.command: /usr/bin/risky_operation
  rescue:
    - name: Handle failure
      ansible.builtin.debug:
        msg: "Operation failed, running recovery"
    - name: Recovery task
      ansible.builtin.command: /usr/bin/recover
  always:
    - name: Always runs
      ansible.builtin.debug:
        msg: "Cleanup complete"
```

## Common Patterns

### 1. Role Structure
```yaml
# roles/webserver/tasks/main.yml
---
- name: Include OS-specific variables
  ansible.builtin.include_vars: "{{ ansible_os_family }}.yml"

- name: Install web server
  ansible.builtin.package:
    name: "{{ webserver_package }}"
    state: present

- name: Configure web server
  ansible.builtin.template:
    src: webserver.conf.j2
    dest: "{{ webserver_config_path }}"
    mode: '0644'
  notify: restart webserver

- name: Ensure web server is running
  ansible.builtin.service:
    name: "{{ webserver_service }}"
    state: started
    enabled: yes
```

### 2. Conditional Execution
```yaml
# When clauses
- name: Install package on RedHat family
  ansible.builtin.yum:
    name: httpd
    state: present
  when: ansible_os_family == "RedHat"

# Multiple conditions
- name: Complex conditional
  ansible.builtin.debug:
    msg: "This runs on Ubuntu 20.04+"
  when:
    - ansible_distribution == "Ubuntu"
    - ansible_distribution_version is version('20.04', '>=')

# Conditional with registered variables
- name: Check if file exists
  ansible.builtin.stat:
    path: /etc/myapp.conf
  register: config_file

- name: Create default config if missing
  ansible.builtin.copy:
    src: myapp.conf.default
    dest: /etc/myapp.conf
  when: not config_file.stat.exists
```

### 3. Loops
```yaml
# Simple loop
- name: Install multiple packages
  ansible.builtin.package:
    name: "{{ item }}"
    state: present
  loop:
    - nginx
    - postgresql
    - redis

# Loop with dictionary
- name: Create multiple users
  ansible.builtin.user:
    name: "{{ item.name }}"
    groups: "{{ item.groups }}"
    state: present
  loop:
    - { name: 'alice', groups: 'admin,developers' }
    - { name: 'bob', groups: 'developers' }
    - { name: 'carol', groups: 'operators' }

# Loop with loop_control
- name: Process items with clearer output
  ansible.builtin.debug:
    msg: "Processing {{ item }}"
  loop:
    - one
    - two
    - three
  loop_control:
    label: "{{ item }}"
    pause: 2
```

### 4. Templates (Jinja2)
```jinja2
{# templates/nginx.conf.j2 #}
user {{ nginx_user }};
worker_processes {{ ansible_processor_vcpus }};

{% if nginx_ssl_enabled %}
ssl_protocols TLSv1.2 TLSv1.3;
ssl_certificate {{ nginx_ssl_cert }};
ssl_certificate_key {{ nginx_ssl_key }};
{% endif %}

upstream backend {
{% for host in groups['backend_servers'] %}
    server {{ hostvars[host]['ansible_default_ipv4']['address'] }}:8080;
{% endfor %}
}

server {
    listen {{ nginx_port }};
    server_name {{ nginx_server_name }};
    
    location / {
        proxy_pass http://backend;
    }
}
```

## Debugging Techniques

### 1. Verbose Output
```bash
# Basic verbosity
ansible-playbook playbook.yml -v

# More verbose (shows task execution details)
ansible-playbook playbook.yml -vv

# Very verbose (shows connection debugging)
ansible-playbook playbook.yml -vvv

# Maximum verbosity (connection debugging + plugin details)
ansible-playbook playbook.yml -vvvv
```

### 2. Debug Module
```yaml
- name: Show all facts
  ansible.builtin.debug:
    var: ansible_facts

- name: Show specific variable
  ansible.builtin.debug:
    var: my_variable

- name: Show custom message
  ansible.builtin.debug:
    msg: "The value is {{ my_variable }}"

- name: Debug with verbosity control
  ansible.builtin.debug:
    msg: "Only shows with -v or higher"
    verbosity: 1
```

### 3. Check and Diff Modes
```bash
# Check mode - don't make changes, just show what would change
ansible-playbook playbook.yml --check

# Diff mode - show file differences
ansible-playbook playbook.yml --diff

# Combine both
ansible-playbook playbook.yml --check --diff
```

### 4. Start at Specific Task
```bash
# Start at a specific task
ansible-playbook playbook.yml --start-at-task="Install nginx"

# Use tags to run specific tasks
ansible-playbook playbook.yml --tags "configuration,deployment"

# Skip specific tags
ansible-playbook playbook.yml --skip-tags "testing"
```

## Testing Strategies

### 1. Syntax Validation
```bash
# Check playbook syntax
ansible-playbook playbook.yml --syntax-check

# Lint playbooks with ansible-lint
ansible-lint playbook.yml
```

### 2. Molecule Testing
```yaml
# molecule/default/molecule.yml
---
dependency:
  name: galaxy
driver:
  name: docker
platforms:
  - name: instance
    image: geerlingguy/docker-ubuntu2004-ansible:latest
    pre_build_image: true
provisioner:
  name: ansible
verifier:
  name: ansible
```

### 3. Tag Strategy for Testing
```yaml
---
- name: Web server setup
  hosts: webservers
  
  tasks:
    - name: Install packages
      ansible.builtin.package:
        name: nginx
        state: present
      tags:
        - packages
        - nginx
    
    - name: Configure nginx
      ansible.builtin.template:
        src: nginx.conf.j2
        dest: /etc/nginx/nginx.conf
      tags:
        - configuration
        - nginx
    
    - name: Run tests
      ansible.builtin.command: /usr/local/bin/test_nginx.sh
      tags:
        - never
        - testing
```

## Security Best Practices

### 1. Ansible Vault
```bash
# Create encrypted file
ansible-vault create secrets.yml

# Encrypt existing file
ansible-vault encrypt vars.yml

# Edit encrypted file
ansible-vault edit secrets.yml

# Use vault password file
ansible-playbook playbook.yml --vault-password-file ~/.vault_pass

# Use in playbook
ansible-playbook playbook.yml --ask-vault-pass
```
```yaml
# Using vaulted variables
---
- name: Deploy application
  hosts: webservers
  vars_files:
    - secrets.yml  # encrypted file
  
  tasks:
    - name: Configure database connection
      ansible.builtin.template:
        src: db_config.j2
        dest: /etc/app/database.yml
        mode: '0600'
```

### 2. No Hardcoded Secrets
```yaml
# ❌ Bad - hardcoded credentials
- name: Configure database
  ansible.builtin.template:
    src: db.conf.j2
    dest: /etc/db.conf
  vars:
    db_password: "hardcoded_password_123"

# ✅ Good - use vault or environment variables
- name: Configure database
  ansible.builtin.template:
    src: db.conf.j2
    dest: /etc/db.conf
  vars:
    db_password: "{{ vault_db_password }}"

# ✅ Good - use no_log for sensitive tasks
- name: Create user with password
  ansible.builtin.user:
    name: appuser
    password: "{{ vault_user_password | password_hash('sha512') }}"
  no_log: true
```

### 3. Privilege Escalation
```yaml
# Escalate for entire play
- name: System configuration
  hosts: all
  become: yes
  become_method: sudo
  
  tasks:
    - name: This runs as root
      ansible.builtin.package:
        name: nginx
        state: present

# Escalate for specific tasks only
- name: Mixed privilege tasks
  hosts: all
  
  tasks:
    - name: Runs as regular user
      ansible.builtin.debug:
        msg: "No privileges needed"
    
    - name: Runs as root
      ansible.builtin.package:
        name: nginx
        state: present
      become: yes
```

## Performance Optimization

### 1. Parallelism
```ini
# ansible.cfg
[defaults]
forks = 20  # Run on 20 hosts simultaneously
```

### 2. Fact Gathering
```yaml
# Disable fact gathering when not needed
- name: Quick task
  hosts: all
  gather_facts: no
  
  tasks:
    - name: Simple command
      ansible.builtin.command: /usr/bin/quick_check

# Gather specific facts only
- name: Selective facts
  hosts: all
  gather_facts: yes
  gather_subset:
    - '!all'
    - '!min'
    - network
```

### 3. Async Tasks
```yaml
# Run long tasks asynchronously
- name: Long running operation
  ansible.builtin.command: /usr/bin/long_process
  async: 3600  # Maximum runtime in seconds
  poll: 0      # Don't wait, fire and forget
  register: long_task

# Check on async task later
- name: Check on long task
  ansible.builtin.async_status:
    jid: "{{ long_task.ansible_job_id }}"
  register: job_result
  until: job_result.finished
  retries: 30
  delay: 10
```

### 4. Pipelining
```ini
# ansible.cfg
[defaults]
pipelining = True
```

## Common Modules Reference

### File Operations
```yaml
# ansible.builtin.file - manage files and directories
- name: Create directory
  ansible.builtin.file:
    path: /opt/app
    state: directory
    owner: appuser
    group: appgroup
    mode: '0755'

# ansible.builtin.copy - copy files
- name: Copy configuration file
  ansible.builtin.copy:
    src: app.conf
    dest: /etc/app/app.conf
    owner: root
    group: root
    mode: '0644'
    backup: yes

# ansible.builtin.template - render Jinja2 templates
- name: Deploy templated config
  ansible.builtin.template:
    src: nginx.conf.j2
    dest: /etc/nginx/nginx.conf
    validate: 'nginx -t -c %s'

# ansible.builtin.lineinfile - modify single lines
- name: Ensure line in config
  ansible.builtin.lineinfile:
    path: /etc/ssh/sshd_config
    regexp: '^PermitRootLogin'
    line: 'PermitRootLogin no'
    state: present

# ansible.builtin.blockinfile - insert/update block of lines
- name: Add block to file
  ansible.builtin.blockinfile:
    path: /etc/hosts
    block: |
      192.168.1.10 host1
      192.168.1.11 host2
    marker: "# {mark} ANSIBLE MANAGED BLOCK"
```

### Package Management
```yaml
# ansible.builtin.package - generic package manager
- name: Install package (distro-agnostic)
  ansible.builtin.package:
    name: nginx
    state: present

# ansible.builtin.apt - Debian/Ubuntu
- name: Install on Debian/Ubuntu
  ansible.builtin.apt:
    name: nginx
    state: present
    update_cache: yes
    cache_valid_time: 3600

# ansible.builtin.yum - RedHat/CentOS
- name: Install on RHEL/CentOS
  ansible.builtin.yum:
    name: nginx
    state: present
```

### Service Management
```yaml
# ansible.builtin.service - manage services
- name: Ensure service is running
  ansible.builtin.service:
    name: nginx
    state: started
    enabled: yes

# ansible.builtin.systemd - systemd-specific
- name: Manage systemd service
  ansible.builtin.systemd:
    name: nginx
    state: restarted
    daemon_reload: yes
    enabled: yes
```

### Command Execution
```yaml
# ansible.builtin.command - run commands (no shell processing)
- name: Run command
  ansible.builtin.command: /usr/bin/myapp --version
  register: version
  changed_when: false

# ansible.builtin.shell - run shell commands (with shell processing)
- name: Run shell command
  ansible.builtin.shell: |
    cd /opt/app
    ./configure && make && make install
  args:
    creates: /opt/app/bin/myapp

# ansible.builtin.script - run local script on remote
- name: Execute local script remotely
  ansible.builtin.script: /local/path/to/script.sh
  args:
    creates: /tmp/script.done
```

## Inventory Management

### 1. Static Inventory
```yaml
# inventory/production/hosts.yml
---
all:
  children:
    webservers:
      hosts:
        web1.example.com:
          ansible_host: 192.168.1.10
        web2.example.com:
          ansible_host: 192.168.1.11
      vars:
        nginx_port: 80
        app_environment: production
    
    databases:
      hosts:
        db1.example.com:
          ansible_host: 192.168.1.20
          postgresql_version: 14
      vars:
        db_backup_enabled: true
    
    loadbalancers:
      hosts:
        lb1.example.com:
```

### 2. Dynamic Inventory
```python
#!/usr/bin/env python3
# inventory/aws_ec2.py - example dynamic inventory

import json
import boto3

def get_inventory():
    ec2 = boto3.client('ec2')
    response = ec2.describe_instances()
    
    inventory = {
        'webservers': {
            'hosts': [],
            'vars': {}
        },
        '_meta': {
            'hostvars': {}
        }
    }
    
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            if instance['State']['Name'] == 'running':
                tags = {tag['Key']: tag['Value'] 
                       for tag in instance.get('Tags', [])}
                
                if tags.get('Role') == 'webserver':
                    hostname = instance['PublicDnsName']
                    inventory['webservers']['hosts'].append(hostname)
                    inventory['_meta']['hostvars'][hostname] = {
                        'ansible_host': instance['PublicIpAddress']
                    }
    
    return inventory

if __name__ == '__main__':
    print(json.dumps(get_inventory(), indent=2))
```

## Error Messages and Solutions

### Common Issues

**1. SSH Connection Refused**
```yaml
# Solution: Add connection parameters
- name: Configure host
  hosts: myserver
  vars:
    ansible_user: ubuntu
    ansible_ssh_private_key_file: ~/.ssh/my_key.pem
    ansible_python_interpreter: /usr/bin/python3
```

**2. Permission Denied**
```yaml
# Solution: Use become
- name: Install package
  ansible.builtin.package:
    name: nginx
    state: present
  become: yes
```

**3. Module Not Found**
```bash
# Solution: Install required collection
ansible-galaxy collection install community.general
```

**4. Unreachable Host**
```bash
# Solution: Test connectivity first
ansible all -m ping -i inventory/hosts.yml
```

## File Creation Workflow

When creating Ansible files:

1. **Always create in `/home/claude` first** for development
2. **Test and validate** the content
3. **Copy to `/mnt/user-data/outputs/`** for user delivery
4. **Use proper file extensions**: `.yml` for YAML, `.j2` for Jinja2 templates
5. **Include comments** explaining complex logic

Example workflow:
```bash
# Create playbook
create_file /home/claude/webserver_setup.yml

# Validate syntax
ansible-playbook /home/claude/webserver_setup.yml --syntax-check

# Copy to outputs
cp /home/claude/webserver_setup.yml /mnt/user-data/outputs/
```

## Resources

- Official Docs: https://docs.ansible.com
- Best Practices: https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html
- Module Index: https://docs.ansible.com/ansible/latest/collections/index_module.html
- Galaxy (roles/collections): https://galaxy.ansible.com

---

**Remember:** Ansible is about declarative infrastructure - describe the desired state, not the steps to get there. Focus on idempotency, clarity, and maintainability in all playbooks and roles.
