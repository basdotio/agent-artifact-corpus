import os
import json
import tempfile
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP
mcp = FastMCP("ansible-lint")

# Check if ansible-lint is available
def check_ansible_lint_available() -> bool:
    """Check if ansible-lint is installed and available."""
    return shutil.which("ansible-lint") is not None

# Helper function to run ansible-lint commands
async def run_ansible_lint(args: List[str], input_content: str = None) -> Dict[str, Any]:
    """Run ansible-lint with specified arguments and return parsed results."""
    if not check_ansible_lint_available():
        return {
            "error": "ansible-lint is not installed. Please install it with: pip install ansible-lint",
            "success": False
        }
    
    cmd = ["ansible-lint"] + args
    
    try:
        if input_content:
            # Create temporary file for content
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as temp_file:
                temp_file.write(input_content)
                temp_file_path = temp_file.name
            
            # Add temp file to command
            cmd.append(temp_file_path)
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            finally:
                # Clean up temp file
                os.unlink(temp_file_path)
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
        
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode in [0, 2]  # 0 = no issues, 2 = issues found
        }
    
    except subprocess.TimeoutExpired:
        return {
            "error": "ansible-lint command timed out after 60 seconds",
            "success": False
        }
    except Exception as e:
        return {
            "error": f"Failed to run ansible-lint: {str(e)}",
            "success": False
        }

def parse_lint_output(output: str, format_type: str = "json") -> Dict[str, Any]:
    """Parse ansible-lint output based on format type."""
    if format_type == "json":
        try:
            return json.loads(output) if output.strip() else []
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON output", "raw_output": output}
    else:
        return {"raw_output": output}

@mcp.tool()
async def lint_playbook(
    content: str, 
    profile: str = "basic", 
    format_type: str = "json",
    rules: Optional[List[str]] = None
) -> Any:
    """
    Lint Ansible playbook content and return issues with suggestions.
    
    Args:
        content: YAML content of the Ansible playbook
        profile: Quality profile (min, basic, moderate, safety, shared, production)
        format_type: Output format (json, brief, full, sarif)
        rules: Specific rules to check (optional)
    """
    args = [f"--format={format_type}"]
    
    if profile:
        args.extend(["--profile", profile])
    
    if rules:
        args.extend(["--tags", ",".join(rules)])
    
    result = await run_ansible_lint(args, content)
    
    if not result["success"]:
        return {
            "error": result.get("error", "ansible-lint failed"),
            "stderr": result.get("stderr", ""),
            "success": False
        }
    
    parsed_output = parse_lint_output(result["stdout"], format_type)
    
    return {
        "success": True,
        "issues": parsed_output,
        "profile_used": profile,
        "format": format_type,
        "summary": {
            "total_issues": len(parsed_output) if isinstance(parsed_output, list) else 0,
            "return_code": result["returncode"]
        }
    }

@mcp.tool()
async def lint_file(
    file_path: str, 
    profile: str = "basic", 
    format_type: str = "json"
) -> Any:
    """
    Lint a specific Ansible file and return issues.
    
    Args:
        file_path: Path to the Ansible file to lint
        profile: Quality profile to use
        format_type: Output format
    """
    if not os.path.exists(file_path):
        return {
            "error": f"File not found: {file_path}",
            "success": False
        }
    
    args = [f"--format={format_type}"]
    
    if profile:
        args.extend(["--profile", profile])
    
    args.append(file_path)
    
    result = await run_ansible_lint(args)
    
    if not result["success"]:
        return {
            "error": result.get("error", "ansible-lint failed"),
            "stderr": result.get("stderr", ""),
            "success": False
        }
    
    parsed_output = parse_lint_output(result["stdout"], format_type)
    
    return {
        "success": True,
        "file_path": file_path,
        "issues": parsed_output,
        "profile_used": profile,
        "format": format_type,
        "summary": {
            "total_issues": len(parsed_output) if isinstance(parsed_output, list) else 0,
            "return_code": result["returncode"]
        }
    }

