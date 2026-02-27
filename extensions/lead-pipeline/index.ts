import type { OpenClawPluginApi } from "openclaw/plugin-sdk";
import { normalizeVkPost } from "./src/normalize.ts";
import { createDedupeStore } from "./src/dedupe.ts";
import { qualifyLead } from "./src/qualify.ts";
import { notifyOwner } from "./src/notify.ts";
import { buildCommentText, postVkComment } from "./src/vk-comment.ts";
import { appendLeadToSheets } from "./src/sheets.ts";
import { fetchAllGroupPosts } from "./src/ingest/vk.ts";
import type { LeadRecord } from "./src/types.ts";

interface LeadPipelineConfig {
  vkToken: string;
  vkGroupIds: string[];
  telegramBotToken: string;
  notifyUserId: string;
  botUsername: string;
  sheetsId?: string;
  sheetsServiceAccountJson?: string;
  openrouterApiKey: string;
  pollIntervalMs?: number;
  vkCommentDailyLimit?: number;
}

const plugin = {
  id: "lead-pipeline",

  register(api: OpenClawPluginApi) {
    const config = api.pluginConfig as LeadPipelineConfig;
    const pollInterval = config.pollIntervalMs ?? 300_000;
    const dailyLimit = config.vkCommentDailyLimit ?? 20;

    const dedupe = createDedupeStore();
    let commentsTodayCount = 0;
    let lastCommentResetDate = new Date().toDateString();

    function resetDailyCounterIfNeeded() {
      const today = new Date().toDateString();
      if (today !== lastCommentResetDate) {
        commentsTodayCount = 0;
        lastCommentResetDate = today;
      }
    }

    async function processPost(
      post: { id: number; from_id: number; owner_id: number; text: string; date: number },
      groupId: string
    ) {
      const lead: LeadRecord = normalizeVkPost(post, groupId);

      if (!dedupe.isNew(lead.source, lead.source_item_id)) return;
      dedupe.markSeen(lead.source, lead.source_item_id);

      const qualify = await qualifyLead(lead.raw_text, {
        openrouterApiKey: config.openrouterApiKey,
      });
      if (!qualify) {
        console.log(`[lead-pipeline] не квалифицирован: ${lead.source_item_id}`);
        return;
      }

      console.log(`[lead-pipeline] квалифицирован лид: ${lead.source_item_id}`);

      let botCommented = false;
      resetDailyCounterIfNeeded();
      if (commentsTodayCount < dailyLimit) {
        const commentText = buildCommentText(
          qualify.from_city,
          qualify.to_city,
          config.botUsername
        );
        botCommented = await postVkComment(post.owner_id, post.id, commentText, {
          vkToken: config.vkToken,
        });
        if (botCommented) {
          commentsTodayCount++;
          lead.bot_action = "vk_comment";
          lead.bot_comment_text = commentText;
        }
      }

      await notifyOwner(lead, qualify, botCommented, {
        telegramBotToken: config.telegramBotToken,
        notifyUserId: config.notifyUserId,
      });

      if (config.sheetsId && config.sheetsServiceAccountJson) {
        try {
          await appendLeadToSheets(lead, qualify, {
            sheetsId: config.sheetsId,
            sheetsServiceAccountJson: config.sheetsServiceAccountJson,
          });
        } catch (err) {
          console.error("[lead-pipeline] Sheets error:", err);
        }
      }
    }

    async function pollVk() {
      console.log("[lead-pipeline] polling VK...");
      const posts = await fetchAllGroupPosts({
        vkToken: config.vkToken,
        vkGroupIds: config.vkGroupIds,
      });
      for (const { post, groupId } of posts) {
        await processPost(post, groupId);
      }
    }

    api.services.register({
      id: "lead-monitor",
      async start() {
        console.log(
          `[lead-pipeline] lead-monitor started, polling every ${pollInterval}ms`
        );
        await pollVk().catch(console.error);
        setInterval(() => pollVk().catch(console.error), pollInterval);
      },
    });
  },
};

export default plugin;
