import os
import httpx
import urllib3
from mcp.server.fastmcp import FastMCP
from typing import Any

# Disable SSL warnings for lab environments with self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Environment variables for authentication
AAP_URL = os.getenv("AAP_URL")
AAP_TOKEN = os.getenv("AAP_TOKEN")

if not AAP_TOKEN:
    raise ValueError("AAP_TOKEN is required")

# Headers for API authentication
HEADERS = {"Authorization": f"Bearer {AAP_TOKEN}", "Content-Type": "application/json"}

# Initialize FastMCP
mcp = FastMCP("ansible")


async def make_request(url: str, method: str = "GET", json: dict = None) -> Any:
    """Helper function to make authenticated API requests to AAP."""
    # For lab environments, disable SSL verification for self-signed certificates
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.request(method, url, headers=HEADERS, json=json)
    if response.status_code not in [200, 201]:
        return f"Error {response.status_code}: {response.text}"
    return response.json() if "application/json" in response.headers.get("Content-Type", "") else response.text


@mcp.tool()
async def list_inventories() -> Any:
    """List all inventories in Ansible Automation Platform."""
    return await make_request(f"{AAP_URL}/inventories/")


@mcp.tool()
async def get_inventory(inventory_id: str) -> Any:
    """Get details of a specific inventory by ID."""
    return await make_request(f"{AAP_URL}/inventories/{inventory_id}/")


@mcp.tool()
async def run_job(template_id: int, extra_vars: dict = {}) -> Any:
    """Run a job template by ID, optionally with extra_vars."""
    return await make_request(
        f"{AAP_URL}/job_templates/{template_id}/launch/", method="POST", json={"extra_vars": extra_vars}
    )


@mcp.tool()
async def job_status(job_id: int) -> Any:
    """Check the status of a job by ID."""
    return await make_request(f"{AAP_URL}/jobs/{job_id}/")


@mcp.tool()
async def job_logs(job_id: int) -> str:
    """Retrieve logs for a job."""
    return await make_request(f"{AAP_URL}/jobs/{job_id}/stdout/?format=txt")


@mcp.tool()
async def create_project(
    name: str,
    organization_id: int,
    source_control_url: str,
    source_control_type: str = "git",
    description: str = "",
    execution_environment_id: int = None,
    content_signature_validation_credential_id: int = None,
    source_control_branch: str = "",
    source_control_refspec: str = "",
    source_control_credential_id: int = None,
    clean: bool = False,
    update_revision_on_launch: bool = False,
    delete: bool = False,
    allow_branch_override: bool = False,
    track_submodules: bool = False,
) -> Any:
    """Create a new project in Ansible Automation Platform."""

    payload = {
        "name": name,
        "description": description,
        "organization": organization_id,
        "scm_type": source_control_type.lower(),  # Git is default
        "scm_url": source_control_url,
        "scm_branch": source_control_branch,
        "scm_refspec": source_control_refspec,
        "scm_clean": clean,
        "scm_delete_on_update": delete,
        "scm_update_on_launch": update_revision_on_launch,
        "allow_override": allow_branch_override,
        "scm_track_submodules": track_submodules,
    }

    if execution_environment_id:
        payload["execution_environment"] = execution_environment_id
    if content_signature_validation_credential_id:
        payload["signature_validation_credential"] = content_signature_validation_credential_id
    if source_control_credential_id:
        payload["credential"] = source_control_credential_id

    return await make_request(f"{AAP_URL}/projects/", method="POST", json=payload)