@mcp.tool()
async def lint_role(role_path: str, profile: str = "basic") -> Any:
    """
    Comprehensive linting of an Ansible role directory.
    
    Args:
        role_path: Path to the Ansible role directory
        profile: Quality profile to use
    """
    if not os.path.exists(role_path):
        return {
            "error": f"Role path not found: {role_path}",
            "success": False
        }
    
    if not os.path.isdir(role_path):
        return {
            "error": f"Path is not a directory: {role_path}",
            "success": False
        }
    
    args = ["--format=json"]
    
    if profile:
        args.extend(["--profile", profile])
    
    args.append(role_path)
    
    result = await run_ansible_lint(args)
    
    if not result["success"]:
        return {
            "error": result.get("error", "ansible-lint failed"),
            "stderr": result.get("stderr", ""),
            "success": False
        }
    
    parsed_output = parse_lint_output(result["stdout"], "json")
    
    # Analyze role structure
    role_structure = {}
    role_dirs = ["tasks", "handlers", "vars", "defaults", "meta", "templates", "files"]
    
    for dir_name in role_dirs:
        dir_path = os.path.join(role_path, dir_name)
        role_structure[dir_name] = {
            "exists": os.path.exists(dir_path),
            "files": list(os.listdir(dir_path)) if os.path.exists(dir_path) else []
        }
    
    return {
        "success": True,
        "role_path": role_path,
        "issues": parsed_output,
        "role_structure": role_structure,
        "profile_used": profile,
        "summary": {
            "total_issues": len(parsed_output) if isinstance(parsed_output, list) else 0,
            "return_code": result["returncode"]
        }
    }

@mcp.tool()
async def list_rules(tags: Optional[str] = None) -> Any:
    """
    List available ansible-lint rules, optionally filtered by tags.
    
    Args:
        tags: Comma-separated list of tags to filter rules
    """
    args = ["--list-rules"]
    
    if tags:
        args.extend(["--tags", tags])
    
    result = await run_ansible_lint(args)
    
    if not result["success"]:
        return {
            "error": result.get("error", "Failed to list rules"),
            "stderr": result.get("stderr", ""),
            "success": False
        }
    
    return {
        "success": True,
        "rules_output": result["stdout"],
        "tags_filter": tags
    }

@mcp.tool()
async def list_tags() -> Any:
    """List all available tags for ansible-lint rules."""
    args = ["--list-tags"]
    
    result = await run_ansible_lint(args)
    
    if not result["success"]:
        return {
            "error": result.get("error", "Failed to list tags"),
            "stderr": result.get("stderr", ""),
            "success": False
        }
    
    return {
        "success": True,
        "tags_output": result["stdout"]
    }

@mcp.tool()
async def validate_syntax(content: str) -> Any:
    """
    Quick syntax validation of Ansible content.
    
    Args:
        content: YAML content to validate
    """
    # Use only syntax-related rules for faster checking
    args = ["--format=json", "--tags", "syntax"]
    
    result = await run_ansible_lint(args, content)
    
    if not result["success"]:
        return {
            "error": result.get("error", "Syntax validation failed"),
            "stderr": result.get("stderr", ""),
            "success": False
        }
    
    parsed_output = parse_lint_output(result["stdout"], "json")
    syntax_issues = [issue for issue in parsed_output if isinstance(issue, dict) and 'syntax' in issue.get('tag', '').lower()]
    
    return {
        "success": True,
        "syntax_valid": len(syntax_issues) == 0,
        "syntax_issues": syntax_issues,
        "summary": {
            "total_syntax_issues": len(syntax_issues)
        }
    }

