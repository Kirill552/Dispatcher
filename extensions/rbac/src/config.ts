/**
 * RBAC plugin configuration types and validation.
 */

export type RBACRoleConfig = {
  users: string[] | "*";
  tools: string[] | "*";
  channels: string[] | "*";
};

export type RateLimitConfig = {
  maxBlockedPerMinute: number;
  action: "suppress-logs";
};

export type SystemCommandsConfig = {
  mode: "blocklist" | "allowlist";
  blocked: string[];   // blocklist mode: these specific commands are blocked
  allowed: string[];   // allowlist mode: only these /commands pass through for guests
  guestHelp: string | null;
  blockResponse: string;
};

export type RBACConfig = {
  roles: Record<string, RBACRoleConfig>;
  defaultRole: string;
  logBlocked: boolean;
  logAllowed: boolean;
  failSafe: "deny" | "allow";
  toolGroups: Record<string, string[]>;
  rateLimit: RateLimitConfig | null;
  systemCommands: SystemCommandsConfig | null;
  warnings: string[];
};

function assertObject(value: unknown, label: string): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }
  return value as Record<string, unknown>;
}

function parseUsers(value: unknown, roleName: string): string[] | "*" {
  if (value === "*") return "*";
  if (Array.isArray(value) && value.every((v) => typeof v === "string")) {
    return value as string[];
  }
  throw new Error(`roles.${roleName}.users must be "*" or string[]`);
}

function parseTools(value: unknown, roleName: string): string[] | "*" {
  if (value === "*") return "*";
  if (Array.isArray(value) && value.every((v) => typeof v === "string")) {
    return value as string[];
  }
  throw new Error(`roles.${roleName}.tools must be "*" or string[]`);
}

function parseChannels(value: unknown, roleName: string): string[] | "*" {
  if (value === undefined || value === "*") return "*";
  if (Array.isArray(value) && value.every((v) => typeof v === "string")) {
    return value as string[];
  }
  throw new Error(`roles.${roleName}.channels must be "*" or string[]`);
}

function parseToolGroups(value: unknown): Record<string, string[]> {
  if (value === undefined || value === null) return {};
  const obj = assertObject(value, "toolGroups");
  const result: Record<string, string[]> = {};
  for (const [name, tools] of Object.entries(obj)) {
    if (!Array.isArray(tools) || !tools.every((t) => typeof t === "string")) {
      throw new Error(`toolGroups.${name} must be string[]`);
    }
    result[name] = tools as string[];
  }
  return result;
}

function parseRateLimit(value: unknown): RateLimitConfig | null {
  if (value === undefined || value === null) return null;
  const obj = assertObject(value, "rateLimit");
  const max = obj.maxBlockedPerMinute;
  if (typeof max !== "number" || max < 1) {
    throw new Error("rateLimit.maxBlockedPerMinute must be a positive number");
  }
  return { maxBlockedPerMinute: max, action: "suppress-logs" };
}

function normalizeCommands(arr: string[]): string[] {
  return arr.map((cmd) => {
    const c = cmd.toLowerCase().trim();
    return c.startsWith("/") ? c : `/${c}`;
  });
}

function parseSystemCommands(value: unknown): SystemCommandsConfig | null {
  if (value === undefined || value === null) return null;
  const obj = assertObject(value, "systemCommands");

  // Mode: "blocklist" (block specific) or "allowlist" (block all except listed)
  const mode = obj.mode;
  if (mode !== undefined && mode !== "blocklist" && mode !== "allowlist") {
    throw new Error('systemCommands.mode must be "blocklist" or "allowlist"');
  }
  const resolvedMode: "blocklist" | "allowlist" = (mode as "blocklist" | "allowlist") ?? "blocklist";

  // blocked — required for blocklist mode, optional for allowlist
  const blocked = obj.blocked;
  if (blocked !== undefined && blocked !== null) {
    if (!Array.isArray(blocked) || !blocked.every((v) => typeof v === "string")) {
      throw new Error("systemCommands.blocked must be string[]");
    }
  }
  if (resolvedMode === "blocklist" && (!Array.isArray(blocked) || blocked.length === 0)) {
    throw new Error("systemCommands.blocked is required and must be non-empty in blocklist mode");
  }

  // allowed — required for allowlist mode, optional for blocklist
  const allowed = obj.allowed;
  if (allowed !== undefined && allowed !== null) {
    if (!Array.isArray(allowed) || !allowed.every((v) => typeof v === "string")) {
      throw new Error("systemCommands.allowed must be string[]");
    }
  }
  if (resolvedMode === "allowlist" && !Array.isArray(allowed)) {
    throw new Error("systemCommands.allowed is required in allowlist mode");
  }

  const guestHelp = obj.guestHelp;
  if (guestHelp !== undefined && guestHelp !== null && typeof guestHelp !== "string") {
    throw new Error("systemCommands.guestHelp must be a string or null");
  }

  const blockResponse = obj.blockResponse;
  if (typeof blockResponse !== "string") {
    throw new Error("systemCommands.blockResponse must be a string");
  }

  return {
    mode: resolvedMode,
    blocked: Array.isArray(blocked) ? normalizeCommands(blocked as string[]) : [],
    allowed: Array.isArray(allowed) ? normalizeCommands(allowed as string[]) : [],
    guestHelp: (guestHelp as string) ?? null,
    blockResponse,
  };
}