@mcp.tool()
async def create_job_template(
    name: str,
    project_id: int,
    playbook: str,
    inventory_id: int,
    job_type: str = "run",
    description: str = "",
    credential_id: int = None,
    execution_environment_id: int = None,
    labels: list[str] = None,
    forks: int = 0,
    limit: str = "",
    verbosity: int = 0,
    timeout: int = 0,
    job_tags: list[str] = None,
    skip_tags: list[str] = None,
    extra_vars: dict = None,
    privilege_escalation: bool = False,
    concurrent_jobs: bool = False,
    provisioning_callback: bool = False,
    enable_webhook: bool = False,
    prevent_instance_group_fallback: bool = False,
) -> Any:
    """Create a new job template in Ansible Automation Platform."""

    payload = {
        "name": name,
        "description": description,
        "job_type": job_type,
        "project": project_id,
        "playbook": playbook,
        "inventory": inventory_id,
        "forks": forks,
        "limit": limit,
        "verbosity": verbosity,
        "timeout": timeout,
        "ask_variables_on_launch": bool(extra_vars),
        "ask_tags_on_launch": bool(job_tags),
        "ask_skip_tags_on_launch": bool(skip_tags),
        "ask_credential_on_launch": credential_id is None,
        "ask_execution_environment_on_launch": execution_environment_id is None,
        "ask_labels_on_launch": labels is None,
        "ask_inventory_on_launch": False,  # Inventory is required, so not prompting
        "ask_job_type_on_launch": False,  # Job type is required, so not prompting
        "become_enabled": privilege_escalation,
        "allow_simultaneous": concurrent_jobs,
        "scm_branch": "",
        "webhook_service": "github" if enable_webhook else "",
        "prevent_instance_group_fallback": prevent_instance_group_fallback,
    }

    if credential_id:
        payload["credential"] = credential_id
    if execution_environment_id:
        payload["execution_environment"] = execution_environment_id
    if labels:
        payload["labels"] = labels
    if job_tags:
        payload["job_tags"] = job_tags
    if skip_tags:
        payload["skip_tags"] = skip_tags
    if extra_vars:
        payload["extra_vars"] = extra_vars

    return await make_request(f"{AAP_URL}/job_templates/", method="POST", json=payload)


@mcp.tool()
async def list_inventory_sources() -> Any:
    """List all inventory sources in Ansible Automation Platform."""
    return await make_request(f"{AAP_URL}/inventory_sources/")


@mcp.tool()
async def get_inventory_source(inventory_source_id: int) -> Any:
    """Get details of a specific inventory source."""
    return await make_request(f"{AAP_URL}/inventory_sources/{inventory_source_id}/")


@mcp.tool()
async def create_inventory_source(
    name: str,
    inventory_id: int,
    source: str,
    credential_id: int,
    source_vars: dict = None,
    update_on_launch: bool = True,
    timeout: int = 0,
) -> Any:
    """Create a dynamic inventory source. Claude will ask for the source type and credential before proceeding."""
    valid_sources = [
        "file",
        "constructed",
        "scm",
        "ec2",
        "gce",
        "azure_rm",
        "vmware",
        "satellite6",
        "openstack",
        "rhv",
        "controller",
        "insights",
        "terraform",
        "openshift_virtualization",
    ]

    if source not in valid_sources:
        return f"Error: Invalid source type '{source}'. Please select from: {', '.join(valid_sources)}"

    if not credential_id:
        return "Error: Credential is required to create an inventory source."

    payload = {
        "name": name,
        "inventory": inventory_id,
        "source": source,
        "credential": credential_id,
        "source_vars": source_vars,
        "update_on_launch": update_on_launch,
        "timeout": timeout,
    }
    return await make_request(f"{AAP_URL}/inventory_sources/", method="POST", json=payload)


@mcp.tool()
async def update_inventory_source(inventory_source_id: int, update_data: dict) -> Any:
    """Update an existing inventory source."""
    return await make_request(f"{AAP_URL}/inventory_sources/{inventory_source_id}/", method="PATCH", json=update_data)


@mcp.tool()
async def delete_inventory_source(inventory_source_id: int) -> Any:
    """Delete an inventory source."""
    return await make_request(f"{AAP_URL}/inventory_sources/{inventory_source_id}/", method="DELETE")


@mcp.tool()
async def sync_inventory_source(inventory_source_id: int) -> Any:
    """Manually trigger a sync for an inventory source."""
    return await make_request(f"{AAP_URL}/inventory_sources/{inventory_source_id}/update/", method="POST")


@mcp.tool()
async def create_inventory(
    name: str,
    organization_id: int,
    description: str = "",
    kind: str = "",
    host_filter: str = "",
    variables: dict = None,
    prevent_instance_group_fallback: bool = False,
) -> Any:
    """Create an inventory in Ansible Automation Platform."""
    payload = {
        "name": name,
        "organization": organization_id,
        "description": description,
        "kind": kind,
        "host_filter": host_filter,
        "variables": variables,
        "prevent_instance_group_fallback": prevent_instance_group_fallback,
    }
    return await make_request(f"{AAP_URL}/inventories/", method="POST", json=payload)


@mcp.tool()
async def delete_inventory(inventory_id: int) -> Any:
    """Delete an inventory from Ansible Automation Platform."""
    return await make_request(f"{AAP_URL}/inventories/{inventory_id}/", method="DELETE")


