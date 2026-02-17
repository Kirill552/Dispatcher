import Fastify from "fastify";
import fastifyStatic from "@fastify/static";
import fastifyView from "@fastify/view";
import ejs from "ejs";
import { readdir, readFile, stat } from "node:fs/promises";
import { join, basename, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { marked } from "marked";
import matter from "gray-matter";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

const PORT = parseInt(process.env.PORT || "3000", 10);
const ARTICLES_DIR = process.env.ARTICLES_DIR || join(__dirname, "articles");
const DOMAIN = process.env.DOMAIN || "https://ai-dispatcher.ru";

// --- Article cache ---
interface ArticleMeta {
  slug: string;
  title: string;
  description: string;
  date: string;
  keywords: string[];
  html: string;
  mtime: number;
}

const articleCache = new Map<string, ArticleMeta>();

async function loadArticle(slug: string): Promise<ArticleMeta | null> {
  const filePath = join(ARTICLES_DIR, slug + ".md");
  try {
    const fileStat = await stat(filePath);
    const cached = articleCache.get(slug);
    if (cached && cached.mtime === fileStat.mtimeMs) {
      return cached;
    }

    const raw = await readFile(filePath, "utf-8");
    const { data, content } = matter(raw);
    const html = await marked.parse(content);

    const article: ArticleMeta = {
      slug,
      title: data.title || slug,
      description: data.description || "",
      date: data.date ? formatDate(data.date) : "",
      keywords: Array.isArray(data.keywords) ? data.keywords : [],
      html,
      mtime: fileStat.mtimeMs,
    };

    articleCache.set(slug, article);
    return article;
  } catch {
    return null;
  }
}

async function listArticles(): Promise<ArticleMeta[]> {
  try {
    const files = await readdir(ARTICLES_DIR);
    const mdFiles = files.filter((f) => extname(f) === ".md");
    const articles: ArticleMeta[] = [];

    for (const file of mdFiles) {
      const slug = basename(file, ".md");
      const article = await loadArticle(slug);
      if (article) articles.push(article);
    }

    // Sort by date descending
    articles.sort((a, b) => {
      if (!a.date && !b.date) return 0;
      if (!a.date) return 1;
      if (!b.date) return -1;
      return b.date.localeCompare(a.date);
    });

    return articles;
  } catch {
    return [];
  }
}

function formatDate(date: string | Date): string {
  const d = new Date(date);
  if (isNaN(d.getTime())) return String(date);
  return d.toLocaleDateString("ru-RU", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// --- Server ---
const app = Fastify({ logger: true });

// Static files
await app.register(fastifyStatic, {
  root: join(__dirname, "public"),
  prefix: "/public/",
  maxAge: "30d",
});

// Template engine
await app.register(fastifyView, {
  engine: { ejs },
  root: join(__dirname, "templates"),
});

// --- Routes ---

// Главная
app.get("/", async (_req, reply) => {
  return reply.view("index.ejs");
});

// Услуги
app.get("/uslugi", async (_req, reply) => {
  return reply.view("uslugi.ejs");
});

// О компании
app.get("/o-kompanii", async (_req, reply) => {
  return reply.view("o-kompanii.ejs");
});

// Контакты
app.get("/kontakty", async (_req, reply) => {
  return reply.view("kontakty.ejs");
});

// Блог — список
app.get("/blog", async (_req, reply) => {
  const articles = await listArticles();
  return reply.view("blog-list.ejs", { articles });
});

// Блог — статья
app.get<{ Params: { slug: string } }>("/blog/:slug", async (req, reply) => {
  const { slug } = req.params;
  // Sanitize slug
  if (!/^[a-z0-9-]+$/.test(slug)) {
    return reply.status(404).view("404.ejs");
  }
  const article = await loadArticle(slug);
  if (!article) {
    return reply.status(404).view("404.ejs");
  }
  return reply.view("blog-article.ejs", { article });
});

// Sitemap.xml
app.get("/sitemap.xml", async (_req, reply) => {
  const articles = await listArticles();
  const staticPages = [
    { url: "/", priority: "1.0", freq: "weekly" },
    { url: "/uslugi", priority: "0.8", freq: "monthly" },
    { url: "/o-kompanii", priority: "0.6", freq: "monthly" },
    { url: "/kontakty", priority: "0.6", freq: "monthly" },
    { url: "/blog", priority: "0.7", freq: "weekly" },
  ];

  let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
  xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n';

  for (const page of staticPages) {
    xml += `  <url>\n    <loc>${DOMAIN}${page.url}</loc>\n    <changefreq>${page.freq}</changefreq>\n    <priority>${page.priority}</priority>\n  </url>\n`;
  }

  for (const article of articles) {
    xml += `  <url>\n    <loc>${DOMAIN}/blog/${article.slug}</loc>\n    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>\n`;
  }

  xml += "</urlset>";

  reply.header("Content-Type", "application/xml; charset=utf-8");
  return reply.send(xml);
});

// robots.txt (fallback if not served by nginx)
app.get("/robots.txt", async (_req, reply) => {
  return reply.sendFile("robots.txt");
});

// 404
app.setNotFoundHandler(async (_req, reply) => {
  return reply.status(404).view("404.ejs");
});

// --- Start ---
try {
  const HOST = process.env.HOST || "127.0.0.1";
  await app.listen({ port: PORT, host: HOST });
  console.log(`Site running at http://${HOST}:${PORT}`);
} catch (err) {
  app.log.error(err);
  process.exit(1);
}
