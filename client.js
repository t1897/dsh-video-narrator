window.__ModuleLoader__.load({
  id: 'dsh-video-narrator',
  factory(require) {
    const React = require('react')
    const h = React.createElement
    const { useEffect, useRef, useState } = React
    const NS = 'dsh-video-narrator'

    const zh = {
      open: '视频工作台',
      title: '视频工作台',
      subtitle: '左侧查看历史项目，右侧设置下一条视频；确认后写入输入框。',
      history: '历史项目',
      refresh: '刷新',
      empty: '还没有历史项目',
      loading: '正在读取项目…',
      loadFailed: '读取历史失败',
      done: '已完成',
      unfinished: '未完成',
      images: '张图',
      reuse: '复用参数',
      source: '素材',
      sourceHint: 'YouTube/文章 URL、PDF 路径，或直接粘贴一段文字（可留空，让 Agent 再问）',
      orientation: '画幅',
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
      cancel: '取消',
      fill: '填入输入框',
      send: '填入并开始',
      errorWidth: '请输入有效的自定义宽高。',
      errorMinutes: '请输入有效的分钟数。',
      errorSegment: '每段秒数必须大于 0，且起始值不能大于结束值。',
      errorVoice: '自定义参考音需要填写文件路径。',
      busy: '当前输入正在发送，稍后再试。',
      defaults: '恢复默认',
      selected: '已选项目',
      close: '关闭',
      noFinal: '暂无成片',
    }

    const en = {
      open: 'Video workbench',
      title: 'Video workbench',
      subtitle: 'Browse projects on the left, configure the next video on the right.',
      history: 'Projects',
      refresh: 'Refresh',
      empty: 'No projects yet',
      loading: 'Loading projects…',
      loadFailed: 'Could not load projects',
      done: 'Done',
      unfinished: 'Unfinished',
      images: 'images',
      reuse: 'Reuse settings',
      source: 'Source',
      sourceHint: 'YouTube/article URL, PDF path, or paste text (leave empty to let the agent ask)',
      orientation: 'Orientation',
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
      cancel: 'Cancel',
      fill: 'Fill composer',
      send: 'Fill and start',
      errorWidth: 'Enter a valid custom size.',
      errorMinutes: 'Enter a valid number of minutes.',
      errorSegment: 'Segment seconds must be positive and ordered.',
      errorVoice: 'A custom reference needs a file path.',
      busy: 'The input is busy; try again in a moment.',
      defaults: 'Reset defaults',
      selected: 'Selected project',
      close: 'Close',
      noFinal: 'No final video',
    }

    const css = `
      .vcn-trigger {
        display: inline-flex; align-items: center; gap: 6px;
        height: 28px; padding: 0 10px; border-radius: 999px;
        border: 1px solid var(--dsw-alias-border-l2);
        background: var(--dsw-alias-bg-layer-1);
        color: var(--dsw-alias-label-primary);
        font: inherit; font-size: 12px; cursor: pointer;
      }
      .vcn-trigger:hover { border-color: var(--dsw-alias-brand-primary); }
      .vcn-trigger svg { width: 13px; height: 13px; }
      .vcn-dialog {
        width: min(1120px, calc(100vw - 32px));
        height: min(86vh, 860px);
        max-height: 86vh;
        padding: 0; overflow: hidden;
        border: 1px solid var(--dsw-alias-border-l2);
        border-radius: 16px;
        background: var(--dsw-alias-bg-overlay);
        color: var(--dsw-alias-label-primary);
        box-shadow: 0 24px 72px rgba(0,0,0,.32);
      }
      .vcn-dialog::backdrop { background: rgba(0,0,0,.44); }
      .vcn-shell { display: flex; flex-direction: column; height: 100%; min-height: 0; }
      .vcn-head { display: flex; align-items: flex-start; gap: 12px; padding: 18px 22px 14px; border-bottom: 1px solid var(--dsw-alias-border-l1); }
      .vcn-head-main { flex: 1; min-width: 0; }
      .vcn-title { margin: 0; font-size: 17px; font-weight: 650; }
      .vcn-sub { margin: 5px 0 0; font-size: 12px; color: var(--dsw-alias-label-secondary); line-height: 1.5; }
      .vcn-iconbtn { width: 30px; height: 30px; border-radius: 8px; border: 1px solid transparent; background: transparent; color: var(--dsw-alias-label-secondary); cursor: pointer; font-size: 16px; line-height: 1; }
      .vcn-iconbtn:hover { background: var(--dsw-alias-bg-layer-2); color: var(--dsw-alias-label-primary); }
      .vcn-main { display: flex; flex: 1; min-height: 0; }
      .vcn-aside { width: 300px; flex: 0 0 300px; border-right: 1px solid var(--dsw-alias-border-l1); display: flex; flex-direction: column; min-height: 0; background: var(--dsw-alias-bg-layer-1); }
      .vcn-aside-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 13px 14px 9px; }
      .vcn-aside-title { font-size: 12px; font-weight: 600; color: var(--dsw-alias-label-secondary); letter-spacing: .02em; }
      .vcn-list { flex: 1; overflow: auto; padding: 0 8px 10px; display: grid; gap: 4px; align-content: start; }
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
      .vcn-foot { margin-top: auto; display: flex; justify-content: flex-end; gap: 8px; padding: 14px 0 18px; position: sticky; bottom: 0; background: var(--dsw-alias-bg-overlay); }
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

    function formatDate(ms) {
      if (!ms) return ''
      const d = new Date(ms)
      return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    }

    function Entry(props) {
      const t = props.t
      const actions = props.inputActions
      const sessionId = props.sessionId
      const loadHistory = props.loadHistory
      const [open, setOpen] = useState(false)
      const [history, setHistory] = useState([])
      const [loading, setLoading] = useState(false)
      const [historyError, setHistoryError] = useState('')
      const [selected, setSelected] = useState(null)

      const [source, setSource] = useState('')
      const [orientation, setOrientation] = useState('portrait')
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
      const [error, setError] = useState('')

      const dialogRef = useRef(null)
      const phase = props.useInput((state) => state.phase)
      const busy = phase !== 'plain'

      useEffect(() => {
        const dialog = dialogRef.current
        if (!dialog) return
        if (open && !dialog.open) dialog.showModal()
        if (!open && dialog.open) dialog.close()
      }, [open])

      useEffect(() => {
        if (!open || !loadHistory) return
        let cancelled = false
        setLoading(true)
        setHistoryError('')
        loadHistory(sessionId)
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
      }, [open, sessionId, loadHistory])

      function reset() {
        setSource('')
        setOrientation('portrait')
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
      }

      function applyProject(project) {
        if (!project) return
        setSelected(project)
        const pw = Number(project.width || 0)
        const ph = Number(project.height || 0)
        if (project.orientation === 'landscape' && pw === 1920 && ph === 1080) {
          setOrientation('landscape')
          setWidth('1920')
          setHeight('1080')
        } else if (project.orientation === 'portrait' && pw === 1080 && ph === 1920) {
          setOrientation('portrait')
          setWidth('1080')
          setHeight('1920')
        } else {
          setOrientation('custom')
          setWidth(String(pw || 1080))
          setHeight(String(ph || 1920))
        }
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
      }

      function buildMessage() {
        const lines = ['使用 video-narrator 制作视频。', '[VCS_PARAMS_CONFIRMED]']
        if (source.trim()) lines.push(`素材：${source.trim()}`)
        else lines.push('素材：待提供（请只询问素材，参数已确认）')

        if (orientation === 'custom') {
          const w = Number(width)
          const hh = Number(height)
          if (!Number.isFinite(w) || !Number.isFinite(hh) || w <= 0 || hh <= 0) throw new Error(t('errorWidth'))
          lines.push(`画幅：自定义 ${Math.round(w)}x${Math.round(hh)}`)
        } else {
          lines.push(orientation === 'landscape' ? '画幅：横屏 16:9（1920x1080）' : '画幅：竖屏 9:16（1080x1920）')
        }

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

      function commit(send) {
        if (busy) { setError(t('busy')); return }
        try {
          actions.setDraft(buildMessage())
          if (send) actions.submit()
          setError('')
          setOpen(false)
        } catch (err) {
          setError(err && err.message ? err.message : String(err))
        }
      }

      return h(React.Fragment, null,
        h('button', {
          className: 'vcn-trigger', type: 'button', title: t('open'),
          onClick: () => { setError(''); setOpen(true) },
        },
          h('svg', { viewBox: '0 0 24 24', fill: 'none', 'aria-hidden': true },
            h('rect', { x: 3, y: 5, width: 18, height: 14, rx: 3, stroke: 'currentColor', strokeWidth: 1.7 }),
            h('path', { d: 'M10 9.5v5l4.2-2.5z', fill: 'currentColor' })),
          h('span', null, t('open'))),
        h('dialog', {
          ref: dialogRef, className: 'vcn-dialog',
          onClose: () => setOpen(false),
          onClick: (event) => { if (event.target === dialogRef.current) setOpen(false) },
        },
          h('div', { className: 'vcn-shell' },
            h('div', { className: 'vcn-head' },
              h('div', { className: 'vcn-head-main' },
                h('h2', { className: 'vcn-title' }, t('title')),
                h('p', { className: 'vcn-sub' }, t('subtitle'))),
              h('button', { className: 'vcn-iconbtn', type: 'button', title: t('close'), onClick: () => setOpen(false) }, '×')),
            h('div', { className: 'vcn-main' },
              h('aside', { className: 'vcn-aside' },
                h('div', { className: 'vcn-aside-head' },
                  h('span', { className: 'vcn-aside-title' }, t('history')),
                  h('button', {
                    className: 'vcn-btn small ghost', type: 'button', disabled: loading,
                    onClick: () => {
                      setLoading(true); setHistoryError('')
                      loadHistory(sessionId)
                        .then((data) => setHistory(Array.isArray(data && data.projects) ? data.projects : []))
                        .catch((err) => setHistoryError(err && err.message ? err.message : String(err)))
                        .finally(() => setLoading(false))
                    },
                  }, t('refresh'))),
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
                      h('span', null, `${project.imageCount} ${t('images')}`))))),
              h('section', { className: 'vcn-content' },
                selected ? h('div', { className: 'vcn-selected' },
                  h('div', { className: 'vcn-selected-row' },
                    h('span', { className: 'vcn-selected-title' }, selected.title),
                    h('button', { className: 'vcn-btn small', type: 'button', onClick: () => applyProject(selected) }, t('reuse'))),
                  h('div', { className: 'vcn-selected-meta' },
                    h('span', null, `${t('selected')} · ${selected.orientation === 'landscape' ? '16:9' : '9:16'} · ${selected.duration}`),
                    h('span', null, selected.finalName ? `${formatBytes(selected.finalSize)} · ${selected.finalName}` : t('noFinal')))) : null,
                error ? h('p', { className: 'vcn-error' }, error) : null,
                h('div', { className: 'vcn-body' },
                  field(t('source'), h('textarea', {
                    className: 'vcn-textarea', value: source, placeholder: t('sourceHint'),
                    onChange: (event) => setSource(event.target.value),
                  })),
                  field(t('orientation'), h('select', {
                    className: 'vcn-select', value: orientation,
                    onChange: (event) => setOrientation(event.target.value),
                  },
                    h('option', { value: 'portrait' }, t('portrait')),
                    h('option', { value: 'landscape' }, t('landscape')),
                    h('option', { value: 'custom' }, t('custom')))),
                  orientation === 'custom' ? field('', h(React.Fragment, null,
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
                  h('button', { className: 'vcn-btn', type: 'button', onClick: () => setOpen(false) }, t('cancel')),
                  h('button', { className: 'vcn-btn', type: 'button', disabled: busy, onClick: () => commit(false) }, t('fill')),
                  h('button', { className: 'vcn-btn primary', type: 'button', disabled: busy, onClick: () => commit(true) }, t('send')))))))),
        h('style', null, css))
    }

    return {
      inject: ['slots', 'locale', 'remote', 'remote.commands'],
      apply(ctx) {
        ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'video-narrator: locale')
        const t = ctx.locale.bind(NS)
        async function loadHistory(sessionId) {
          const result = await ctx.remote.commands.execute(sessionId, '/vcn-history', [])
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
        ctx.effect(() => ctx.slots.inject('conversation.composer.dock', () =>
          ctx.slots.register({
            name: 'conversation.composer.dock',
            id: 'video-narrator-control',
            order: 30,
          }, (props) => h(Entry, { ...props, t, loadHistory }))), 'video-narrator: composer control')
      },
    }
  },
})
