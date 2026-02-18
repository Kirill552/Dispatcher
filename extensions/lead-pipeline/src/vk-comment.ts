export function buildCommentText(
  fromCity: string | null,
  toCity: string | null,
  botUsername: string
): string {
  const route = fromCity && toCity ? ` ${fromCity}–${toCity}` : "";
  return (
    `Добрый день! Занимаемся грузоперевозками по России,` +
    ` можем взять${route}. Напишите для расчёта стоимости: t.me/${botUsername}`
  );
}

export interface VkCommentConfig {
  vkToken: string;
}

export async function postVkComment(
  ownerId: number,
  postId: number,
  text: string,
  config: VkCommentConfig
): Promise<boolean> {
  try {
    const body = new URLSearchParams({
      owner_id: String(ownerId < 0 ? ownerId : -ownerId),
      post_id: String(postId),
      message: text,
      access_token: config.vkToken,
      v: "5.199",
    });

    const res = await fetch("https://api.vk.com/method/wall.createComment", {
      method: "POST",
      body,
    });

    const data = await res.json() as any;
    return !data.error;
  } catch {
    return false;
  }
}
