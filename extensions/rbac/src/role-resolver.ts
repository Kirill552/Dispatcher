/**
 * Resolve a peerId + channel to a role name based on RBAC config.
 * Roles are checked in insertion order. First match wins.
 *
 * Match criteria (both must hold):
 *   1. users  — peerId is in the list OR users is "*"
 *   2. channels — channel is in the list OR channels is "*"
 *              — when channel is null, only channels: "*" matches
 */

import type { RBACConfig } from "./config.js";

export function resolveRole(
  peerId: string,
  channel: string | null,
  config: RBACConfig,
): string {
  for (const [roleName, role] of Object.entries(config.roles)) {
    // --- users match ---
    const usersMatch =
      role.users === "*" || role.users.includes(peerId);
    if (!usersMatch) continue;

    // --- channels match ---
    let channelsMatch: boolean;
    if (role.channels === "*") {
      // Wildcard channels always match, even when channel is null
      channelsMatch = true;
    } else if (channel === null) {
      // null channel only matches wildcard (handled above) — not specific arrays
      channelsMatch = false;
    } else {
      channelsMatch = role.channels.includes(channel);
    }
    if (!channelsMatch) continue;

    return roleName;
  }

  return config.defaultRole;
}
