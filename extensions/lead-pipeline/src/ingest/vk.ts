export interface VkIngestConfig {
  vkToken: string;
  vkGroupIds: string[];
}

export interface VkPost {
  id: number;
  from_id: number;
  owner_id: number;
  text: string;
  date: number;
}

export async function fetchRecentVkPosts(
  groupId: string,
  token: string
): Promise<VkPost[]> {
  const params = new URLSearchParams({
    owner_id: `-${groupId}`,
    count: "20",
    filter: "all",
    access_token: token,
    v: "5.199",
  });

  try {
    const res = await fetch(
      `https://api.vk.com/method/wall.get?${params.toString()}`
    );
    const data = await res.json() as any;

    if (data.error) {
      console.error(`[lead-pipeline] VK API error for group ${groupId}:`, data.error.error_msg);
      return [];
    }

    return (data.response?.items ?? []) as VkPost[];
  } catch (err) {
    console.error(`[lead-pipeline] VK fetch failed for group ${groupId}:`, err);
    return [];
  }
}

export async function fetchAllGroupPosts(
  config: VkIngestConfig
): Promise<Array<{ post: VkPost; groupId: string }>> {
  const results: Array<{ post: VkPost; groupId: string }> = [];

  for (const groupId of config.vkGroupIds) {
    await new Promise((r) => setTimeout(r, 350));
    const posts = await fetchRecentVkPosts(groupId, config.vkToken);
    for (const post of posts) {
      if (post.text.trim().length > 10) {
        results.push({ post, groupId });
      }
    }
  }

  return results;
}
