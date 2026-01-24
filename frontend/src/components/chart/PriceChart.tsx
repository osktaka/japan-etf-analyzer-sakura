/** Price chart component */
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { ChartDataPoint } from '../../api';
import { formatPrice } from '../../utils';
import styles from './PriceChart.module.css';

interface PriceChartProps {
  data: ChartDataPoint[];
  height?: number;
}

export function PriceChart({ data, height = 300 }: PriceChartProps) {
  if (data.length === 0) {
    return (
      <div className={styles.empty}>
        <p>チャートデータがありません</p>
      </div>
    );
  }

  return (
    <div className={styles.container} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => {
              const date = new Date(value);
              return `${date.getMonth() + 1}/${date.getDate()}`;
            }}
          />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(value) => formatPrice(value).replace('¥', '')}
            domain={['auto', 'auto']}
          />
          <Tooltip
            formatter={(value: number) => [formatPrice(value), '終値']}
            labelFormatter={(label) => label}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#2563eb"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
