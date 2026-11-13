import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))

export const inject = ['skills']

export function apply(ctx) {
  const content = readFileSync(join(here, 'SKILL.md'), 'utf8')
  ctx.effect(() => ctx.skills.register({
    name: 'video-narrator',
    description: 'Turns a video, article, PDF, or text into a narrated video with per-scene images, TTS, metadata, and ordered API fallback.',
    content,
    source: 'bundled',
    resourceBase: { kind: 'directory', path: here },
    invocation: { modelInvocable: true, userInvocable: true }
  }))
}
