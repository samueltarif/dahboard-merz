// Wrapper fino sobre o ECharts. As cores vêm dos tokens CSS, então tema claro/escuro
// e mudanças de paleta acontecem sem tocar nos gráficos.
import { brl, brlc } from '../format.js';

const live = new Set(); // gráficos montados (para resize e troca de tema)

const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
export const seriesColor = (i) => css(`--c${i % 4}`);

function theme() {
  return {
    fg: css('--color-fg'), muted: css('--color-fg-muted'), axis: css('--chart-axis'), grid: css('--chart-grid'),
    panel: css('--surface-popover'), border: css('--color-border-line'), font: css('--font-sans'),
  };
}

function tooltip(t, extra = {}) {
  return {
    backgroundColor: t.panel, borderColor: t.border, borderWidth: 1, padding: [8, 10],
    textStyle: { color: t.fg, fontSize: 12, fontFamily: t.font },
    extraCssText: 'box-shadow: 0 6px 24px rgba(0,0,0,.12); border-radius: 8px;',
    ...extra,
  };
}

function mount(el, buildOption, onClick, tries = 0) {
  // As views montam o DOM fora da página e só depois o inserem; o ECharts precisa
  // do elemento visível para medir o tamanho, então esperamos ele entrar no documento.
  if (!el.isConnected) {
    if (tries < 120) requestAnimationFrame(() => mount(el, buildOption, onClick, tries + 1));
    return null;
  }
  const prev = echarts.getInstanceByDom(el);
  if (prev) prev.dispose();
  const chart = echarts.init(el, null, { renderer: 'svg' });
  const entry = { chart, el, buildOption };
  chart.setOption(buildOption(theme()));
  if (onClick) chart.on('click', (p) => onClick(p));
  live.add(entry);
  return chart;
}

/**
 * Barras agrupadas (vertical ou horizontal).
 * @param {HTMLElement} el
 * @param {{categories: string[], series: {name: string, data: number[], color?: number}[], horizontal?: boolean,
 *          fmt?: (v:number)=>string, onClick?: (p)=>void, selected?: string, labels?: boolean}} cfg
 */
export function bars(el, cfg) {
  const fmt = cfg.fmt || brl;
  const short = cfg.shortFmt || brlc;
  const many = cfg.series.length > 1;
  return mount(el, (t) => {
    const catAxis = {
      type: 'category', data: cfg.categories, inverse: !!cfg.horizontal,
      axisLine: { lineStyle: { color: t.axis } }, axisTick: { show: false },
      axisLabel: { color: t.muted, fontSize: 11, fontFamily: t.font, interval: 0, hideOverlap: true },
    };
    const valAxis = {
      type: 'value', splitLine: { lineStyle: { color: t.grid } }, axisLine: { show: false },
      axisLabel: { color: t.muted, fontSize: 11, fontFamily: t.font, formatter: short },
    };
    return {
      animationDuration: 450, animationEasing: 'cubicOut',
      grid: { left: cfg.horizontal ? 8 : 8, right: cfg.horizontal ? 56 : 12, top: 12, bottom: 8, containLabel: true },
      tooltip: tooltip(t, {
        trigger: 'axis', axisPointer: { type: 'shadow', shadowStyle: { color: t.grid, opacity: 0.5 } },
        valueFormatter: fmt,
      }),
      xAxis: cfg.horizontal ? valAxis : catAxis,
      yAxis: cfg.horizontal ? catAxis : valAxis,
      series: cfg.series.map((s, i) => ({
        name: s.name, type: 'bar', data: s.data.map((v, j) => ({
          value: v,
          itemStyle: cfg.selected && cfg.categories[j] !== cfg.selected ? { opacity: 0.35 } : undefined,
        })),
        barMaxWidth: many ? 14 : 22, barGap: '15%',
        itemStyle: { color: seriesColor(s.color ?? i), borderRadius: cfg.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0] },
        emphasis: { focus: 'none', itemStyle: { opacity: 1 } },
        label: cfg.labels && !many ? {
          show: true, position: cfg.horizontal ? 'right' : 'top', color: t.muted, fontSize: 11, fontFamily: t.font,
          formatter: (p) => short(p.value),
        } : { show: false },
      })),
    };
  }, cfg.onClick);
}

/** Linha (uma ou mais séries na mesma escala). */
export function lines(el, cfg) {
  const fmt = cfg.fmt || brl;
  return mount(el, (t) => ({
    animationDuration: 450,
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    tooltip: tooltip(t, { trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: t.axis } }, valueFormatter: fmt }),
    xAxis: {
      type: 'category', data: cfg.categories, boundaryGap: false, axisLine: { lineStyle: { color: t.axis } }, axisTick: { show: false },
      axisLabel: { color: t.muted, fontSize: 11, fontFamily: t.font, hideOverlap: true },
    },
    yAxis: {
      type: 'value', min: cfg.min, max: cfg.max, splitLine: { lineStyle: { color: t.grid } },
      axisLabel: { color: t.muted, fontSize: 11, fontFamily: t.font, formatter: cfg.shortFmt || brlc },
    },
    series: cfg.series.map((s, i) => ({
      name: s.name, type: 'line', data: s.data, smooth: 0.25, showSymbol: false, symbolSize: 8,
      lineStyle: { width: 2, color: seriesColor(s.color ?? i) }, itemStyle: { color: seriesColor(s.color ?? i) },
      areaStyle: cfg.area ? { color: seriesColor(s.color ?? i), opacity: 0.08 } : undefined,
    })),
  }));
}

export function disposeAll() {
  for (const e of live) { if (!document.body.contains(e.el)) { e.chart.dispose(); live.delete(e); } }
}

export function rethemeAll() {
  const t = theme();
  for (const e of live) {
    if (!document.body.contains(e.el)) { e.chart.dispose(); live.delete(e); continue; }
    e.chart.setOption(e.buildOption(t), true);
  }
}

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => live.forEach((e) => e.chart.resize()), 120);
});