@mcp.tool()
async def list_job_templates() -> Any:
    """List all job templates available in Ansible Automation Platform."""
    return await make_request(f"{AAP_URL}/job_templates/")


@mcp.tool()
async def get_job_template(template_id: int) -> Any:
    """Retrieve details of a specific job template."""
    return await make_request(f"{AAP_URL}/job_templates/{template_id}/")


@mcp.tool()
async def list_jobs() -> Any:
    """List all jobs available in Ansible Automation Platform."""
    return await make_request(f"{AAP_URL}/jobs/")


@mcp.tool()
async def list_recent_jobs(hours: int = 24) -> Any:
    """List all jobs executed in the last specified hours (default 24 hours)."""
    from datetime import datetime, timedelta

    time_filter = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"
    return await make_request(f"{AAP_URL}/jobs/?created__gte={time_filter}")


# Host Management Tools
@mcp.tool()
async def list_hosts(inventory_id: int) -> Any:
    """List all hosts in a specific inventory."""
    return await make_request(f"{AAP_URL}/inventories/{inventory_id}/hosts/")


@mcp.tool()
async def get_host_details(host_id: int) -> Any:
    """Get detailed information about a specific host including facts and variables."""
    return await make_request(f"{AAP_URL}/hosts/{host_id}/")


@mcp.tool()
async def get_host_facts(host_id: int) -> Any:
    """Get gathered facts for a specific host."""
    return await make_request(f"{AAP_URL}/hosts/{host_id}/ansible_facts/")


@mcp.tool()
async def add_host_to_inventory(
    inventory_id: int, hostname: str, description: str = "", variables: dict = None, enabled: bool = True
) -> Any:
    """Add a new host to an inventory with optional variables."""
    payload = {
        "name": hostname,
        "description": description,
        "inventory": inventory_id,
        "enabled": enabled,
        "variables": variables or {},
    }
    return await make_request(f"{AAP_URL}/hosts/", method="POST", json=payload)


@mcp.tool()
async def update_host(host_id: int, update_data: dict) -> Any:
    """Update host settings including variables, description, or enabled status."""
    return await make_request(f"{AAP_URL}/hosts/{host_id}/", method="PATCH", json=update_data)


@mcp.tool()
async def delete_host(host_id: int) -> Any:
    """Delete a host from inventory."""
    return await make_request(f"{AAP_URL}/hosts/{host_id}/", method="DELETE")


@mcp.tool()
async def get_failed_hosts(inventory_id: int) -> Any:
    """Get list of hosts with active failures in an inventory."""
    return await make_request(f"{AAP_URL}/inventories/{inventory_id}/hosts/?has_active_failures=true")


@mcp.tool()
async def list_groups(inventory_id: int) -> Any:
    """List all groups in a specific inventory."""
    return await make_request(f"{AAP_URL}/inventories/{inventory_id}/groups/")


@mcp.tool()
async def get_group_details(group_id: int) -> Any:
    """Get detailed information about a specific group."""
    return await make_request(f"{AAP_URL}/groups/{group_id}/")


@mcp.tool()
async def create_group(inventory_id: int, name: str, description: str = "", variables: dict = None) -> Any:
    """Create a new group in an inventory."""
    payload = {"name": name, "description": description, "inventory": inventory_id, "variables": variables or {}}
    return await make_request(f"{AAP_URL}/groups/", method="POST", json=payload)


@mcp.tool()
async def add_host_to_group(group_id: int, host_id: int) -> Any:
    """Add a host to a group."""
    payload = {"id": host_id}
    return await make_request(f"{AAP_URL}/groups/{group_id}/hosts/", method="POST", json=payload)


@mcp.tool()
async def remove_host_from_group(group_id: int, host_id: int) -> Any:
    """Remove a host from a group."""
    return await make_request(
        f"{AAP_URL}/groups/{group_id}/hosts/", method="POST", json={"id": host_id, "disassociate": True}
    )


@mcp.tool()
async def get_host_groups(host_id: int) -> Any:
    """Get all groups that a host belongs to."""
    return await make_request(f"{AAP_URL}/hosts/{host_id}/groups/")


