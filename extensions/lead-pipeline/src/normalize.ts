import { createHash } from "node:crypto";
import type { LeadRecord } from "./types.js";

export interface VkPost {
  id: number;
  from_id: number;
  owner_id: number;
  text: string;
  date: number;
}

export function normalizeVkPost(post: VkPost, groupShortName: string): LeadRecord {
  const sourceItemId = `vk_wall${post.owner_id}_${post.id}`;
  const id = createHash("sha256")
    .update(`vk:${sourceItemId}`)
    .digest("hex");

  return {
    id,
    source: "vk",
    source_item_id: sourceItemId,
    source_group: groupShortName,
    contact: `vk:${post.from_id}`,
    contact_url: `https://vk.com/wall${post.owner_id}_${post.id}`,
    raw_text: post.text.slice(0, 2000),
    created_at: new Date(post.date * 1000).toISOString(),
  };
}
