window.__ModuleLoader__.load({
  id: 'dsh-video-narrator',
  factory(require) {
    const React = require('react')
    const h = React.createElement
    const { useEffect, useRef, useState } = React
    const NS = 'dsh-video-narrator'

    const zh = {
      open: '视频参数',
      title: 'Video Narrator 参数',
      subtitle: '设置后填入输入框；Skill 会按这些参数直接开始。',
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
    }

    const en = {
      open: 'Video settings',
      title: 'Video Narrator settings',
      subtitle: 'Fill the composer with these settings; the skill starts from them.',
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
        width: min(620px, calc(100vw - 32px));
        max-height: min(82vh, 760px);
        overflow: auto;
        padding: 0;
        border: 1px solid var(--dsw-alias-border-l2);
        border-radius: 16px;
        background: var(--dsw-alias-bg-overlay);
        color: var(--dsw-alias-label-primary);
        box-shadow: 0 24px 64px rgba(0,0,0,.28);
      }
      .vcn-dialog::backdrop { background: rgba(0,0,0,.42); }
      .vcn-head { padding: 18px 20px 12px; border-bottom: 1px solid var(--dsw-alias-border-l1); }
      .vcn-title { margin: 0; font-size: 16px; font-weight: 650; }
      .vcn-sub { margin: 5px 0 0; font-size: 12px; color: var(--dsw-alias-label-secondary); line-height: 1.5; }
      .vcn-body { padding: 14px 20px 4px; display: grid; gap: 13px; }
      .vcn-row { display: grid; grid-template-columns: 96px 1fr; gap: 12px; align-items: center; }
      .vcn-label { font-size: 12px; color: var(--dsw-alias-label-secondary); }
      .vcn-control { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; min-width: 0; }
      .vcn-input, .vcn-select, .vcn-textarea {
        min-width: 0; box-sizing: border-box;
        border: 1px solid var(--dsw-alias-border-l2);
        border-radius: 9px; background: var(--dsw-alias-bg-layer-1);
        color: var(--dsw-alias-label-primary);
        font: inherit; font-size: 13px; padding: 7px 9px;
      }
      .vcn-textarea { width: 100%; min-height: 64px; resize: vertical; line-height: 1.5; }
      .vcn-input { width: 92px; }
      .vcn-wide { flex: 1 1 220px; }
      .vcn-select { padding-right: 24px; }
      .vcn-help { flex-basis: 100%; font-size: 11px; color: var(--dsw-alias-label-secondary); }
      .vcn-error { margin: 0 20px; padding: 8px 10px; border-radius: 8px; font-size: 12px; color: var(--dsw-alias-state-error-primary); border: 1px solid var(--dsw-alias-state-error-primary); }
      .vcn-foot { display: flex; justify-content: flex-end; gap: 8px; padding: 14px 20px 18px; }
      .vcn-btn { height: 32px; padding: 0 13px; border-radius: 9px; font: inherit; font-size: 13px; cursor: pointer; border: 1px solid var(--dsw-alias-border-l2); background: var(--dsw-alias-bg-layer-1); color: var(--dsw-alias-label-primary); }
      .vcn-btn:hover { border-color: var(--dsw-alias-brand-primary); }
      .vcn-btn.primary { border-color: var(--dsw-alias-brand-primary); background: var(--dsw-alias-brand-primary); color: #fff; }
      .vcn-btn:disabled { opacity: .45; cursor: not-allowed; }
      .vcn-btn.ghost { border-color: transparent; background: transparent; color: var(--dsw-alias-label-secondary); }
      .vcn-reset { margin-right: auto; }
      @media (max-width: 560px) {
        .vcn-row { grid-template-columns: 1fr; gap: 6px; }
        .vcn-label { font-size: 12px; }
      }
    `

    function field(label, control, help) {
      return h('div', { className: 'vcn-row' },
        h('div', { className: 'vcn-label' }, label),
        h('div', { className: 'vcn-control' }, control, help ? h('div', { className: 'vcn-help' }, help) : null))
    }

    function Entry(props) {
      const t = props.t
      const actions = props.inputActions
      const [open, setOpen] = useState(false)
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
          const message = buildMessage()
          actions.setDraft(message)
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
          h('div', { className: 'vcn-head' },
            h('h2', { className: 'vcn-title' }, t('title')),
            h('p', { className: 'vcn-sub' }, t('subtitle'))),
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
            h('button', { className: 'vcn-btn primary', type: 'button', disabled: busy, onClick: () => commit(true) }, t('send')))),
        h('style', null, css))
    }

    return {
      inject: ['slots', 'locale'],
      apply(ctx) {
        ctx.effect(() => ctx.locale.register(NS, { zh, en }), 'video-narrator: locale')
        const t = ctx.locale.bind(NS)
        ctx.effect(() => ctx.slots.inject('conversation.composer.dock', () =>
          ctx.slots.register({
            name: 'conversation.composer.dock',
            id: 'video-narrator-control',
            order: 30,
          }, (props) => h(Entry, { ...props, t }))), 'video-narrator: composer control')
      },
    }
  },
})