@mcp.tool()
async def run_adhoc_command(
    inventory_id: int,
    module_name: str,
    module_args: str = "",
    limit: str = "",
    credential_id: int = None,
    become_enabled: bool = False,
    verbosity: int = 0,
) -> Any:
    """Run an ad-hoc Ansible command against inventory hosts."""
    payload = {
        "inventory": inventory_id,
        "module_name": module_name,
        "module_args": module_args,
        "limit": limit,
        "become_enabled": become_enabled,
        "verbosity": verbosity,
    }
    if credential_id:
        payload["credential"] = credential_id

    return await make_request(f"{AAP_URL}/ad_hoc_commands/", method="POST", json=payload)


@mcp.tool()
async def get_adhoc_command_status(adhoc_id: int) -> Any:
    """Get status of an ad-hoc command."""
    return await make_request(f"{AAP_URL}/ad_hoc_commands/{adhoc_id}/")


@mcp.tool()
async def get_adhoc_command_output(adhoc_id: int) -> Any:
    """Get output/logs from an ad-hoc command."""
    return await make_request(f"{AAP_URL}/ad_hoc_commands/{adhoc_id}/stdout/?format=txt")


# Project Management Tools
@mcp.tool()
async def list_projects() -> Any:
    """List all projects in Ansible Automation Platform."""
    return await make_request(f"{AAP_URL}/projects/")


@mcp.tool()
async def get_project(project_id: int) -> Any:
    """Get details of a specific project by ID."""
    return await make_request(f"{AAP_URL}/projects/{project_id}/")


@mcp.tool()
async def list_project_updates() -> Any:
    """List all project update jobs (SCM sync operations)."""
    return await make_request(f"{AAP_URL}/project_updates/")


@mcp.tool()
async def get_project_update(update_id: int) -> Any:
    """Get status and details of a specific project update job."""
    return await make_request(f"{AAP_URL}/project_updates/{update_id}/")


@mcp.tool()
async def get_project_update_logs(update_id: int) -> str:
    """Get logs from a project update job (SCM sync operation)."""
    return await make_request(f"{AAP_URL}/project_updates/{update_id}/stdout/?format=txt")


@mcp.tool()
async def update_project(project_id: int) -> Any:
    """Trigger a project update (SCM sync) for a specific project."""
    return await make_request(f"{AAP_URL}/projects/{project_id}/update/", method="POST")


# Galaxy API Helper Functions
async def search_galaxy_api(endpoint: str, params: dict = None) -> Any:
    """Helper function to make requests to Ansible Galaxy API."""
    base_url = "https://galaxy.ansible.com"
    url = f"{base_url}{endpoint}"

    timeout = httpx.Timeout(60.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)

        if response.status_code != 200:
            return f"Galaxy API Error {response.status_code}: {response.text}"

        return response.json()
    except httpx.TimeoutException:
        return "Galaxy API timeout - service may be slow"
    except httpx.RequestError as e:
        return f"Galaxy API request error: {str(e)}"
    except Exception as e:
        return f"Galaxy API unexpected error: {str(e)}"


def analyze_use_case(description: str) -> dict:
    """Extract keywords and context from use case description."""
    description_lower = description.lower()

    # Cloud providers
    cloud_keywords = {
        "aws": ["aws", "ec2", "amazon", "s3", "lambda", "cloudformation"],
        "azure": ["azure", "microsoft", "vm", "resource group"],
        "gcp": ["gcp", "google cloud", "compute engine", "gke"],
        "openstack": ["openstack", "nova", "neutron"],
    }

    # Infrastructure components
    infra_keywords = {
        "web": ["web", "apache", "nginx", "http", "https"],
        "database": ["database", "db", "mysql", "postgresql", "postgres", "mongodb"],
        "container": ["docker", "kubernetes", "k8s", "container", "pod"],
        "network": ["network", "firewall", "vpc", "subnet", "security group"],
        "monitoring": ["monitoring", "metrics", "logging", "prometheus", "grafana"],
        "security": ["security", "ssl", "tls", "certificate", "vault"],
    }

    detected_categories = []
    all_keywords = []

    # Check cloud providers
    for provider, keywords in cloud_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            detected_categories.append(provider)
            all_keywords.extend(keywords)

    # Check infrastructure components
    for component, keywords in infra_keywords.items():
        if any(keyword in description_lower for keyword in keywords):
            detected_categories.append(component)
            all_keywords.extend(keywords)

    # Extract specific action keywords
    action_keywords = []
    actions = ["deploy", "install", "configure", "manage", "create", "delete", "start", "stop", "scale"]
    for action in actions:
        if action in description_lower:
            action_keywords.append(action)

    return {
        "categories": detected_categories,
        "keywords": list(set(all_keywords)),
        "actions": action_keywords,
        "original_description": description,
    }


