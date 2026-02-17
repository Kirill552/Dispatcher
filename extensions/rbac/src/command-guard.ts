/**
 * System command guard for non-admin users.
 *
 * Uses two hooks:
 * - message_received (sync, fire-and-forget): detects blocked commands, sets flag
 * - message_sending (sequential, can modify): checks flag, replaces response
 *
 * Safe because OpenClaw is single-instance with sequential message processing.
 * The sync handler in message_received sets the flag before command processing starts.
 */

import type { SystemCommandsConfig } from "./config.js";

type PendingBlock = {
  command: string;
  timestamp: number;
};

// Single pending block — safe because OpenClaw processes messages sequentially.
let pendingBlock: PendingBlock | null = null;

// Stale threshold: auto-clear flags older than 10 seconds (safety net).
const STALE_MS = 10_000;

/**
 * Extract the /command name from a message (lowercase, without args).
 * Returns null if the message is not a /command.
 */
function extractCommand(trimmed: string): string | null {
  if (!trimmed.startsWith("/")) return null;
  const spaceIdx = trimmed.indexOf(" ");
  return spaceIdx === -1 ? trimmed : trimmed.slice(0, spaceIdx);
}

/**
 * Check if an incoming message is a system command that should be blocked.
 * Returns the matched command (lowercase with /) or null.
 *
 * Two modes:
 * - "blocklist": block only commands in config.blocked
 * - "allowlist": block ALL /commands EXCEPT those in config.allowed
 */
export function matchBlockedCommand(
  content: string,
  config: SystemCommandsConfig,
): string | null {
  const trimmed = content.trim().toLowerCase();
  const command = extractCommand(trimmed);
  if (!command) return null;

  // /help interception (both modes): when guestHelp is configured, intercept /help
  // to show custom help instead of OpenClaw's built-in help
  if (config.guestHelp !== null && command === "/help") {
    return "/help";
  }

  if (config.mode === "allowlist") {
    // Allowlist: block everything NOT in allowed list
    if (config.allowed.includes(command)) return null;
    return command;
  }

  // Blocklist: block only commands in blocked list
  if (config.blocked.includes(command)) return command;
  return null;
}

/**
 * Set a pending block flag. Called from message_received hook (sync).
 */
export function setPendingBlock(command: string): void {
  pendingBlock = { command, timestamp: Date.now() };
}

/**
 * Consume the pending block flag. Returns the blocked command or null.
 * Auto-clears stale flags as a safety net.
 */
export function consumePendingBlock(): string | null {
  if (!pendingBlock) return null;

  const block = pendingBlock;
  pendingBlock = null;

  // Discard stale flags (shouldn't happen in normal flow)
  if (Date.now() - block.timestamp > STALE_MS) {
    return null;
  }

  return block.command;
}

/**
 * Get the appropriate response for a blocked command.
 */
export function getBlockResponse(
  command: string,
  config: SystemCommandsConfig,
): string {
  if (command === "/help" && config.guestHelp !== null) {
    return config.guestHelp;
  }
  return config.blockResponse;
}

/**
 * Check if a user is an admin based on their peer ID.
 * Admins = users with tools: "*" in any role.
 * Simpler: check if peerId is in any role that has non-wildcard users list.
 * If peerId is in a specific-users role, they're "known". If that role has tools: "*", admin.
 *
 * Actually, simplest: resolve role and check if tools === "*".
 */
export function isAdminByTools(
  roleName: string,
  roles: Record<string, { tools: string[] | "*" }>,
): boolean {
  const role = roles[roleName];
  return role?.tools === "*";
}
