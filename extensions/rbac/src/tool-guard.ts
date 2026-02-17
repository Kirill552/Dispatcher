/**
 * Check whether a role is allowed to use a specific tool.
 *
 * Supports:
 *  - Exact tool names:  "catalog_search"
 *  - Wildcard prefixes: "exec_*"  (matches exec_shell but NOT exec itself)
 *  - Group references:  "@news_read" (expands via config.toolGroups)
 *
 * Priority: exact match first, then wildcard prefix, then group expansion.
 */

import type { RBACConfig } from "./config.js";

export type ToolGuardResult = {
  allowed: boolean;
  role: string;
  reason?: string;
};

/**
 * Expand a raw tool list into exact names and wildcard patterns.
 *
 * - Plain names go into `exact`.
 * - Entries ending with `_*` go into `wildcards` (kept as-is, e.g. "exec_*").
 * - Entries starting with `@` are looked up in `config.toolGroups` and their
 *   concrete tool names are added to `exact`.
 */
export function expandTools(
  tools: string[],
  config: RBACConfig,
): { exact: string[]; wildcards: string[] } {
  const exact: string[] = [];
  const wildcards: string[] = [];

  for (const entry of tools) {
    if (entry.endsWith("_*")) {
      wildcards.push(entry);
    } else if (entry.startsWith("@")) {
      const groupName = entry.slice(1);
      const groupTools = config.toolGroups[groupName];
      if (groupTools) {
        exact.push(...groupTools);
      }
    } else {
      exact.push(entry);
    }
  }

  return { exact, wildcards };
}

export function checkToolAccess(
  toolName: string,
  roleName: string,
  config: RBACConfig,
): ToolGuardResult {
  const role = config.roles[roleName];
  if (!role) {
    return {
      allowed: false,
      role: roleName,
      reason: `Unknown role "${roleName}"`,
    };
  }

  // Wildcard "*" means all tools allowed.
  if (role.tools === "*") {
    return { allowed: true, role: roleName };
  }

  // Expand the tool list into exact names and wildcard patterns.
  const { exact, wildcards } = expandTools(role.tools, config);

  // 1. Exact match (highest priority).
  if (exact.includes(toolName)) {
    return { allowed: true, role: roleName };
  }

  // 2. Wildcard prefix match.
  //    "exec_*" matches any toolName starting with "exec_" that has at least
  //    one more character after the prefix (i.e. "exec_" alone won't match).
  for (const pattern of wildcards) {
    const prefix = pattern.slice(0, -1); // strip trailing "*", keep the "_"
    if (toolName.startsWith(prefix) && toolName.length > prefix.length) {
      return { allowed: true, role: roleName };
    }
  }

  return {
    allowed: false,
    role: roleName,
    reason: `Role "${roleName}" does not have access to tool "${toolName}"`,
  };
}