def rank_content_relevance(content_list: list, keywords: list, content_type: str = "collection") -> list:
    """Score and sort content based on relevance to keywords."""
    scored_content = []

    for item in content_list:
        score = 0

        # Get relevant text fields based on content type
        if content_type == "collection":
            searchable_text = f"{item.get('namespace', '')} {item.get('name', '')}".lower()
        else:  # role
            searchable_text = f"{item.get('name', '')} {item.get('description', '')} {' '.join(item.get('summary_fields', {}).get('tags', []))}".lower()

        # Score based on keyword matches
        for keyword in keywords:
            if keyword.lower() in searchable_text:
                score += 2

        # Bonus for download count (popularity)
        download_count = item.get("download_count", 0)
        if download_count > 1000:
            score += 3
        elif download_count > 100:
            score += 1

        # Bonus for recent updates (for collections)
        if content_type == "collection" and not item.get("deprecated", False):
            score += 1

        scored_content.append({"item": item, "relevance_score": score})

    # Sort by relevance score (highest first)
    scored_content.sort(key=lambda x: x["relevance_score"], reverse=True)
    return [item["item"] for item in scored_content]


# Galaxy Search MCP Tools
@mcp.tool()
async def search_galaxy_collections(query: str, tags: str = None, namespace: str = None, limit: int = 20) -> Any:
    """Search Ansible Galaxy collections by query terms, tags, or namespace."""
    # Since Galaxy v3 API doesn't support direct search, we need to fetch more data to find matches
    max_fetch = min(500, limit * 20)  # Fetch significantly more to increase chance of finding matches
    params = {"limit": max_fetch}

    collections_data = await search_galaxy_api("/api/v3/plugin/ansible/content/published/collections/index/", params)

    if isinstance(collections_data, str):  # Error occurred
        return collections_data

    collections = collections_data.get("data", [])

    # Filter collections based on query
    filtered_collections = []
    query_lower = query.lower()

    for collection in collections:
        collection_text = f"{collection.get('namespace', '')} {collection.get('name', '')}".lower()

        # Check if query matches namespace or name
        matches_query = query_lower in collection_text
        
        # Additional filtering by namespace if specified
        matches_namespace = True
        if namespace:
            matches_namespace = collection.get("namespace", "").lower() == namespace.lower()
        
        if matches_query and matches_namespace:
            filtered_collections.append(collection)

        if len(filtered_collections) >= limit:
            break

    # Format response
    results = []
    for collection in filtered_collections[:limit]:
        results.append(
            {
                "namespace": collection.get("namespace"),
                "name": collection.get("name"),
                "download_count": collection.get("download_count", 0),
                "latest_version": collection.get("highest_version", {}).get("version"),
                "deprecated": collection.get("deprecated", False),
                "created_at": collection.get("created_at"),
                "updated_at": collection.get("updated_at"),
                "install_command": f"ansible-galaxy collection install {collection.get('namespace')}.{collection.get('name')}",
                "galaxy_url": f"https://galaxy.ansible.com/{collection.get('namespace')}/{collection.get('name')}",
            }
        )

    return {"query": query, "total_found": len(results), "collections": results}


