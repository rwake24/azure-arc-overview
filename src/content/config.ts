import { defineCollection, z } from 'astro:content';

const pages = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    navLabel: z.string(),
    navOrder: z.number(),
    heroEmoji: z.string().optional(),
    heroSubtitle: z.string().optional(),
    accentColor: z.enum(['blue', 'green', 'purple', 'orange', 'red', 'cyan']).default('blue'),
  }),
});

export const collections = { pages };