function parseFailSafe(value: unknown): "deny" | "allow" {
  if (value === undefined || value === null) return "deny";
  if (value === "deny" || value === "allow") return value;
  throw new Error(`failSafe must be "deny" or "allow", got "${String(value)}"`);
}

export const rbacConfigSchema = {
  parse(value: unknown): RBACConfig {
    const cfg = assertObject(value, "rbac config");

    const rolesRaw = assertObject(cfg.roles, "rbac config.roles");
    const roles: Record<string, RBACRoleConfig> = {};
    const warnings: string[] = [];

    // Track whether we've seen a wildcard users role to validate ordering.
    let firstWildcardRole: string | null = null;

    for (const [roleName, roleRaw] of Object.entries(rolesRaw)) {
      const role = assertObject(roleRaw, `roles.${roleName}`);
      const users = parseUsers(role.users, roleName);
      const tools = parseTools(role.tools, roleName);
      const channels = parseChannels(role.channels, roleName);

      // Validate wildcard ordering: wildcard users before specific is an error.
      if (users === "*") {
        if (firstWildcardRole === null) {
          firstWildcardRole = roleName;
        }
      } else {
        // Specific users role — if a wildcard already appeared, error.
        if (firstWildcardRole !== null) {
          throw new Error(
            `Role "${firstWildcardRole}" has wildcard users "*" before role "${roleName}" with specific users. ` +
              `Wildcard roles must come after specific roles (first match wins).`,
          );
        }
      }

      // Warn on empty arrays.
      if (Array.isArray(tools) && tools.length === 0) {
        warnings.push(`Role "${roleName}" has empty tools array — it will block all tool access.`);
      }
      if (Array.isArray(channels) && channels.length === 0) {
        warnings.push(`Role "${roleName}" has empty channels array — it will match no channels.`);
      }

      roles[roleName] = { users, tools, channels };
    }

    if (Object.keys(roles).length === 0) {
      throw new Error("rbac config.roles must have at least one role");
    }

    const defaultRole = typeof cfg.defaultRole === "string" ? cfg.defaultRole : "guest";
    if (!roles[defaultRole]) {
      throw new Error(`defaultRole "${defaultRole}" not found in roles`);
    }

    const toolGroups = parseToolGroups(cfg.toolGroups);
    const failSafe = parseFailSafe(cfg.failSafe);
    const rateLimit = parseRateLimit(cfg.rateLimit);
    const systemCommands = parseSystemCommands(cfg.systemCommands);

    // Validate @group references in tool lists against defined toolGroups.
    for (const [roleName, role] of Object.entries(roles)) {
      if (Array.isArray(role.tools)) {
        for (const tool of role.tools) {
          if (tool.startsWith("@")) {
            const groupName = tool.slice(1);
            if (!toolGroups[groupName]) {
              throw new Error(
                `Role "${roleName}" references tool group "${tool}" but no matching entry exists in toolGroups.`,
              );
            }
          }
        }
      }
    }

    return {
      roles,
      defaultRole,
      logBlocked: cfg.logBlocked !== false,
      logAllowed: cfg.logAllowed === true,
      failSafe,
      toolGroups,
      rateLimit,
      systemCommands,
      warnings,
    };
  },
};