@mcp.tool()
async def search_galaxy_roles(keyword: str = None, name: str = None, author: str = None, limit: int = 20) -> Any:
    """Search Ansible Galaxy roles by keyword, name, or author."""
    # Since Galaxy roles API has limited server-side filtering, we fetch more results for client-side filtering
    fetch_size = min(500, limit * 20) if keyword or name else limit
    params = {"page_size": fetch_size}

    if author:
        params["github_user"] = author  # Use 'github_user' for author filtering

    roles_data = await search_galaxy_api("/api/v1/roles/", params)

    if isinstance(roles_data, str):  # Error occurred
        return roles_data

    roles = roles_data.get("results", [])

    # Client-side filtering for keyword and name
    filtered_roles = []
    for role in roles:
        matches = True
        
        # Filter by keyword
        if keyword:
            keyword_lower = keyword.lower()
            searchable_text = f"{role.get('name', '')} {role.get('description', '')} {' '.join(role.get('summary_fields', {}).get('tags', []))}".lower()
            matches = matches and keyword_lower in searchable_text
        
        # Filter by name
        if name:
            name_lower = name.lower()
            role_name_lower = role.get('name', '').lower()
            matches = matches and name_lower in role_name_lower
        
        if matches:
            filtered_roles.append(role)
            
        if len(filtered_roles) >= limit:
            break

    # Format response
    results = []
    for role in filtered_roles[:limit]:
        github_user = role.get("github_user", "")
        role_name = role.get("name", "")

        results.append(
            {
                "id": role.get("id"),
                "name": role_name,
                "author": github_user,
                "description": role.get("description", ""),
                "download_count": role.get("download_count", 0),
                "stargazers_count": role.get("stargazers_count", 0),
                "github_repo": role.get("github_repo", ""),
                "github_branch": role.get("github_branch", ""),
                "tags": role.get("summary_fields", {}).get("tags", []),
                "install_command": f"ansible-galaxy role install {github_user}.{role_name}",
                "galaxy_url": f"https://galaxy.ansible.com/{github_user}/{role_name}",
            }
        )

    return {
        "search_params": {"keyword": keyword, "name": name, "author": author},
        "total_found": len(results),
        "roles": results,
    }


@mcp.tool()
async def get_collection_details(namespace: str, name: str) -> Any:
    """Get detailed information about a specific Ansible Galaxy collection."""
    collection_data = await search_galaxy_api(
        f"/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/"
    )

    if isinstance(collection_data, str):  # Error occurred
        return collection_data

    # Get versions information
    versions_data = await search_galaxy_api(
        f"/api/v3/plugin/ansible/content/published/collections/index/{namespace}/{name}/versions/"
    )

    versions = []
    if isinstance(versions_data, dict) and "data" in versions_data:
        for version in versions_data["data"]:
            versions.append({"version": version.get("version"), "created_at": version.get("created_at")})

    return {
        "namespace": collection_data.get("namespace"),
        "name": collection_data.get("name"),
        "download_count": collection_data.get("download_count", 0),
        "deprecated": collection_data.get("deprecated", False),
        "created_at": collection_data.get("created_at"),
        "updated_at": collection_data.get("updated_at"),
        "latest_version": collection_data.get("highest_version", {}).get("version"),
        "versions": versions,
        "install_command": f"ansible-galaxy collection install {namespace}.{name}",
        "galaxy_url": f"https://galaxy.ansible.com/{namespace}/{name}",
    }


@mcp.tool()
async def get_role_details(role_id: int) -> Any:
    """Get detailed information about a specific Ansible Galaxy role."""
    role_data = await search_galaxy_api(f"/api/v1/roles/{role_id}/")

    if isinstance(role_data, str):  # Error occurred
        return role_data

    github_user = role_data.get("github_user", "")
    role_name = role_data.get("name", "")

    return {
        "id": role_data.get("id"),
        "name": role_name,
        "author": github_user,
        "description": role_data.get("description", ""),
        "download_count": role_data.get("download_count", 0),
        "stargazers_count": role_data.get("stargazers_count", 0),
        "watchers_count": role_data.get("watchers_count", 0),
        "forks_count": role_data.get("forks_count", 0),
        "github_repo": role_data.get("github_repo", ""),
        "github_branch": role_data.get("github_branch", ""),
        "issue_tracker_url": role_data.get("issue_tracker_url", ""),
        "license": role_data.get("license", ""),
        "min_ansible_version": role_data.get("min_ansible_version", ""),
        "tags": role_data.get("summary_fields", {}).get("tags", []),
        "platforms": role_data.get("summary_fields", {}).get("platforms", []),
        "dependencies": role_data.get("summary_fields", {}).get("dependencies", []),
        "install_command": f"ansible-galaxy role install {github_user}.{role_name}",
        "galaxy_url": f"https://galaxy.ansible.com/{github_user}/{role_name}",
    }


