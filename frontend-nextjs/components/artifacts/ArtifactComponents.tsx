'use client'

/**
 * ============================================================
 * 🎨 ARTIFACT COMPONENTS - Generative UI
 * ============================================================
 * 
 * These components render structured JSON artifacts streamed
 * from the AI agent as rich, interactive UI elements.
 * 
 * Supported Types:
 * - LineChart: Time series (stock prices, trends)
 * - BarChart: Category comparisons
 * - DataTable: Structured data
 * - StockCard: Rich stock info cards
 * - MetricCard: Single metric highlights
 */

import React from 'react'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { TrendingUp, TrendingDown, Minus, Activity, DollarSign, BarChart3 } from 'lucide-react'

// ============================================================
// TYPE DEFINITIONS (matching Python backend)
// ============================================================

interface ChartDataPoint {
  name: string
  value: number
  value2?: number
  label?: string
  color?: string
}

interface LineChartArtifact {
  type: 'line_chart'
  title: string
  data: ChartDataPoint[]
  x_axis_label?: string
  y_axis_label?: string
  series_names?: string[]
  show_grid?: boolean
  colors?: string[]
}

interface BarChartArtifact {
  type: 'bar_chart'
  title: string
  data: ChartDataPoint[]
  x_axis_label?: string
  y_axis_label?: string
  horizontal?: boolean
  colors?: string[]
}

interface AreaChartArtifact {
  type: 'area_chart'
  title: string
  data: ChartDataPoint[]
  x_axis_label?: string
  y_axis_label?: string
  fill_opacity?: number
}

interface PieChartArtifact {
  type: 'pie_chart'
  title: string
  data: ChartDataPoint[]
  show_legend?: boolean
  inner_radius?: number
}

interface TableColumn {
  key: string
  label: string
  align?: 'left' | 'center' | 'right'
  format?: 'text' | 'number' | 'currency' | 'percent' | 'date'
}

interface DataTableArtifact {
  type: 'data_table'
  title: string
  columns: TableColumn[]
  rows: Record<string, any>[]
  sortable?: boolean
}

interface StockMetric {
  label: string
  value: string
  change?: string
  change_type?: 'positive' | 'negative' | 'neutral'
}

interface StockCardArtifact {
  type: 'stock_card'
  symbol: string
  company_name: string
  current_price: number
  price_change: number
  price_change_percent: number
  metrics: StockMetric[]
  sparkline_data?: number[]
}

interface MetricCardArtifact {
  type: 'metric_card'
  title: string
  value: string
  subtitle?: string
  change?: string
  change_type?: 'positive' | 'negative' | 'neutral'
  icon?: string
}

interface TextArtifact {
  type: 'text'
  content: string
}

export type UIArtifact =
  | LineChartArtifact
  | BarChartArtifact
  | AreaChartArtifact
  | PieChartArtifact
  | DataTableArtifact
  | StockCardArtifact
  | MetricCardArtifact
  | TextArtifact

// Default colors for charts
const DEFAULT_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']

// ============================================================
// 📈 LINE CHART COMPONENT
// ============================================================