@mcp.tool()
async def check_best_practices(
    content: str, 
    context: str = "production",
    exclude_rules: Optional[List[str]] = None
) -> Any:
    """
    Check Ansible content against best practices for specific context.
    
    Args:
        content: YAML content to check
        context: Context for best practices (development, staging, production)
        exclude_rules: Rules to exclude from checking
    """
    # Map context to appropriate profile
    profile_mapping = {
        "development": "basic",
        "staging": "moderate", 
        "production": "production"
    }
    
    profile = profile_mapping.get(context, "basic")
    args = [f"--format=json", "--profile", profile]
    
    if exclude_rules:
        args.extend(["--skip-list", ",".join(exclude_rules)])
    
    result = await run_ansible_lint(args, content)
    
    if not result["success"]:
        return {
            "error": result.get("error", "Best practices check failed"),
            "stderr": result.get("stderr", ""),
            "success": False
        }
    
    parsed_output = parse_lint_output(result["stdout"], "json")
    
    # Categorize issues by severity
    categorized_issues = {
        "critical": [],
        "major": [],
        "minor": [],
        "info": []
    }
    
    for issue in parsed_output:
        if isinstance(issue, dict):
            # Categorize based on rule type and context
            rule_id = issue.get("rule", {}).get("id", "")
            if any(critical_rule in rule_id for critical_rule in ["syntax-check", "load-failure"]):
                categorized_issues["critical"].append(issue)
            elif context == "production" and any(major_rule in rule_id for major_rule in ["risky-shell-pipe", "command-instead-of-module"]):
                categorized_issues["major"].append(issue)
            elif any(minor_rule in rule_id for minor_rule in ["name", "yaml"]):
                categorized_issues["minor"].append(issue)
            else:
                categorized_issues["info"].append(issue)
    
    return {
        "success": True,
        "context": context,
        "profile_used": profile,
        "all_issues": parsed_output,
        "categorized_issues": categorized_issues,
        "summary": {
            "total_issues": len(parsed_output),
            "critical": len(categorized_issues["critical"]),
            "major": len(categorized_issues["major"]),
            "minor": len(categorized_issues["minor"]),
            "info": len(categorized_issues["info"])
        },
        "recommendations": {
            "ready_for_production": len(categorized_issues["critical"]) == 0 and len(categorized_issues["major"]) == 0,
            "next_steps": "Fix critical and major issues before deploying to production" if len(categorized_issues["critical"]) > 0 or len(categorized_issues["major"]) > 0 else "Code meets basic quality standards"
        }
    }

@mcp.tool()
async def analyze_project(project_path: str, profile: str = "moderate") -> Any:
    """
    Analyze an entire Ansible project structure and generate a comprehensive report.
    
    Args:
        project_path: Path to the Ansible project directory
        profile: Quality profile to use for analysis
    """
    if not os.path.exists(project_path):
        return {
            "error": f"Project path not found: {project_path}",
            "success": False
        }
    
    if not os.path.isdir(project_path):
        return {
            "error": f"Path is not a directory: {project_path}",
            "success": False
        }
    
    args = ["--format=json", "--profile", profile, project_path]
    
    result = await run_ansible_lint(args)
    
    if not result["success"]:
        return {
            "error": result.get("error", "Project analysis failed"),
            "stderr": result.get("stderr", ""),
            "success": False
        }
    
    parsed_output = parse_lint_output(result["stdout"], "json")
    
    # Analyze project structure
    project_structure = {}
    
    # Look for common Ansible project files and directories
    common_paths = [
        "playbooks", "roles", "inventory", "group_vars", "host_vars", 
        "ansible.cfg", "requirements.yml", "site.yml"
    ]
    
    for path in common_paths:
        full_path = os.path.join(project_path, path)
        if os.path.exists(full_path):
            if os.path.isdir(full_path):
                project_structure[path] = {
                    "type": "directory",
                    "contents": os.listdir(full_path)
                }
            else:
                project_structure[path] = {
                    "type": "file",
                    "size": os.path.getsize(full_path)
                }
    
    # Categorize issues by file
    issues_by_file = {}
    for issue in parsed_output:
        if isinstance(issue, dict):
            filename = issue.get("filename", "unknown")
            if filename not in issues_by_file:
                issues_by_file[filename] = []
            issues_by_file[filename].append(issue)
    
    return {
        "success": True,
        "project_path": project_path,
        "profile_used": profile,
        "project_structure": project_structure,
        "all_issues": parsed_output,
        "issues_by_file": issues_by_file,
        "summary": {
            "total_issues": len(parsed_output),
            "files_with_issues": len(issues_by_file),
            "most_problematic_files": sorted(
                issues_by_file.items(), 
                key=lambda x: len(x[1]), 
                reverse=True
            )[:5]
        }
    }

@mcp.tool()
async def get_ansible_lint_version() -> Any:
    """Get the version of ansible-lint installed."""
    if not check_ansible_lint_available():
        return {
            "error": "ansible-lint is not installed",
            "success": False
        }
    
    result = await run_ansible_lint(["--version"])
    
    return {
        "success": result["success"],
        "version_info": result["stdout"] if result["success"] else result.get("error", "Unknown error"),
        "available": check_ansible_lint_available()
    }

if __name__ == "__main__":
    mcp.run(transport="stdio")