@mcp.tool()
async def suggest_ansible_content(use_case: str, check_aap_inventory: bool = True) -> Any:
    """Intelligently suggest Ansible collections and roles based on use case description."""

    # Analyze the use case to extract keywords and context
    analysis = analyze_use_case(use_case)

    suggestions = {
        "use_case_analysis": analysis,
        "aap_context": {},
        "recommended_collections": [],
        "recommended_roles": [],
        "playbook_suggestions": [],
    }

    # Check AAP environment if requested
    if check_aap_inventory and AAP_URL and AAP_TOKEN:
        try:
            # Get existing inventories to understand current infrastructure
            inventories = await make_request(f"{AAP_URL}/inventories/")
            if isinstance(inventories, dict) and "results" in inventories:
                suggestions["aap_context"] = {
                    "existing_inventories": len(inventories["results"]),
                    "inventory_names": [inv.get("name", "") for inv in inventories["results"][:5]],
                }
        except:
            suggestions["aap_context"] = {"note": "Could not check AAP inventory"}

    # Search for relevant collections
    collection_searches = []
    for category in analysis["categories"]:
        collection_searches.append(category)

    # Add specific searches based on detected categories
    if "aws" in analysis["categories"]:
        collection_searches.extend(["amazon.aws", "community.aws"])
    if "azure" in analysis["categories"]:
        collection_searches.append("azure.azcollection")
    if "gcp" in analysis["categories"]:
        collection_searches.append("google.cloud")
    if "container" in analysis["categories"]:
        collection_searches.extend(["community.docker", "kubernetes.core"])

    # Search for collections
    for search_term in collection_searches[:3]:  # Limit API calls
        try:
            collections = await search_galaxy_collections(search_term, limit=5)
            if isinstance(collections, dict) and "collections" in collections:
                # Rank by relevance
                relevant_collections = rank_content_relevance(
                    collections["collections"], analysis["keywords"], "collection"
                )
                suggestions["recommended_collections"].extend(relevant_collections[:2])
        except:
            continue

    # Search for relevant roles
    role_searches = analysis["keywords"][:3]  # Limit searches
    for keyword in role_searches:
        try:
            roles = await search_galaxy_roles(keyword=keyword, limit=5)
            if isinstance(roles, dict) and "roles" in roles:
                # Rank by relevance
                relevant_roles = rank_content_relevance(roles["roles"], analysis["keywords"], "role")
                suggestions["recommended_roles"].extend(relevant_roles[:2])
        except:
            continue

    # Remove duplicates and limit results
    seen_collections = set()
    unique_collections = []
    for collection in suggestions["recommended_collections"]:
        collection_id = f"{collection.get('namespace')}.{collection.get('name')}"
        if collection_id not in seen_collections:
            seen_collections.add(collection_id)
            unique_collections.append(collection)
    suggestions["recommended_collections"] = unique_collections[:5]

    seen_roles = set()
    unique_roles = []
    for role in suggestions["recommended_roles"]:
        role_id = f"{role.get('author')}.{role.get('name')}"
        if role_id not in seen_roles:
            seen_roles.add(role_id)
            unique_roles.append(role)
    suggestions["recommended_roles"] = unique_roles[:5]

    # Generate playbook suggestions based on analysis
    playbook_suggestions = []

    if "aws" in analysis["categories"] and "ec2" in analysis["keywords"]:
        playbook_suggestions.append(
            {
                "title": "EC2 Instance Management",
                "description": "Create, start, stop, and terminate EC2 instances",
                "required_collections": ["amazon.aws"],
                "key_modules": ["amazon.aws.ec2_instance", "amazon.aws.ec2_security_group"],
                "example_tasks": [
                    "Create security group for EC2 instances",
                    "Launch EC2 instances with specified configuration",
                    "Configure instance tags and metadata",
                    "Manage instance state (start/stop/terminate)",
                ],
            }
        )

    if "database" in analysis["categories"]:
        playbook_suggestions.append(
            {
                "title": "Database Server Setup",
                "description": "Install and configure database servers",
                "required_collections": ["community.mysql", "community.postgresql"],
                "key_modules": ["mysql_user", "mysql_db", "postgresql_user", "postgresql_db"],
                "example_tasks": [
                    "Install database server packages",
                    "Configure database server settings",
                    "Create databases and users",
                    "Set up backup procedures",
                ],
            }
        )

    if "web" in analysis["categories"]:
        playbook_suggestions.append(
            {
                "title": "Web Server Configuration",
                "description": "Setup and configure web servers",
                "required_collections": ["community.general"],
                "key_modules": ["apache2_module", "nginx", "systemd"],
                "example_tasks": [
                    "Install web server packages",
                    "Configure virtual hosts",
                    "Manage SSL certificates",
                    "Setup load balancing",
                ],
            }
        )

    suggestions["playbook_suggestions"] = playbook_suggestions

    return suggestions


if __name__ == "__main__":
    mcp.run(transport="stdio")