export function LineChartComponent({ artifact }: { artifact: LineChartArtifact }) {
  const colors = artifact.colors || DEFAULT_COLORS
  const hasSecondSeries = artifact.data.some(d => d.value2 !== undefined)
  
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4">
      <h3 className="text-lg font-semibold text-white mb-4">{artifact.title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={artifact.data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          {artifact.show_grid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#374151" />}
          <XAxis 
            dataKey="name" 
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            label={artifact.x_axis_label ? { value: artifact.x_axis_label, position: 'insideBottom', offset: -5, fill: '#9CA3AF' } : undefined}
          />
          <YAxis 
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
            label={artifact.y_axis_label ? { value: artifact.y_axis_label, angle: -90, position: 'insideLeft', fill: '#9CA3AF' } : undefined}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
            labelStyle={{ color: '#F3F4F6' }}
            itemStyle={{ color: '#F3F4F6' }}
          />
          {hasSecondSeries && artifact.series_names && (
            <Legend wrapperStyle={{ color: '#F3F4F6' }} />
          )}
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke={colors[0]} 
            strokeWidth={2}
            dot={false}
            name={artifact.series_names?.[0] || 'Value'}
          />
          {hasSecondSeries && (
            <Line 
              type="monotone" 
              dataKey="value2" 
              stroke={colors[1]} 
              strokeWidth={2}
              dot={false}
              name={artifact.series_names?.[1] || 'Value 2'}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ============================================================
// 📊 BAR CHART COMPONENT
// ============================================================

export function BarChartComponent({ artifact }: { artifact: BarChartArtifact }) {
  const colors = artifact.colors || DEFAULT_COLORS
  
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4">
      <h3 className="text-lg font-semibold text-white mb-4">{artifact.title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart 
          data={artifact.data} 
          layout={artifact.horizontal ? 'vertical' : 'horizontal'}
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis 
            type={artifact.horizontal ? 'number' : 'category'}
            dataKey={artifact.horizontal ? undefined : 'name'}
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
          />
          <YAxis 
            type={artifact.horizontal ? 'category' : 'number'}
            dataKey={artifact.horizontal ? 'name' : undefined}
            stroke="#9CA3AF"
            tick={{ fill: '#9CA3AF', fontSize: 12 }}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
            labelStyle={{ color: '#F3F4F6' }}
            itemStyle={{ color: '#F3F4F6' }}
          />
          <Bar dataKey="value" fill={colors[0]} radius={[4, 4, 0, 0]}>
            {artifact.data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ============================================================
// 📈 AREA CHART COMPONENT
// ============================================================

export function AreaChartComponent({ artifact }: { artifact: AreaChartArtifact }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4">
      <h3 className="text-lg font-semibold text-white mb-4">{artifact.title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={artifact.data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="name" stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
          <YAxis stroke="#9CA3AF" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
            labelStyle={{ color: '#F3F4F6' }}
          />
          <Area 
            type="monotone" 
            dataKey="value" 
            stroke="#3B82F6" 
            fill="#3B82F6" 
            fillOpacity={artifact.fill_opacity || 0.3}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ============================================================
// 🥧 PIE CHART COMPONENT
// ============================================================

export function PieChartComponent({ artifact }: { artifact: PieChartArtifact }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4">
      <h3 className="text-lg font-semibold text-white mb-4">{artifact.title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={artifact.data}
            cx="50%"
            cy="50%"
            innerRadius={artifact.inner_radius || 0}
            outerRadius={100}
            dataKey="value"
            nameKey="name"
            label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          >
            {artifact.data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={DEFAULT_COLORS[index % DEFAULT_COLORS.length]} />
            ))}
          </Pie>
          {artifact.show_legend !== false && (
            <Legend wrapperStyle={{ color: '#F3F4F6' }} />
          )}
          <Tooltip 
            contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
            labelStyle={{ color: '#F3F4F6' }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

// ============================================================
// 📋 DATA TABLE COMPONENT
// ============================================================

export function DataTableComponent({ artifact }: { artifact: DataTableArtifact }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4 overflow-x-auto">
      <h3 className="text-lg font-semibold text-white mb-4">{artifact.title}</h3>
      <table className="min-w-full divide-y divide-gray-700">
        <thead>
          <tr>
            {artifact.columns.map((column) => (
              <th
                key={column.key}
                className={`px-4 py-3 text-${column.align || 'left'} text-xs font-medium text-gray-400 uppercase tracking-wider`}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700">
          {artifact.rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="hover:bg-gray-700/50 transition-colors">
              {artifact.columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-4 py-3 text-${column.align || 'left'} text-sm text-gray-300 whitespace-nowrap`}
                >
                  {row[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ============================================================
// 💹 STOCK CARD COMPONENT
// ============================================================

export function StockCardComponent({ artifact }: { artifact: StockCardArtifact }) {
  const isPositive = artifact.price_change >= 0
  const TrendIcon = isPositive ? TrendingUp : TrendingDown
  const trendColor = isPositive ? 'text-green-400' : 'text-red-400'
  const bgGradient = isPositive 
    ? 'from-green-900/30 to-gray-800' 
    : 'from-red-900/30 to-gray-800'
  
  return (
    <div className={`bg-gradient-to-r ${bgGradient} rounded-lg p-5 mb-4 border border-gray-700`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-white">{artifact.symbol}</span>
            <span className={`flex items-center gap-1 text-sm ${trendColor}`}>
              <TrendIcon className="w-4 h-4" />
              {artifact.price_change >= 0 ? '+' : ''}{artifact.price_change.toFixed(2)} ({artifact.price_change_percent.toFixed(2)}%)
            </span>
          </div>
          <p className="text-gray-400 text-sm">{artifact.company_name}</p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-bold text-white">${artifact.current_price.toFixed(2)}</p>
          <p className="text-gray-400 text-xs">Current Price</p>
        </div>
      </div>
      
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
        {artifact.metrics.map((metric, index) => (
          <div key={index} className="bg-gray-900/50 rounded-lg p-3">
            <p className="text-gray-400 text-xs">{metric.label}</p>
            <p className="text-white font-semibold">{metric.value}</p>
            {metric.change && (
              <p className={`text-xs ${
                metric.change_type === 'positive' ? 'text-green-400' :
                metric.change_type === 'negative' ? 'text-red-400' : 'text-gray-400'
              }`}>
                {metric.change}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// ============================================================
// 📊 METRIC CARD COMPONENT
// ============================================================

export function MetricCardComponent({ artifact }: { artifact: MetricCardArtifact }) {
  const IconComponent = {
    'trending-up': TrendingUp,
    'trending-down': TrendingDown,
    'dollar': DollarSign,
    'chart': BarChart3,
    'activity': Activity,
  }[artifact.icon || 'activity'] || Activity
  
  const changeColor = {
    positive: 'text-green-400',
    negative: 'text-red-400',
    neutral: 'text-gray-400'
  }[artifact.change_type || 'neutral']
  
  return (
    <div className="bg-gray-800 rounded-lg p-4 mb-4 border border-gray-700">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-400 text-sm">{artifact.title}</p>
          <p className="text-2xl font-bold text-white mt-1">{artifact.value}</p>
          {artifact.subtitle && (
            <p className="text-gray-500 text-xs mt-1">{artifact.subtitle}</p>
          )}
          {artifact.change && (
            <p className={`text-sm mt-1 ${changeColor}`}>{artifact.change}</p>
          )}
        </div>
        <div className="bg-blue-500/20 p-3 rounded-lg">
          <IconComponent className="w-6 h-6 text-blue-400" />
        </div>
      </div>
    </div>
  )
}

// ============================================================
// 📝 TEXT COMPONENT
// ============================================================

export function TextComponent({ artifact }: { artifact: TextArtifact }) {
  return (
    <div className="prose prose-invert max-w-none">
      <div className="text-gray-200 whitespace-pre-wrap">
        {artifact.content}
      </div>
    </div>
  )
}

// ============================================================
// 🎯 ARTIFACT RENDERER - Main Dispatcher
// ============================================================

export function ArtifactRenderer({ artifact }: { artifact: UIArtifact }) {
  switch (artifact.type) {
    case 'line_chart':
      return <LineChartComponent artifact={artifact} />
    case 'bar_chart':
      return <BarChartComponent artifact={artifact} />
    case 'area_chart':
      return <AreaChartComponent artifact={artifact} />
    case 'pie_chart':
      return <PieChartComponent artifact={artifact} />
    case 'data_table':
      return <DataTableComponent artifact={artifact} />
    case 'stock_card':
      return <StockCardComponent artifact={artifact} />
    case 'metric_card':
      return <MetricCardComponent artifact={artifact} />
    case 'text':
      return <TextComponent artifact={artifact} />
    default:
      console.warn('Unknown artifact type:', (artifact as any).type)
      return null
  }
}

export default ArtifactRenderer
