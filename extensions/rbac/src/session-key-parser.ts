/**
 * Extract peerId and channel from an OpenClaw session key.
 *
 * Session key formats (from src/routing/session-key.ts):
 *   per-channel-peer:         agent:main:telegram:direct:408001372
 *   per-account-channel-peer: agent:main:telegram:default:direct:408001372
 *   per-peer:                 agent:main:direct:408001372
 *   main:                     agent:main:main
 *   group:                    agent:main:telegram:group:-100123456
 *   channel:                  agent:main:telegram:channel:-100123456
 */

export type ParsedSessionKey = {
  peerId: string;
  channel: string | null;
  peerKind: "direct" | "group" | "channel";
};

const PEER_KINDS = new Set(["direct", "group", "channel"]);

export function parseSessionKey(sessionKey: string): ParsedSessionKey | null {
  const parts = sessionKey.split(":");

  // Minimum: agent:<id>:<kind>:<peerId> (4 parts for per-peer direct)
  if (parts.length < 4) return null;

  // Find the peerKind segment ("direct", "group", or "channel")
  for (let i = 2; i < parts.length - 1; i++) {
    if (PEER_KINDS.has(parts[i])) {
      const peerKind = parts[i] as "direct" | "group" | "channel";
      const peerId = parts[i + 1];
      if (!peerId) return null;

      // Channel is the segment right before peerKind (if it's not "agent" or agent ID)
      // For per-peer: agent:main:direct:408001372 → channel = null
      // For per-channel-peer: agent:main:telegram:direct:408001372 → channel = "telegram"
      // For per-account-channel-peer: agent:main:telegram:default:direct:408001372 → channel = "telegram"
      let channel: string | null = null;
      if (i >= 3) {
        // parts[2] is channel name (parts[0]="agent", parts[1]=agentId)
        channel = parts[2];
      }

      return { peerId, channel, peerKind };
    }
  }

  return null;
}
