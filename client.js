window.__ModuleLoader__.load({
  id: 'dsh-video-narrator',
  factory(require) {
    const React = require('react')
    const h = React.createElement
    const { useEffect, useState } = React
    const NS = 'dsh-video-narrator'

    const zh = {
      nav: '视频',
      title: '视频工作台',
      subtitle: '左侧查看历史项目，右侧配置下一条视频；开始后会创建新的会话。',
      workspace: '工作区',
      history: '历史项目',
      refresh: '刷新',
      empty: '这个工作区还没有历史项目',
      loading: '正在读取项目…',
      loadFailed: '读取历史失败',
      done: '已完成',
      unfinished: '未完成',
      images: '张图',
      reuse: '复用参数',
      source: '素材',
      sourceHint: 'YouTube/文章 URL、PDF 路径，或直接粘贴一段文字（可留空，让 Agent 再问）',
      orientation: '画幅',
      resolution: '分辨率',
      customSize: '自定义',
      portrait: '竖屏 9:16',
      landscape: '横屏 16:9',
      custom: '自定义',
      width: '宽',
      height: '高',
      duration: '时长',
      fixed: '固定',
      range: '范围',
      unlimited: '不限',
      minutes: '分钟',
      to: '到',
      segment: '每段',
      seconds: '秒',
      voice: '音色',
      female: 'female（Tina）',
      male: 'male（hugo）',
      customVoice: '自定义参考音',
      voiceRef: '参考音路径',
      voiceRefHint: '例如 /Users/you/voice.wav',
      voiceRefText: '参考音文字稿（可选）',
      style: '风格',
      cinematic: 'cinematic',
      documentary: 'documentary',
      anime: 'anime',
      customStyle: '自定义风格',
      start: '开始生成',
      started: '已创建新会话，正在交给 Agent 处理。',
      errorWidth: '请输入有效的自定义宽高。',
      errorMinutes: '请输入有效的分钟数。',
      errorSegment: '每段秒数必须大于 0，且起始值不能大于结束值。',
      errorVoice: '自定义参考音需要填写文件路径。',
      defaults: '恢复默认',
      selected: '已选项目',
      noFinal: '暂无成片',
      noWorkspace: '没有可用工作区',
    }

    const en = {
      nav: 'Video',
      title: 'Video workbench',
      subtitle: 'Browse projects on the left, configure the next video on the right; starting creates a new session.',
      workspace: 'Workspace',
      history: 'Projects',
      refresh: 'Refresh',
      empty: 'No projects in this workspace yet',
      loading: 'Loading projects…',
      loadFailed: 'Could not load projects',
      done: 'Done',
      unfinished: 'Unfinished',
      images: 'images',
      reuse: 'Reuse settings',
      source: 'Source',
      sourceHint: 'YouTube/article URL, PDF path, or paste text (leave empty to let the agent ask)',
      orientation: 'Orientation',
      resolution: 'Resolution',
      customSize: 'Custom',
      portrait: 'Portrait 9:16',
      landscape: 'Landscape 16:9',
      custom: 'Custom',
      width: 'Width',
      height: 'Height',
      duration: 'Duration',
      fixed: 'Fixed',
      range: 'Range',
      unlimited: 'Unlimited',
      minutes: 'min',
      to: 'to',
      segment: 'Per segment',
      seconds: 's',
      voice: 'Voice',
      female: 'female (Tina)',
      male: 'male (hugo)',
      customVoice: 'Custom reference',
      voiceRef: 'Reference path',
      voiceRefHint: 'e.g. /Users/you/voice.wav',
      voiceRefText: 'Reference transcript (optional)',
      style: 'Style',
      cinematic: 'cinematic',
      documentary: 'documentary',
      anime: 'anime',
      customStyle: 'Custom style',
      start: 'Start',
      started: 'New session created; handing it to the agent.',
      errorWidth: 'Enter a valid custom size.',
      errorMinutes: 'Enter a valid number of minutes.',
      errorSegment: 'Segment seconds must be positive and ordered.',
      errorVoice: 'A custom reference needs a file path.',
      defaults: 'Reset defaults',
      selected: 'Selected project',
      noFinal: 'No final video',
      noWorkspace: 'No workspace available',
    }

    const css = `
      .vcn-page { height: 100%; min-height: 0; display: flex; flex-direction: column; background: var(--dsw-alias-bg-base); color: var(--dsw-alias-label-primary); }
      .vcn-head { display: flex; align-items: flex-start; gap: 14px; padding: 18px 22px 14px; border-bottom: 1px solid var(--dsw-alias-border-l1); }
      .vcn-head-main { flex: 1; min-width: 0; }
      .vcn-title { margin: 0; font-size: 17px; font-weight: 650; }
      .vcn-sub { margin: 5px 0 0; font-size: 12px; color: var(--dsw-alias-label-secondary); line-height: 1.5; }
      .vcn-workspace { display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--dsw-alias-label-secondary); flex: 0 0 auto; padding-top: 2px; }
      .vcn-main { display: flex; flex: 1; min-height: 0; }
      .vcn-aside { width: 300px; flex: 0 0 300px; border-right: 1px solid var(--dsw-alias-border-l1); display: flex; flex-direction: column; min-height: 0; background: var(--dsw-alias-bg-layer-1); }
      .vcn-aside-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 13px 14px 9px; }
      .vcn-aside-title { font-size: 12px; font-weight: 600; color: var(--dsw-alias-label-secondary); letter-spacing: .02em; }
      .vcn-list { flex: 1; overflow: auto; padding: 0 8px 12px; display: grid; gap: 4px; align-content: start; }
      .vcn-item { width: 100%; text-align: left; border: 1px solid transparent; background: transparent; color: var(--dsw-alias-label-primary); border-radius: 9px; padding: 9px 10px; cursor: pointer; font: inherit; display: grid; gap: 3px; }
      .vcn-item:hover { background: var(--dsw-alias-bg-layer-2); }
      .vcn-item.selected { background: var(--dsw-alias-bg-layer-2); border-color: var(--dsw-alias-brand-primary); }
      .vcn-item-title { font-size: 12.5px; font-weight: 550; line-height: 1.35; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
      .vcn-item-meta { font-size: 11px; color: var(--dsw-alias-label-secondary); display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
      .vcn-badge { border: 1px solid var(--dsw-alias-border-l2); border-radius: 999px; padding: 0 6px; font-size: 10px; line-height: 16px; color: var(--dsw-alias-label-secondary); }
      .vcn-badge.done { color: var(--dsw-alias-state-success-primary); border-color: var(--dsw-alias-state-success-primary); }
      .vcn-empty { padding: 18px 12px; color: var(--dsw-alias-label-secondary); font-size: 12px; line-height: 1.6; }
      .vcn-content { flex: 1; min-width: 0; overflow: auto; padding: 16px 22px 0; display: flex; flex-direction: column; }
      .vcn-selected { margin-bottom: 14px; border: 1px solid var(--dsw-alias-border-l1); border-radius: 11px; padding: 11px 12px; background: var(--dsw-alias-bg-layer-1); display: grid; gap: 6px; }
      .vcn-selected-row { display: flex; gap: 8px; align-items: center; justify-content: space-between; }
      .vcn-selected-title { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .vcn-selected-meta { font-size: 11.5px; color: var(--dsw-alias-label-secondary); display: flex; flex-wrap: wrap; gap: 8px; }
      .vcn-body { display: grid; gap: 13px; padding-bottom: 4px; }
      .vcn-row { display: grid; grid-template-columns: 92px 1fr; gap: 12px; align-items: start; }
      .vcn-label { font-size: 12px; color: var(--dsw-alias-label-secondary); padding-top: 8px; }
      .vcn-control { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; min-width: 0; }
      .vcn-input, .vcn-select, .vcn-textarea { min-width: 0; box-sizing: border-box; border: 1px solid var(--dsw-alias-border-l2); border-radius: 9px; background: var(--dsw-alias-bg-layer-1); color: var(--dsw-alias-label-primary); font: inherit; font-size: 13px; padding: 7px 9px; }
      .vcn-textarea { width: 100%; min-height: 62px; resize: vertical; line-height: 1.5; }
      .vcn-input { width: 92px; }
      .vcn-wide { flex: 1 1 220px; }
      .vcn-select { padding-right: 24px; }
      .vcn-help { flex-basis: 100%; font-size: 11px; color: var(--dsw-alias-label-secondary); }
      .vcn-error { margin: 0 0 10px; padding: 8px 10px; border-radius: 8px; font-size: 12px; color: var(--dsw-alias-state-error-primary); border: 1px solid var(--dsw-alias-state-error-primary); }
      .vcn-notice { margin: 0 0 10px; padding: 8px 10px; border-radius: 8px; font-size: 12px; color: var(--dsw-alias-state-success-primary); border: 1px solid var(--dsw-alias-state-success-primary); }
      .vcn-foot { margin-top: auto; display: flex; justify-content: flex-end; gap: 8px; padding: 14px 0 18px; position: sticky; bottom: 0; background: var(--dsw-alias-bg-base); }
      .vcn-btn { height: 32px; padding: 0 13px; border-radius: 9px; font: inherit; font-size: 13px; cursor: pointer; border: 1px solid var(--dsw-alias-border-l2); background: var(--dsw-alias-bg-layer-1); color: var(--dsw-alias-label-primary); }
      .vcn-btn:hover { border-color: var(--dsw-alias-brand-primary); }
      .vcn-btn.primary { border-color: var(--dsw-alias-brand-primary); background: var(--dsw-alias-brand-primary); color: #fff; }
      .vcn-btn:disabled { opacity: .45; cursor: not-allowed; }
      .vcn-btn.ghost { border-color: transparent; background: transparent; color: var(--dsw-alias-label-secondary); }
      .vcn-btn.small { height: 26px; font-size: 11.5px; padding: 0 9px; }
      .vcn-reset { margin-right: auto; }
      @media (max-width: 760px) {
        .vcn-aside { width: 220px; flex-basis: 220px; }
        .vcn-row { grid-template-columns: 1fr; gap: 6px; }
        .vcn-label { padding-top: 0; }
      }
    `

    function field(label, control, help) {
      return h('div', { className: 'vcn-row' },
        h('div', { className: 'vcn-label' }, label),
        h('div', { className: 'vcn-control' }, control, help ? h('div', { className: 'vcn-help' }, help) : null))
    }

    function formatBytes(bytes) {
      if (!bytes) return ''
      if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`
    }

    function WorkbenchPage(props) {
      const t = props.t
      const loadHistory = props.loadHistory
      const startSession = props.startSession
      const workspaces = props.useWorkspaces((state) => state.items)
      const [workspacePath, setWorkspacePath] = useState('')
      const [history, setHistory] = useState([])
      const [loading, setLoading] = useState(false)
      const [historyError, setHistoryError] = useState('')
      const [selected, setSelected] = useState(null)
      const [notice, setNotice] = useState('')
      const [error, setError] = useState('')

      const [source, setSource] = useState('')
      const [orientation, setOrientation] = useState('portrait')
      const [resolution, setResolution] = useState('1080x1920')
      const [width, setWidth] = useState('1080')
      const [height, setHeight] = useState('1920')
      const [durationMode, setDurationMode] = useState('fixed')
      const [minutes, setMinutes] = useState('6')
      const [minMinutes, setMinMinutes] = useState('5')
      const [maxMinutes, setMaxMinutes] = useState('8')
      const [segmentMin, setSegmentMin] = useState('20')
      const [segmentMax, setSegmentMax] = useState('40')
      const [voice, setVoice] = useState('female')
      const [voiceRef, setVoiceRef] = useState('')
      const [voiceRefText, setVoiceRefText] = useState('')
      const [style, setStyle] = useState('cinematic')
      const [customStyle, setCustomStyle] = useState('')
      const [starting, setStarting] = useState(false)

      const workspaceList = Array.isArray(workspaces) ? workspaces : []
      const workspace = workspaceList.find((item) => item.path === workspacePath)
      const commandSessionId = workspace && Array.isArray(workspace.sessionIds) ? workspace.sessionIds[0] : ''

      useEffect(() => {
        const items = Array.isArray(workspaces) ? workspaces : []
        if (items.length === 0) return
        if (!workspacePath || !items.some((item) => item.path === workspacePath)) {
          setWorkspacePath(items[0].path)
        }
      }, [workspaces, workspacePath])

      useEffect(() => {
        if (!workspacePath) return
        let cancelled = false
        setLoading(true)
        setHistoryError('')
        loadHistory(workspacePath, commandSessionId)
          .then((data) => {
            if (cancelled) return
            setHistory(Array.isArray(data && data.projects) ? data.projects : [])
          })
          .catch((err) => {
            if (cancelled) return
            setHistoryError(err && err.message ? err.message : String(err))
          })
          .finally(() => {
            if (!cancelled) setLoading(false)
          })
        return () => { cancelled = true }
      }, [workspacePath, commandSessionId, loadHistory])

      function refresh() {
        if (!workspacePath) return
        setLoading(true)
        setHistoryError('')
        loadHistory(workspacePath, commandSessionId)
          .then((data) => setHistory(Array.isArray(data && data.projects) ? data.projects : []))
          .catch((err) => setHistoryError(err && err.message ? err.message : String(err)))
          .finally(() => setLoading(false))
      }

      function reset() {
        setSource('')
        setOrientation('portrait')
        setResolution('1080x1920')
        setWidth('1080')
        setHeight('1920')
        setDurationMode('fixed')
        setMinutes('6')
        setMinMinutes('5')
        setMaxMinutes('8')
        setSegmentMin('20')
        setSegmentMax('40')
        setVoice('female')
        setVoiceRef('')
        setVoiceRefText('')
        setStyle('cinematic')
        setCustomStyle('')
        setError('')
        setNotice('')
      }

      function applyProject(project) {
        if (!project) return
        const pw = Number(project.width || 0)
        const ph = Number(project.height || 0)
        setOrientation(pw > ph ? 'landscape' : 'portrait')
        setWidth(String(pw || 1080))
        setHeight(String(ph || 1920))
        const preset = `${pw}x${ph}`
        setResolution(['1080x1920', '720x1280', '1920x1080', '1280x720'].includes(preset) ? preset : 'custom')
        if (project.durationMode === 'range') {
          setDurationMode('range')
          setMinMinutes(String(project.durationMin ?? 5))
          setMaxMinutes(String(project.durationMax ?? 8))
        } else if (project.durationMode === 'unlimited') {
          setDurationMode('unlimited')
        } else {
          setDurationMode('fixed')
          setMinutes(String(project.minutes ?? 6))
        }
        if (Array.isArray(project.segment)) {
          setSegmentMin(String(project.segment[0]))
          setSegmentMax(String(project.segment[1]))
        }
        setVoice(project.voice === 'male' ? 'male' : 'female')
        setStyle(project.style || 'cinematic')
        setError('')
        setNotice('')
      }

      function buildMessage() {
        const lines = ['使用 video-narrator 制作视频。', '[VCS_PARAMS_CONFIRMED]']
        if (source.trim()) lines.push(`素材：${source.trim()}`)
        else lines.push('素材：待提供（请只询问素材，参数已确认）')

        const outW = Number(width)
        const outH = Number(height)
        if (!Number.isFinite(outW) || !Number.isFinite(outH) || outW <= 0 || outH <= 0) throw new Error(t('errorWidth'))
        lines.push(orientation === 'landscape' ? '画幅：横屏 16:9' : '画幅：竖屏 9:16')
        lines.push(`分辨率：${Math.round(outW)}x${Math.round(outH)}`)

        if (durationMode === 'fixed') {
          const value = Number(minutes)
          if (!Number.isFinite(value) || value <= 0) throw new Error(t('errorMinutes'))
          lines.push(`时长：固定 ${value} 分钟`)
        } else if (durationMode === 'range') {
          const lo = Number(minMinutes)
          const hi = Number(maxMinutes)
          if (!Number.isFinite(lo) || !Number.isFinite(hi) || lo <= 0 || hi <= 0 || lo > hi) throw new Error(t('errorMinutes'))
          lines.push(`时长：${lo}–${hi} 分钟`)
        } else {
          lines.push('时长：不限')
        }

        const smin = Number(segmentMin)
        const smax = Number(segmentMax)
        if (!Number.isFinite(smin) || !Number.isFinite(smax) || smin <= 0 || smax <= 0 || smin > smax) throw new Error(t('errorSegment'))
        lines.push(`每段：${smin}–${smax} 秒`)

        if (voice === 'custom') {
          if (!voiceRef.trim()) throw new Error(t('errorVoice'))
          lines.push(`音色：自定义参考音 ${voiceRef.trim()}`)
          if (voiceRefText.trim()) lines.push(`参考音文字稿：${voiceRefText.trim()}`)
        } else {
          lines.push(`音色：${voice === 'male' ? 'male（hugo）' : 'female（Tina）'}`)
        }

        const finalStyle = style === 'custom' ? customStyle.trim() : style
        lines.push(`风格：${finalStyle || 'cinematic'}`)
        lines.push('请直接开始，不要再次询问参数。')
        return lines.join('\n')
      }

      function submit() {
        if (starting) return
        try {
          const message = buildMessage()
          startSession(workspace ? workspace.workspaceId : undefined, message)
          setError('')
          setNotice(t('started'))
          setStarting(true)
        } catch (err) {
          setError(err && err.message ? err.message : String(err))
        }
      }

      return h('div', { className: 'vcn-page' },
        h('div', { className: 'vcn-head' },
          h('div', { className: 'vcn-head-main' },
            h('h1', { className: 'vcn-title' }, t('title')),
            h('p', { className: 'vcn-sub' }, t('subtitle'))),
          h('label', { className: 'vcn-workspace' },
            h('span', null, t('workspace')),
            h('select', {
              className: 'vcn-select', value: workspacePath,
              onChange: (event) => { setWorkspacePath(event.target.value); setSelected(null) },
            },
              (Array.isArray(workspaces) ? workspaces : []).map((item) =>
                h('option', { value: item.path, key: item.workspaceId }, item.title || item.path))))),
        h('div', { className: 'vcn-main' },
          h('aside', { className: 'vcn-aside' },
            h('div', { className: 'vcn-aside-head' },
              h('span', { className: 'vcn-aside-title' }, t('history')),
              h('button', { className: 'vcn-btn small ghost', type: 'button', disabled: loading, onClick: refresh }, t('refresh'))),
            h('div', { className: 'vcn-list' },
              loading ? h('div', { className: 'vcn-empty' }, t('loading')) : null,
              historyError ? h('div', { className: 'vcn-empty' }, `${t('loadFailed')}: ${historyError}`) : null,
              !loading && !historyError && history.length === 0 ? h('div', { className: 'vcn-empty' }, t('empty')) : null,
              history.map((project) => h('button', {
                key: project.path, type: 'button',
                className: `vcn-item${selected && selected.path === project.path ? ' selected' : ''}`,
                onClick: () => setSelected(project),
              },
                h('span', { className: 'vcn-item-title' }, project.title),
                h('span', { className: 'vcn-item-meta' },
                  h('span', { className: `vcn-badge${project.done ? ' done' : ''}` }, project.done ? t('done') : t('unfinished')),
                  h('span', null, project.orientation === 'landscape' ? '16:9' : '9:16'),
                  h('span', null, project.duration),
                  h('span', null, `${project.imageCount} ${t('images')}`)))))),
          h('section', { className: 'vcn-content' },
            selected ? h('div', { className: 'vcn-selected' },
              h('div', { className: 'vcn-selected-row' },
                h('span', { className: 'vcn-selected-title' }, selected.title),
                h('button', { className: 'vcn-btn small', type: 'button', onClick: () => applyProject(selected) }, t('reuse'))),
              h('div', { className: 'vcn-selected-meta' },
                h('span', null, `${t('selected')} · ${selected.orientation === 'landscape' ? '16:9' : '9:16'} · ${selected.duration}`),
                h('span', null, selected.finalName ? `${formatBytes(selected.finalSize)} · ${selected.finalName}` : t('noFinal')))) : null,
            notice ? h('p', { className: 'vcn-notice' }, notice) : null,
            error ? h('p', { className: 'vcn-error' }, error) : null,
            h('div', { className: 'vcn-body' },
              field(t('source'), h('textarea', {
                className: 'vcn-textarea', value: source, placeholder: t('sourceHint'),
                onChange: (event) => setSource(event.target.value),
              })),
              field(t('orientation'), h('select', {
                className: 'vcn-select', value: orientation,
                onChange: (event) => {
                  const value = event.target.value
                  setOrientation(value)
                  const allowed = value === 'landscape' ? ['1920x1080', '1280x720'] : ['1080x1920', '720x1280']
                  if (!allowed.includes(resolution)) {
                    const next = allowed[0]
                    const [w, h] = next.split('x')
                    setResolution(next)
                    setWidth(w)
                    setHeight(h)
                  }
                },
              },
                h('option', { value: 'portrait' }, t('portrait')),
                h('option', { value: 'landscape' }, t('landscape')))),
              field(t('resolution'), h('select', {
                className: 'vcn-select', value: resolution,
                onChange: (event) => {
                  const value = event.target.value
                  setResolution(value)
                  if (value !== 'custom') {
                    const [w, h] = value.split('x')
                    setWidth(w)
                    setHeight(h)
                  }
                },
              },
                (orientation === 'landscape'
                  ? [['1920x1080', '1920×1080'], ['1280x720', '1280×720']]
                  : [['1080x1920', '1080×1920'], ['720x1280', '720×1280']]
                ).map(([value, label]) => h('option', { value, key: value }, label)),
                h('option', { value: 'custom' }, t('customSize')))),
              resolution === 'custom' ? field('', h(React.Fragment, null,
                h('input', { className: 'vcn-input', type: 'number', min: 1, value: width, 'aria-label': t('width'), onChange: (event) => setWidth(event.target.value) }),
                h('span', { className: 'vcn-help' }, '×'),
                h('input', { className: 'vcn-input', type: 'number', min: 1, value: height, 'aria-label': t('height'), onChange: (event) => setHeight(event.target.value) }),
              )) : null,
              field(t('duration'), h(React.Fragment, null,
                h('select', { className: 'vcn-select', value: durationMode, onChange: (event) => setDurationMode(event.target.value) },
                  h('option', { value: 'fixed' }, t('fixed')),
                  h('option', { value: 'range' }, t('range')),
                  h('option', { value: 'unlimited' }, t('unlimited'))),
                durationMode === 'fixed' ? h(React.Fragment, null,
                  h('input', { className: 'vcn-input', type: 'number', min: 0.1, step: 0.5, value: minutes, onChange: (event) => setMinutes(event.target.value) }),
                  h('span', { className: 'vcn-help' }, t('minutes'))) : null,
                durationMode === 'range' ? h(React.Fragment, null,
                  h('input', { className: 'vcn-input', type: 'number', min: 0.1, step: 0.5, value: minMinutes, onChange: (event) => setMinMinutes(event.target.value) }),
                  h('span', { className: 'vcn-help' }, t('to')),
                  h('input', { className: 'vcn-input', type: 'number', min: 0.1, step: 0.5, value: maxMinutes, onChange: (event) => setMaxMinutes(event.target.value) }),
                  h('span', { className: 'vcn-help' }, t('minutes'))) : null)),
              field(t('segment'), h(React.Fragment, null,
                h('input', { className: 'vcn-input', type: 'number', min: 1, value: segmentMin, onChange: (event) => setSegmentMin(event.target.value) }),
                h('span', { className: 'vcn-help' }, t('to')),
                h('input', { className: 'vcn-input', type: 'number', min: 1, value: segmentMax, onChange: (event) => setSegmentMax(event.target.value) }),
                h('span', { className: 'vcn-help' }, t('seconds')))),
              field(t('voice'), h(React.Fragment, null,
                h('select', { className: 'vcn-select', value: voice, onChange: (event) => setVoice(event.target.value) },
                  h('option', { value: 'female' }, t('female')),
                  h('option', { value: 'male' }, t('male')),
                  h('option', { value: 'custom' }, t('customVoice'))),
                voice === 'custom' ? h(React.Fragment, null,
                  h('input', { className: 'vcn-input vcn-wide', value: voiceRef, placeholder: t('voiceRefHint'), onChange: (event) => setVoiceRef(event.target.value) }),
                  h('input', { className: 'vcn-input vcn-wide', value: voiceRefText, placeholder: t('voiceRefText'), onChange: (event) => setVoiceRefText(event.target.value) })) : null)),
              field(t('style'), h(React.Fragment, null,
                h('select', { className: 'vcn-select', value: style, onChange: (event) => setStyle(event.target.value) },
                  h('option', { value: 'cinematic' }, t('cinematic')),
                  h('option', { value: 'documentary' }, t('documentary')),
                  h('option', { value: 'anime' }, t('anime')),
                  h('option', { value: 'custom' }, t('customStyle'))),
                style === 'custom' ? h('input', { className: 'vcn-input vcn-wide', value: customStyle, onChange: (event) => setCustomStyle(event.target.value) }) : null))),
            h('div', { className: 'vcn-foot' },
              h('button', { className: 'vcn-btn ghost vcn-reset', type: 'button', onClick: reset }, t('defaults')),
              h('button', { className: 'vcn-btn primary', type: 'button', disabled: starting, onClick: submit }, t('start'))))),
        h('style', null, css))
    }

    function VideoIcon(props) {
      const size = props && props.size ? props.size : 18
      return h('svg', { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', 'aria-hidden': true },
        h('rect', { x: 3, y: 5, width: 18, height: 14, rx: 3, stroke: 'currentColor', strokeWidth: 1.7 }),
        h('path', { d: 'M10 9.5v5l4.2-2.5z', fill: 'currentColor' }))
    }

    return {
      inject: ['slots', 'locale', 'remote', 'remote.commands', 'uiWorkspace'],
      apply(ctx) {
        ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'video-narrator: locale')
        const t = ctx.locale.bind(NS)
        async function loadHistory(path, sessionId) {
          if (!sessionId) return { projects: [] }
          const line = path ? `/vcn-history ${path}` : '/vcn-history'
          const result = await ctx.remote.commands.execute(sessionId, line, [])
          if (!result || result.ok !== true) {
            const message = result && result.error && result.error.message ? result.error.message : 'vcn-history failed'
            throw new Error(message)
          }
          const execution = result.value
          const outcome = execution && execution.result
          if (!outcome || outcome.kind !== 'success' || !outcome.text) {
            throw new Error(outcome && outcome.text ? outcome.text : 'vcn-history returned no data')
          }
          return JSON.parse(outcome.text)
        }
        function startSession(workspaceId, prompt) {
          ctx.uiWorkspace.startSession(workspaceId, { prompt, whenDraftExists: 'append' })
        }
        ctx.effect(() => ctx.slots.inject('main', () => ctx.slots.register({
          name: 'main', key: 'video-narrator', locale: NS,
          inject: () => ({ t, loadHistory, startSession }),
        }, WorkbenchPage)), 'video-narrator: main page')
        ctx.effect(() => ctx.slots.inject('sidebar.panellist', () => ctx.slots.register({
          name: 'sidebar.panellist', id: 'video-narrator', order: 20, locale: NS,
          label: () => t('nav'),
        }, VideoIcon)), 'video-narrator: sidebar entry')
      },
    }
  },
})
