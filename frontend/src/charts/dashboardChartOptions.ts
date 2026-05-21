import * as echarts from 'echarts'

export function buildExactMatchLineOption(models: string[], exactMatchData: number[]) {
  return {
    backgroundColor: '#FFFFFF',
    title: {
      text: 'Exact Match Rate Across Different Models',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 21,
        fontWeight: 'bold',
        color: '#2C3E50',
        fontFamily: 'Arial, sans-serif'
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#6BAED6',
      borderWidth: 1,
      textStyle: { color: '#2C3E50', fontSize: 17 },
      axisPointer: {
        type: 'line',
        lineStyle: { color: '#6BAED6', width: 1.5, type: 'dashed' }
      },
      formatter: (params: { name: string; value: number }[]) =>
        `<div style="padding: 4px;"><strong>${params[0].name}</strong><br/>Exact Match: <span style="color: #6BAED6; font-weight: bold;">${params[0].value}%</span></div>`
    },
    grid: { left: '15%', right: '8%', top: '18%', bottom: '38%', containLabel: false },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: models,
      name: 'Model',
      nameLocation: 'middle',
      nameGap: 92,
      nameTextStyle: { fontSize: 18, fontWeight: 'bold', color: '#2C3E50', fontFamily: 'Arial, sans-serif' },
      axisLine: { lineStyle: { color: '#333333', width: 1.5 } },
      axisTick: { show: true, lineStyle: { color: '#333333', width: 1.5 } },
      axisLabel: {
        rotate: 20,
        interval: 0,
        fontSize: 16,
        color: '#2C3E50',
        fontFamily: 'Arial, sans-serif',
        margin: 12
      },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: 'Exact Match (%)',
      min: 0,
      max: 100,
      nameLocation: 'middle',
      nameGap: 55,
      nameTextStyle: { fontSize: 18, fontWeight: 'bold', color: '#2C3E50', fontFamily: 'Arial, sans-serif' },
      axisLine: { lineStyle: { color: '#333333', width: 1.5 } },
      axisTick: { show: true, lineStyle: { color: '#333333', width: 1.5 } },
      axisLabel: { fontSize: 16, color: '#2C3E50', fontFamily: 'Arial, sans-serif' },
      splitLine: { show: true, lineStyle: { color: '#E5E5E5', width: 0.7, type: 'solid' } }
    },
    series: [
      {
        name: 'Exact Match',
        type: 'line',
        smooth: true,
        data: exactMatchData,
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: { color: '#6BAED6', borderColor: '#FFFFFF', borderWidth: 2 },
        lineStyle: { color: '#6BAED6', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(107, 174, 214, 0.35)' },
            { offset: 1, color: 'rgba(107, 174, 214, 0.05)' }
          ])
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}%',
          fontSize: 17,
          color: '#2C3E50',
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif'
        },
        emphasis: {
          itemStyle: { borderWidth: 3, shadowBlur: 10, shadowColor: 'rgba(107, 174, 214, 0.5)' },
          lineStyle: { width: 3 }
        }
      }
    ]
  }
}

export function buildRmseBarOption(models: string[], rmseData: number[]) {
  return {
    backgroundColor: '#FFFFFF',
    title: {
      text: 'RMSE Comparison Across Different Models',
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 21,
        fontWeight: 'bold',
        color: '#2C3E50',
        fontFamily: 'Arial, sans-serif'
      }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#FC8D62',
      borderWidth: 1,
      textStyle: { color: '#2C3E50', fontSize: 17 },
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(252, 141, 98, 0.1)' } },
      formatter: (params: { name: string; value: number }[]) =>
        `<div style="padding: 4px;"><strong>${params[0].name}</strong><br/>RMSE: <span style="color: #FC8D62; font-weight: bold;">${params[0].value.toFixed(4)}</span></div>`
    },
    grid: { left: '15%', right: '8%', top: '18%', bottom: '38%', containLabel: false },
    xAxis: {
      type: 'category',
      data: models,
      name: 'Model',
      nameLocation: 'middle',
      nameGap: 92,
      nameTextStyle: { fontSize: 18, fontWeight: 'bold', color: '#2C3E50', fontFamily: 'Arial, sans-serif' },
      axisLine: { lineStyle: { color: '#333333', width: 1.5 } },
      axisTick: { show: true, lineStyle: { color: '#333333', width: 1.5 } },
      axisLabel: {
        rotate: 20,
        interval: 0,
        fontSize: 16,
        color: '#2C3E50',
        fontFamily: 'Arial, sans-serif',
        margin: 12
      },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: 'RMSE',
      min: 0,
      nameLocation: 'middle',
      nameGap: 55,
      nameTextStyle: { fontSize: 18, fontWeight: 'bold', color: '#2C3E50', fontFamily: 'Arial, sans-serif' },
      axisLine: { lineStyle: { color: '#333333', width: 1.5 } },
      axisTick: { show: true, lineStyle: { color: '#333333', width: 1.5 } },
      axisLabel: { fontSize: 16, color: '#2C3E50', fontFamily: 'Arial, sans-serif' },
      splitLine: { show: true, lineStyle: { color: '#E5E5E5', width: 0.7, type: 'solid' } }
    },
    series: [
      {
        name: 'RMSE',
        type: 'bar',
        barWidth: '50%',
        data: rmseData,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#FC8D62' },
            { offset: 0.5, color: '#FD9E7A' },
            { offset: 1, color: '#FEB896' }
          ]),
          borderRadius: [4, 4, 0, 0],
          borderColor: '#FFFFFF',
          borderWidth: 1
        },
        label: {
          show: true,
          position: 'top',
          formatter: (params: { value: number }) => params.value.toFixed(3),
          fontSize: 17,
          color: '#2C3E50',
          fontWeight: 'bold',
          fontFamily: 'Arial, sans-serif'
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(252, 141, 98, 0.5)', borderWidth: 2 }
        }
      }
    ]
  }
}

