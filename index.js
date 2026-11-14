import { readFileSync, readdirSync, statSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))

export const inject = ['skills', 'commands', 'workingDirectory']

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch {
    return null
  }
}

function formatDuration(config) {
  if (!config) return ''
  if (config.duration_mode === 'unlimited') return '不限'
  if (config.duration_mode === 'range') {
    return `${config.duration_min}-${config.duration_max} 分钟`
  }
  return `${config.minutes || 6} 分钟`
}

function collectProjects(cwd) {
  const roots = [join(cwd, 'runs'), join(cwd, 'projects')]
  const projects = []
  for (const root of roots) {
    let names
    try {
      names = readdirSync(root)
    } catch {
      continue
    }
    for (const name of names) {
      if (name.startsWith('.')) continue
      const projectDir = join(root, name)
      let projectStat
      try {
        projectStat = statSync(projectDir)
      } catch {
        continue
      }
      if (!projectStat.isDirectory()) continue
      const config = readJson(join(projectDir, 'project.json'))
      if (!config) continue
      const metadata = readJson(join(projectDir, '04_metadata.json')) || {}
      const finalFiles = readdirSync(projectDir).filter((entry) => /^07_.+\.mp4$/.test(entry))
      const finalName = finalFiles[0] || ''
      let finalSize = 0
      if (finalName) {
        try {
          finalSize = statSync(join(projectDir, finalName)).size
        } catch {
          finalSize = 0
        }
      }
      let imageCount = 0
      try {
        imageCount = readdirSync(join(projectDir, '06_images')).filter((entry) => entry.endsWith('.png')).length
      } catch {
        imageCount = 0
      }
      projects.push({
        name,
        path: projectDir,
        title: metadata.title || config.source_title || name,
        source: metadata.source || {},
        orientation: config.orientation || 'portrait',
        width: config.width || 0,
        height: config.height || 0,
        duration: formatDuration(config),
        durationMode: config.duration_mode || 'fixed',
        durationMin: config.duration_min,
        durationMax: config.duration_max,
        minutes: config.minutes,
        voice: config.voice || 'female',
        style: config.style || 'cinematic',
        segment: config.segment_seconds || [20, 40],
        imageCount,
        finalName,
        finalSize,
        done: Boolean(finalName),
        mtime: projectStat.mtimeMs,
      })
    }
  }
  projects.sort((a, b) => b.mtime - a.mtime)
  return projects.slice(0, 100)
}

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

  ctx.effect(() => ctx.commands.register({
    name: 'vcn-history',
    description: 'List Video Narrator projects in the current workspace',
    handler: async (invocation) => {
      const requested = String(invocation.rawInput || '').trim()
      const cwd = requested || await ctx.workingDirectory.ensure(invocation.agent)
      return { kind: 'success', text: JSON.stringify({ cwd, projects: collectProjects(cwd) }) }
    }
  }))
}
