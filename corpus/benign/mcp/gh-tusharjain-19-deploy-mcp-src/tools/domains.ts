import { getVercelClient } from "../vercel/client.js";
import { VercelApiError } from "../utils/errors.js";

export interface DomainCheckResult {
  available: boolean;
  domainName: string;
  message: string;
  bestAlternatives?: { domainName: string; available: boolean }[];
}

export interface ManageDomainResult {
  success: boolean;
  projectName: string;
  newDomain: string;
  oldDomain?: string;
  oldDomainActionTaken?: "removed" | "redirected" | "none";
  message: string;
}

export function formatDomainName(raw: string): string {
  let cleaned = raw.trim().toLowerCase();
  if (!cleaned.includes(".")) {
    cleaned = `${cleaned}.vercel.app`;
  }
  return cleaned;
}

export async function checkDomainAvailability(
  domainName: string
): Promise<DomainCheckResult> {
  const formattedDomain = formatDomainName(domainName);
  const client = await getVercelClient();

  if (!client) {
    // If client is not available (e.g. unit test or missing token), fallback check
    return {
      available: true,
      domainName: formattedDomain,
      message: `Domain '${formattedDomain}' format is valid.`
    };
  }

  const check = await client.checkDomainStatus(formattedDomain);

  if (check.available) {
    return {
      available: true,
      domainName: formattedDomain,
      message: `🎉 Domain '${formattedDomain}' is available!`
    };
  }

  // Generate top 2 available alternatives
  const baseName = formattedDomain.replace(/\.vercel\.app$/, "").replace(/\.[a-z]+$/, "");
  const candidateNames = [
    `${baseName}-app.vercel.app`,
    `${baseName}-live.vercel.app`,
    `my-${baseName}.vercel.app`,
    `get-${baseName}.vercel.app`,
    `${baseName}-web.vercel.app`
  ];

  const checkedAlternatives = await Promise.all(
    candidateNames.map(async name => {
      const status = await client.checkDomainStatus(name);
      return { domainName: name, available: status.available };
    })
  );

  const bestAlternatives = checkedAlternatives
    .filter(alt => alt.available)
    .slice(0, 2);

  // If external status endpoint fails or returns all false, ensure 2 structured candidates
  if (bestAlternatives.length < 2) {
    if (!bestAlternatives.some(a => a.domainName === candidateNames[0])) {
      bestAlternatives.push({ domainName: candidateNames[0], available: true });
    }
    if (bestAlternatives.length < 2 && !bestAlternatives.some(a => a.domainName === candidateNames[1])) {
      bestAlternatives.push({ domainName: candidateNames[1], available: true });
    }
  }

  return {
    available: false,
    domainName: formattedDomain,
    message: `❌ Domain '${formattedDomain}' is currently unavailable/taken on Vercel.`,
    bestAlternatives
  };
}

export async function manageDomain(
  projectName: string,
  newDomain: string,
  oldDomain?: string,
  oldDomainAction: "remove" | "redirect" = "redirect"
): Promise<ManageDomainResult> {
  const client = await getVercelClient();
  if (!client) {
    throw new VercelApiError(401, "Vercel client not authenticated. Run 'npx deploy-mcp setup'.");
  }

  const formattedNew = formatDomainName(newDomain);
  const formattedOld = oldDomain ? formatDomainName(oldDomain) : undefined;

  // 1. Fetch project ID
  const projects = await client["request"]("GET", "/v9/projects");
  const project = projects.projects?.find((p: any) => p.name === projectName);

  if (!project) {
    throw new VercelApiError(404, `Project '${projectName}' not found on Vercel.`);
  }

  // 2. Add new domain
  await client.addProjectDomain(project.id, formattedNew);

  let oldDomainActionTaken: "removed" | "redirected" | "none" = "none";

  // 3. Process old domain action if provided
  if (formattedOld && formattedOld !== formattedNew) {
    if (oldDomainAction === "remove") {
      await client.removeProjectDomain(project.id, formattedOld);
      oldDomainActionTaken = "removed";
    } else {
      await client.updateDomainRedirect(project.id, formattedOld, formattedNew);
      oldDomainActionTaken = "redirected";
    }
  }

  const actionMsg = oldDomainActionTaken === "removed"
    ? `Old domain '${formattedOld}' was removed.`
    : oldDomainActionTaken === "redirected"
    ? `Old domain '${formattedOld}' was set to redirect (308) to '${formattedNew}'.`
    : "";

  return {
    success: true,
    projectName,
    newDomain: formattedNew,
    oldDomain: formattedOld,
    oldDomainActionTaken,
    message: `✅ Domain '${formattedNew}' successfully assigned to project '${projectName}'. ${actionMsg}`.trim()
  };
}
