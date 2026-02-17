/**
 * RBAC (Role-Based Access Control) plugin for OpenClaw v2.
 *
 * Restricts tool access based on sender identity parsed from sessionKey.
 * Config defines roles with user lists, allowed tool lists, and channel scoping.
 * Roles are checked top-to-bottom — first match wins.
 *
 * v2 additions:
 *  - Channel-aware role resolution (different guest roles per channel)
 *  - Fail-safe deny when sessionKey is unparseable
 *  - Audit logging for allowed calls (logAllowed)
 *  - Rate limiting for blocked-call log output
 *  - Tool groups (@group references) and wildcard prefixes (exec_*)
 *  - System command guard (blocks /status, /help etc. for non-admin users)
 */

import type { OpenClawPluginApi } from "openclaw/plugin-sdk";

import { rbacConfigSchema, type RBACConfig } from "./src/config.js";
import { parseSessionKey } from "./src/session-key-parser.js";
import { resolveRole } from "./src/role-resolver.js";
import { checkToolAccess } from "./src/tool-guard.js";
import { RateLimiter } from "./src/rate-limiter.js";
import {
  matchBlockedCommand,
  setPendingBlock,
  consumePendingBlock,
  getBlockResponse,
  isAdminByTools,
} from "./src/command-guard.js";

const rbacPlugin = {
  id: "rbac",
  name: "RBAC (Role-Based Access Control)",
  description:
    "Restrict tool access by user role with channel-aware resolution. " +
    "Checks sender ID from sessionKey against role config. " +
    "Supports tool groups, wildcard prefixes, and per-channel guest roles.",
  configSchema: rbacConfigSchema,

  register(api: OpenClawPluginApi) {
    let config: RBACConfig;
    try {
      config = rbacConfigSchema.parse(api.pluginConfig);
    } catch (err) {
      api.logger.error(`rbac: invalid config: ${String(err)}`);
      return;
    }

    // Log config warnings (e.g. empty tools array, empty channels array)
    for (const warning of config.warnings) {
      api.logger.warn(`rbac: config warning: ${warning}`);
    }

    const roleNames = Object.keys(config.roles);
    api.logger.info(
      `rbac: registered with ${roleNames.length} roles (${roleNames.join(", ")}), default="${config.defaultRole}", failSafe="${config.failSafe}"`,
    );

    // Create rate limiter for blocked-call log output (if configured)
    const rateLimiter = config.rateLimit
      ? new RateLimiter(config.rateLimit.maxBlockedPerMinute)
      : null;

    api.on(
      "before_tool_call",
      async (event, ctx) => {
        // No session context — allow (internal/system call)
        if (!ctx.sessionKey) return;

        const parsed = parseSessionKey(ctx.sessionKey);

        // Can't determine sender — check failSafe policy
        if (!parsed) {
          if (config.failSafe === "deny") {
            api.logger.warn(
              `rbac: BLOCKED tool="${event.toolName}" sessionKey="${ctx.sessionKey}" reason="Unrecognized session key (failSafe=deny)"`,
            );
            return {
              block: true,
              blockReason:
                "Access denied: unrecognized session (RBAC failSafe)",
            };
          }
          // failSafe=allow — let it through
          return;
        }

        const { peerId, channel } = parsed;
        const roleName = resolveRole(peerId, channel, config);
        const result = checkToolAccess(event.toolName, roleName, config);

        if (!result.allowed) {
          if (config.logBlocked) {
            const shouldLog = rateLimiter
              ? rateLimiter.shouldLog(peerId)
              : true;
            if (shouldLog) {
              api.logger.warn(
                `rbac: BLOCKED tool="${event.toolName}" peer="${peerId}" channel="${channel ?? "unknown"}" role="${roleName}" reason="${result.reason}"`,
              );
            } else {
              const suppressed = rateLimiter!.getSuppressed(peerId);
              if (suppressed === 1) {
                api.logger.warn(
                  `rbac: rate limit exceeded for peer="${peerId}", suppressing logs for 60s`,
                );
              }
            }
          }
          return {
            block: true,
            blockReason: result.reason ?? "Access denied by RBAC policy",
          };
        }

        // Audit log for allowed calls
        if (config.logAllowed) {
          api.logger.info(
            `rbac: ALLOWED tool="${event.toolName}" peer="${peerId}" channel="${channel ?? "unknown"}" role="${roleName}"`,
          );
        }
      },
      { priority: 100 },
    );

    // ---------------------------------------------------------------
    // System command guard (message_received + message_sending)
    // ---------------------------------------------------------------
    if (config.systemCommands) {
      const sysCmds = config.systemCommands;
      const blockedCount = sysCmds.blocked.length + (sysCmds.guestHelp ? 1 : 0);
      api.logger.info(
        `rbac: system command guard enabled, ${blockedCount} commands guarded for non-admin users`,
      );

      // Hook 1: Detect blocked commands from non-admins (sync, fire-and-forget).
      // Sets a flag BEFORE the built-in command handler processes the message.
      api.on(
        "message_received",
        (event, ctx) => {
          const content = event.content;
          if (!content || !content.trim().startsWith("/")) return;

          const command = matchBlockedCommand(content, sysCmds);
          if (!command) return;

          // Resolve role from event.from (peerId) and ctx.channelId
          const peerId = event.from;
          const channel = ctx.channelId ?? null;
          if (!peerId) return;

          const roleName = resolveRole(peerId, channel, config);
          if (isAdminByTools(roleName, config.roles)) return;

          // Non-admin sending a blocked command — set flag
          setPendingBlock(command);

          if (config.logBlocked) {
            api.logger.info(
              `rbac: GUARD command="${command}" peer="${peerId}" channel="${channel ?? "unknown"}" role="${roleName}"`,
            );
          }
        },
        { priority: 100 },
      );

      // Hook 2: Replace outgoing response for blocked commands.
      api.on(
        "message_sending",
        (event) => {
          const command = consumePendingBlock();
          if (!command) return;

          const replacement = getBlockResponse(command, sysCmds);
          return { content: replacement };
        },
        { priority: 100 },
      );
    }
  },
};

export default rbacPlugin;
