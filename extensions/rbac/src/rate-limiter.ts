/**
 * Sliding-window rate limiter for blocked-call log output.
 *
 * Tracks how many times a blocked tool call has been logged per peer ID
 * within a 60-second window. Once the limit is exceeded, subsequent
 * calls are suppressed (shouldLog returns false) and counted.
 */

const WINDOW_MS = 60_000;

type PeerWindow = {
  /** Timestamp (ms) when the current window started. */
  windowStart: number;
  /** Number of calls logged in the current window. */
  logged: number;
  /** Number of calls suppressed in the current window. */
  suppressed: number;
};

export class RateLimiter {
  private readonly maxPerMinute: number;
  private readonly peers: Map<string, PeerWindow> = new Map();

  constructor(maxPerMinute: number) {
    this.maxPerMinute = maxPerMinute;
  }

  /**
   * Check whether a blocked-call log entry should be emitted for this peer.
   *
   * @returns `true` if the call should be logged, `false` if it should be suppressed.
   */
  shouldLog(peerId: string): boolean {
    const now = Date.now();
    let peer = this.peers.get(peerId);

    // First call from this peer, or window has expired — start fresh.
    if (!peer || now - peer.windowStart >= WINDOW_MS) {
      peer = { windowStart: now, logged: 0, suppressed: 0 };
      this.peers.set(peerId, peer);
    }

    // Under the limit — allow logging.
    if (peer.logged < this.maxPerMinute) {
      peer.logged++;
      return true;
    }

    // Over the limit — suppress.
    peer.suppressed++;
    return false;
  }

  /**
   * Return how many log entries have been suppressed for a peer
   * in the current window.
   */
  getSuppressed(peerId: string): number {
    const peer = this.peers.get(peerId);
    if (!peer) return 0;

    // If the window has expired, nothing is suppressed.
    const now = Date.now();
    if (now - peer.windowStart >= WINDOW_MS) return 0;

    return peer.suppressed;
  }
}
