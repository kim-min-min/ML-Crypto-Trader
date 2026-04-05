import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Activity, TrendingUp, Wallet, Zap, BarChart3, Radio } from 'lucide-react';
import { createChart, CandlestickSeries } from 'lightweight-charts';

const API_BASE = "/api";
const BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/linear";

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  const chartContainerRef = useRef();
  const chartInstance = useRef(null);
  const candleSeries = useRef(null);

  // 1. 백엔드 대시보드 데이터 수신
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get(`${API_BASE}/dashboard`);
        setData(response.data);
        setLoading(false);
      } catch (error) {
        console.error("데이터 로드 실패:", error);
      }
    };
    const interval = setInterval(fetchData, 2000);
    fetchData();
    return () => clearInterval(interval);
  }, []);

  // 2. 차트 초기화 및 5분봉 데이터 연동
  useEffect(() => {
    if (!loading && chartContainerRef.current) {
      chartContainerRef.current.innerHTML = '';
      
      const chart = createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 380,
        layout: { background: { color: '#0d0d0d' }, textColor: '#00f2ff' },
        grid: {
          vertLines: { color: 'rgba(42, 46, 57, 0.1)' },
          horzLines: { color: 'rgba(42, 46, 57, 0.1)' },
        },
        timeScale: { borderColor: '#333', timeVisible: true },
      });

      const series = chart.addSeries(CandlestickSeries, {
        upColor: '#00ffaa',
        downColor: '#ff0055',
        borderVisible: false,
        wickUpColor: '#00ffaa',
        wickDownColor: '#ff0055',
      });

      chartInstance.current = chart;
      candleSeries.current = series;

      // 💡 [변경점] 5분봉 과거 데이터 100개 로드
      const fetchHistoricalData = async () => {
        try {
          const res = await axios.get('https://api.bybit.com/v5/market/kline', {
            params: {
              category: 'linear',
              symbol: 'BTCUSDT',
              interval: '5',  // 👈 5분봉 설정
              limit: 200      // 👈 과거 캔들 100개 설정
            }
          });
          
          const historicalData = res.data.result.list.map(item => ({
            time: parseInt(item[0]) / 1000,
            open: parseFloat(item[1]),
            high: parseFloat(item[2]),
            low: parseFloat(item[3]),
            close: parseFloat(item[4]),
          })).reverse();

          candleSeries.current.setData(historicalData);
        } catch (err) {
          console.error("과거 차트 로드 에러:", err);
        }
      };

      fetchHistoricalData().then(() => {
        const ws = new WebSocket(BYBIT_WS_URL);

        ws.onopen = () => {
          // 💡 [변경점] 5분봉 웹소켓 구독 (kline.5)
          ws.send(JSON.stringify({ 
            "op": "subscribe", 
            "args": ["kline.5.BTCUSDT"] 
          }));
        };

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          // 5분봉 데이터 업데이트 확인
          if (msg.topic && msg.topic.startsWith('kline.5')) {
            const candle = msg.data[0];
            if (candleSeries.current) {
              candleSeries.current.update({
                time: parseInt(candle.start) / 1000,
                open: parseFloat(candle.open),
                high: parseFloat(candle.high),
                low: parseFloat(candle.low),
                close: parseFloat(candle.close),
              });
            }
          }
        };
        chartInstance.current.ws = ws; 
      });

      const handleResize = () => {
        if (chartInstance.current) {
          chartInstance.current.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
      };
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        if (chartInstance.current) {
          if (chartInstance.current.ws) chartInstance.current.ws.close();
          chartInstance.current.remove();
          chartInstance.current = null;
        }
      };
    }
  }, [loading]);

  if (loading) return (
    <div style={{ backgroundColor: '#0a0a0a', height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0ff' }}>
      <div style={{ textAlign: 'center' }}>
        <Zap size={48} style={{ animation: 'pulse 1.5s infinite' }} />
        <p style={{ marginTop: '10px', fontFamily: 'monospace' }}>⚡ ANALYZING 5M CHART DATA...</p>
      </div>
    </div>
  );

  return (
    <div style={{ backgroundColor: '#0a0a0a', color: '#fff', minHeight: '100vh', padding: '20px', fontFamily: 'monospace' }}>
      
      {/* 헤더 */}
      <header style={{ borderBottom: '2px solid #0ff', paddingBottom: '10px', marginBottom: '30px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <h1 style={{ color: '#0ff', display: 'flex', alignItems: 'center', gap: '10px', margin: 0 }}>
            <Zap size={32} /> BIT-TRADER V1.0
          </h1>
          <p style={{ color: '#444', margin: '5px 0 0 0', fontSize: '0.8rem' }}>ENGINE: MAIN_EXECUTION | TIMEFRAME: 5M</p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: '#0f0', display: 'flex', alignItems: 'center', gap: '5px', justifyContent: 'flex-end', fontSize: '0.9rem' }}>
            <Radio size={14} /> LIVE FEED
          </div>
          <p style={{ color: '#666', margin: 0, fontSize: '0.8rem' }}>Last Sync: {data.timestamp}</p>
        </div>
      </header>

      {/* 상태 카드 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
        <div className="card" style={cardStyle}>
          <div style={labelStyle}><Wallet size={18} /> CURRENT BALANCE</div>
          <div style={valueStyle}>$ {data.balance?.toLocaleString()}</div>
        </div>
        <div className="card" style={{ ...cardStyle, borderColor: data.last_pnl >= 0 ? '#0f0' : '#f00' }}>
          <div style={labelStyle}><TrendingUp size={18} /> PROFIT (CURRENT)</div>
          <div style={{ ...valueStyle, color: data.last_pnl >= 0 ? '#0f0' : '#f00' }}>
            {data.last_pnl > 0 ? '+' : ''}{data.last_pnl?.toFixed(2)} %
          </div>
        </div>
        <div className="card" style={cardStyle}>
          <div style={labelStyle}><Activity size={18} /> ACTIVE POSITION</div>
          <div style={{ ...valueStyle, color: data.side === 'IDLE' ? '#444' : '#0ff' }}>
            {data.side}
          </div>
        </div>
      </div>

      {/* 차트 섹션 */}
      <div style={{ marginTop: '30px', border: '1px solid #333', borderRadius: '10px', overflow: 'hidden', background: '#0d0d0d' }}>
        <div style={{ padding: '10px 20px', borderBottom: '1px solid #222', display: 'flex', alignItems: 'center', gap: '10px', color: '#0ff', background: '#111' }}>
          <BarChart3 size={18} /> MARKET_STREAM: BTCUSDT_5M
        </div>
        <div ref={chartContainerRef} style={{ width: '100%', position: 'relative' }} />
      </div>

      {/* AI 예측 */}
      <div style={{ marginTop: '30px', padding: '20px', border: '1px solid #333', borderRadius: '10px', background: '#0d0d0d' }}>
        <h2 style={{ color: '#0ff', fontSize: '1.1rem', marginTop: 0, marginBottom: '20px' }}>🧠 AI ENGINE SIGNALS</h2>
        <div style={{ display: 'flex', gap: '40px' }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem' }}>
              <span>LONG STRENGTH</span>
              <span style={{ color: '#0f0' }}>{(data.pred_long * 100).toFixed(1)}%</span>
            </div>
            <div style={{ height: '8px', backgroundColor: '#222', borderRadius: '4px' }}>
              <div style={{ height: '100%', width: `${data.pred_long * 100}%`, backgroundColor: '#0f0', borderRadius: '4px', boxShadow: '0 0 10px #0f0' }} />
            </div>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.85rem' }}>
              <span>SHORT STRENGTH</span>
              <span style={{ color: '#f00' }}>{(data.pred_short * 100).toFixed(1)}%</span>
            </div>
            <div style={{ height: '8px', backgroundColor: '#222', borderRadius: '4px' }}>
              <div style={{ height: '100%', width: `${data.pred_short * 100}%`, backgroundColor: '#f00', borderRadius: '4px', boxShadow: '0 0 10px #f00' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const cardStyle = { border: '1px solid #333', padding: '20px', borderRadius: '10px', background: '#111' };
const labelStyle = { fontSize: '0.75rem', color: '#666', display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' };
const valueStyle = { fontSize: '1.8rem', fontWeight: 'bold' };

export default App;