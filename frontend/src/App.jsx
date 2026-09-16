import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Activity,
  ArrowLeftRight,
  Bot,
  Boxes,
  CircleStop,
  Factory,
  Gauge,
  House,
  LayoutDashboard,
  LoaderCircle,
  MessageCircle,
  PackageOpen,
  Play,
  RefreshCw,
  RotateCcw,
  RotateCw,
  Settings2,
  SendHorizontal,
  SlidersHorizontal,
  Truck,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';

const DEVICE_DEFS = {
  conveyor: {
    id: 'conveyor',
    name: '기본 컨베이어',
    ip: '172.20.10.14',
    kind: 'conveyor',
    capabilities: { speed: true, direction: true, color: false, agv: false },
  },
  feeder: {
    id: 'feeder',
    name: '피더',
    ip: '10.34.129.112',
    kind: 'feeder',
    capabilities: { speed: true, direction: true, color: false, agv: false },
  },
  colorSorter: {
    id: 'colorSorter',
    name: '색상분류 컨베이어',
    ip: '10.34.129.108',
    kind: 'sorter',
    capabilities: { speed: true, direction: true, color: true, agv: false },
  },
  agv: {
    id: 'agv',
    name: 'AGV',
    ip: '',
    kind: 'agv',
    capabilities: { speed: true, direction: false, color: false, agv: true },
  },
};

function blankState(device) {
  return {
    connected: false,
    running: false,
    speed: 50,
    direction: 'FORWARD',
    color: 'RED',
    agvState: 'IDLE',
  };
}

function endpoint(device, path) {
  if (!device.ip) {
    throw new Error(`${device.name} IP가 설정되지 않았습니다.`);
  }

  return `http://${device.ip}${path}`;
}

function normalizeDeviceIp(value) {
  return value.trim().replace(/^https?:\/\//, '').replace(/\/$/, '');
}

function loadDeviceIps() {
  try {
    const saved = JSON.parse(window.localStorage.getItem('manufacturing-device-ips') || '{}');
    return Object.fromEntries(Object.entries(DEVICE_DEFS).map(([id, device]) => [
      id,
      { ...device, ip: typeof saved[id] === 'string' ? saved[id] : device.ip },
    ]));
  } catch {
    return DEVICE_DEFS;
  }
}

async function request(device, path) {
  const res = await fetch(endpoint(device, path), {
    method: 'GET',
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res;
}

async function statusRequest(device, timeoutMs = 3000) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(endpoint(device, '/status'), {
      method: 'GET',
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res;
  } finally {
    window.clearTimeout(timeout);
  }
}

function formatTime(date = new Date()) {
  return date.toLocaleTimeString('ko-KR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function ConnectionBadge({ connected, configured = true }) {
  if (!configured) {
    return (
      <span className="connection warn">
        <WifiOff size={15} />
        IP 미설정
      </span>
    );
  }

  return (
    <span className={`connection ${connected ? 'ok' : 'bad'}`}>
      {connected ? <Wifi size={15} /> : <WifiOff size={15} />}
      {connected ? '연결됨' : '미확인'}
    </span>
  );
}

const INITIAL_CHAT = [
  {
    id: 'welcome',
    role: 'bot',
    text: '안녕하세요. 공정 현황, 설비 제어 방법, AGV 설정을 도와드릴게요.',
    time: '지금',
  },
];

function findTargetDevice(text) {
  const normalized = text.toLowerCase();
  if (normalized.includes('agv')) return 'agv';
  if (text.includes('색상') || text.includes('분류')) return 'colorSorter';
  if (text.includes('피더') || normalized.includes('feeder')) return 'feeder';
  if (text.includes('컨베이어') || normalized.includes('conveyor')) return 'conveyor';
  return null;
}

function parseControlRequest(text) {
  const deviceId = findTargetDevice(text);
  if (!deviceId) return null;
  const normalized = text.toLowerCase();
  const speedMatch = text.match(/속도\s*(?:를|을)?\s*(\d{1,3})|speed\s*(?:to)?\s*(\d{1,3})/i);
  if (speedMatch) {
    const speed = Number(speedMatch[1] || speedMatch[2]);
    if (Number.isInteger(speed) && speed >= 0 && speed <= 255) {
      return { deviceId, command: 'SET_SPEED', payload: { speed }, description: `속도를 ${speed}으로 변경` };
    }
  }

  if (/비상\s*정지|emergency\s*stop/i.test(text)) {
    return { deviceId, command: 'EMERGENCY_STOP', payload: {}, description: '비상 정지' };
  }
  if (/복귀|return/i.test(text)) {
    return { deviceId, command: 'RETURN_HOME', payload: {}, description: '복귀' };
  }
  if (/적재함|box|적재|하역/i.test(text)) {
    return { deviceId, command: 'BOX_ACTION', payload: {}, description: '적재함 동작' };
  }
  if (/정방향|전진|forward/i.test(text)) {
    return { deviceId, command: 'FORWARD', payload: {}, description: '정방향 가동' };
  }
  if (/역방향|후진|reverse/i.test(text)) {
    return { deviceId, command: 'REVERSE', payload: {}, description: '역방향 가동' };
  }
  if (/시작|가동|start/i.test(text)) {
    return { deviceId, command: 'START', payload: {}, description: '가동 시작' };
  }
  if (/정지|stop/i.test(text)) {
    return { deviceId, command: 'STOP', payload: {}, description: '정지' };
  }

  const color = /빨강|red/i.test(text) ? 'RED'
    : /파랑|blue/i.test(text) ? 'BLUE'
      : /초록|green/i.test(text) ? 'GREEN' : null;
  if (color && (text.includes('색상') || text.includes('컬러') || normalized.includes('color'))) {
    return { deviceId, command: 'SET_COLOR', payload: { color }, description: `인식 색상을 ${color}(으)로 변경` };
  }

  return null;
}

function Chatbot({ devices, states }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [pendingAction, setPendingAction] = useState(null);
  const [chatError, setChatError] = useState('');
  const [messages, setMessages] = useState(() => {
    try {
      const saved = window.localStorage.getItem('manufacturing-chat-history');
      return saved ? JSON.parse(saved) : INITIAL_CHAT;
    } catch {
      return INITIAL_CHAT;
    }
  });
  const messageEndRef = useRef(null);

  const appendBotMessage = (text, action = null) => {
    setMessages((prev) => [...prev, { id: `bot-${Date.now()}`, role: 'bot', text, time: formatTime(), action }]);
  };

  const recordClientEvent = async (interactionType, message) => {
    try {
      await fetch(import.meta.env.VITE_AGENT_EVENT_ENDPOINT || '/planner-api/api/agent/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interaction_type: interactionType, message }),
      });
    } catch {
      // Audit logging must never block an operator from cancelling a command.
    }
  };

  useEffect(() => {
    window.localStorage.setItem('manufacturing-chat-history', JSON.stringify(messages));
    if (open) messageEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, open]);

  const sendMessage = async () => {
    const text = draft.trim();
    if (!text || isSending) return;
    const now = formatTime();
    const userMessage = { id: `user-${Date.now()}`, role: 'user', text, time: now };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setDraft('');
    setChatError('');

    const controlRequest = parseControlRequest(text);
    if (controlRequest) {
      const device = devices[controlRequest.deviceId];
      const action = { ...controlRequest, id: `action-${Date.now()}`, sourceText: text };
      setPendingAction(action);
      appendBotMessage(`${device.name}(장비 ID: ${device.id})의 ${action.description} 작업을 실행할까요?`, action);
      void recordClientEvent('CONTROL_CONFIRMATION_REQUESTED', text);
      return;
    }

    setIsSending(true);

    try {
      const endpoint = import.meta.env.VITE_AGENT_READ_ENDPOINT;
      if (!endpoint) throw new Error('AGENT_READ_ENDPOINT_MISSING');

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      if (!response.ok) throw new Error(`HTTP_${response.status}`);
      const data = await response.json();
      const answer = data.answer;
      if (!answer || typeof answer !== 'string') throw new Error('INVALID_LLM_RESPONSE');
      appendBotMessage(answer);
    } catch (error) {
      setChatError(
        error.message === 'AGENT_READ_ENDPOINT_MISSING'
          ? '읽기 API가 연결되지 않았습니다. .env의 VITE_AGENT_READ_ENDPOINT를 설정해 주세요.'
          : 'Planner에서 LLM 응답을 가져오지 못했습니다. Planner API와 OpenAI 설정을 확인해 주세요.'
      );
    } finally {
      setIsSending(false);
    }
  };

  const resolvePendingAction = async (action, confirmed) => {
    if (!pendingAction || pendingAction.id !== action.id) return;

    setChatError('');
    setPendingAction(null);
    if (!confirmed) {
      appendBotMessage(`${devices[action.deviceId].name} ${action.description} 작업을 취소했습니다.`);
      void recordClientEvent('CONTROL_CANCELLED', action.sourceText);
      return;
    }

    setIsSending(true);
    try {
      const endpoint = import.meta.env.VITE_AGENT_CONTROL_ENDPOINT;
      if (!endpoint) throw new Error('AGENT_CONTROL_ENDPOINT_MISSING');

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: action.sourceText, confirmed: true }),
      });
      if (!response.ok) throw new Error(`HTTP_${response.status}`);

      const data = await response.json();
      const answer = data.answer || `${devices[action.deviceId].name} 속도를 ${action.speed}으로 변경했습니다.`;
      appendBotMessage(answer);
    } catch (error) {
      setChatError(error.message === 'AGENT_CONTROL_ENDPOINT_MISSING'
        ? '제어 API가 연결되지 않았습니다. VITE_AGENT_CONTROL_ENDPOINT를 설정해 주세요.'
        : '제어 명령을 전송하지 못했습니다. Planner API와 AGV 연결 상태를 확인해 주세요.');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <>
      {open && (
        <aside className="chat-panel" aria-label="공정 도우미 챗봇">
          <div className="chat-head">
            <div className="chat-avatar"><Bot size={19} /></div>
            <div>
            <strong>AI 공정 어시스턴트</strong>
              <span><i /> LLM 연결 대기</span>
            </div>
            <button className="chat-close" onClick={() => setOpen(false)} aria-label="챗봇 닫기"><X size={19} /></button>
          </div>
          <div className="chat-context">
            <span>실시간 공정 컨텍스트</span>
            <strong>{Object.values(states).filter((state) => state.running).length}대 가동 중</strong>
          </div>
          <div className="chat-messages">
            {messages.map((message) => (
              <div className={`chat-message ${message.role}`} key={message.id}>
                {message.role === 'bot' && <Bot size={15} />}
                <div>
                  <p>{message.text}</p>
                  {message.action && pendingAction?.id === message.action.id && (
                    <div className="chat-confirm-actions">
                      <button type="button" disabled={isSending} onClick={() => resolvePendingAction(message.action, true)}>확인</button>
                      <button type="button" disabled={isSending} className="cancel" onClick={() => resolvePendingAction(message.action, false)}>취소</button>
                    </div>
                  )}
                  <time>{message.time}</time>
                </div>
              </div>
            ))}
            <div ref={messageEndRef} />
          </div>
          {chatError && <p className="chat-error">{chatError}</p>}
          <div className="chat-suggestions">
            <button onClick={() => setDraft('현재 설비 현황 알려줘')}>설비 현황</button>
            <button onClick={() => setDraft('AGV 설정 방법 알려줘')}>AGV 설정</button>
          </div>
          <form className="chat-composer" onSubmit={(event) => { event.preventDefault(); sendMessage(); }}>
            <input value={draft} disabled={isSending} onChange={(event) => setDraft(event.target.value)} placeholder="공정에 대해 물어보세요" aria-label="챗봇 메시지" />
            <button type="submit" disabled={isSending} aria-label="메시지 전송">{isSending ? <LoaderCircle className="spin" size={18} /> : <SendHorizontal size={18} />}</button>
          </form>
        </aside>
      )}
      <button className={`chat-launcher ${open ? 'is-open' : ''}`} onClick={() => setOpen((value) => !value)} aria-label={open ? '챗봇 닫기' : '챗봇 열기'}>
        {open ? <X size={22} /> : <MessageCircle size={22} />}
        <span>{open ? '닫기' : '챗봇'}</span>
      </button>
    </>
  );
}

function DeviceCard({ device, state, onState, onLog }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const speedTimer = useRef(null);

  useEffect(() => {
    return () => {
      if (speedTimer.current) {
        clearTimeout(speedTimer.current);
      }
    };
  }, []);

  const run = async (path, patch = {}, label = path) => {
    if (!device.ip) {
      setError('AGV IP를 상단 설정에서 입력하세요.');
      return;
    }

    setBusy(true);
    setError('');

    try {
      await request(device, path);

      onState(device.id, {
        ...patch,
        connected: true,
      });

      onLog(device.name, `${label} 성공`, 'success');
    } catch (e) {
      onState(device.id, {
        connected: false,
      });

      setError(
        e.message.includes('IP')
          ? e.message
          : 'ESP와 통신할 수 없습니다. 같은 Wi-Fi인지 확인하세요.'
      );

      onLog(device.name, `${label} 실패`, 'error');
    } finally {
      setBusy(false);
    }
  };

  const changeSpeed = (value) => {
    const n = Number(value);

    onState(device.id, {
      speed: n,
    });

    if (speedTimer.current) {
      clearTimeout(speedTimer.current);
    }

    speedTimer.current = setTimeout(() => {
      run(`/speed?value=${n}`, { speed: n }, `속도 ${n}`);
    }, 180);
  };

  return (
    <section className="device-card">
      <div className="device-head">
        <div>
          <div className="device-title-row">
            {device.kind === 'agv' ? (
              <Truck size={20} />
            ) : (
              <Factory size={20} />
            )}

            <h2>{device.name}</h2>
          </div>

          <p className="ip">
            {device.ip
              ? `http://${device.ip}/`
              : 'AGV IP 설정 필요'}
          </p>
        </div>

        <ConnectionBadge
          connected={state.connected}
          configured={Boolean(device.ip)}
        />
      </div>

      {device.capabilities.agv ? (
        <>
          <div className="button-grid two">
            <button
              className="primary"
              disabled={busy || !device.ip}
              onClick={() =>
                run(
                  '/start',
                  {
                    running: true,
                    agvState: 'MISSION',
                  },
                  'AGV 작업 시작'
                )
              }
            >
              <Play size={18} />
              작업 시작
            </button>

            <button
              className="danger"
              disabled={busy || !device.ip}
              onClick={() =>
                run(
                  '/stop',
                  {
                    running: false,
                    agvState: 'STOPPED',
                  },
                  'AGV 정지'
                )
              }
            >
              <CircleStop size={18} />
              STOP
            </button>

            <button
              disabled={busy || !device.ip}
              onClick={() =>
                run(
                  '/return',
                  {
                    running: true,
                    agvState: 'RETURNING',
                  },
                  'AGV 복귀'
                )
              }
            >
              <House size={18} />
              복귀
            </button>

            <button
              disabled={busy || !device.ip}
              onClick={() =>
                run(
                  '/box',
                  {},
                  '적재함 동작'
                )
              }
            >
              <PackageOpen size={18} />
              적재함
            </button>
          </div>

          <div className="control-block">
            <div className="control-label">
              <Gauge size={17} />
              주행 속도
              <strong>{state.speed}</strong>
            </div>

            <input
              aria-label="AGV 속도"
              type="range"
              min="1"
              max="100"
              value={state.speed}
              disabled={!device.ip}
              onChange={(e) =>
                changeSpeed(e.target.value)
              }
            />
          </div>

          <div className="device-state">
            <span
              className={`dot ${
                state.running ? 'running' : ''
              }`}
            />

            {state.agvState === 'RETURNING'
              ? '복귀 중'
              : state.running
                ? '작업 중'
                : '대기/정지'}
          </div>
        </>
      ) : (
        <>
          <div className="button-grid two">
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                run(
                  '/start',
                  { running: true },
                  'START'
                )
              }
            >
              <Play size={18} />
              START
            </button>

            <button
              className="danger"
              disabled={busy}
              onClick={() =>
                run(
                  '/stop',
                  { running: false },
                  'STOP'
                )
              }
            >
              <CircleStop size={18} />
              STOP
            </button>
          </div>

          {device.capabilities.direction && (
            <div className="control-block">
              <div className="control-label">
                <ArrowLeftRight size={17} />
                방향
              </div>

              <div className="button-grid two">
                <button
                  className={
                    state.direction === 'FORWARD'
                      ? 'selected'
                      : ''
                  }
                  disabled={busy}
                  onClick={() =>
                    run(
                      '/forward',
                      {
                        direction: 'FORWARD',
                      },
                      '정방향'
                    )
                  }
                >
                  <RotateCw size={17} />
                  정방향
                </button>

                <button
                  className={
                    state.direction === 'REVERSE'
                      ? 'selected'
                      : ''
                  }
                  disabled={busy}
                  onClick={() =>
                    run(
                      '/reverse',
                      {
                        direction: 'REVERSE',
                      },
                      '역방향'
                    )
                  }
                >
                  <RotateCcw size={17} />
                  역방향
                </button>
              </div>
            </div>
          )}

          {device.capabilities.speed && (
            <div className="control-block">
              <div className="control-label">
                <Gauge size={17} />
                속도
                <strong>{state.speed}</strong>
              </div>

              <input
                aria-label={`${device.name} 속도`}
                type="range"
                min="1"
                max="100"
                value={state.speed}
                onChange={(e) =>
                  changeSpeed(e.target.value)
                }
              />
            </div>
          )}

          {device.capabilities.color && (
            <div className="control-block">
              <div className="control-label">
                <SlidersHorizontal size={17} />
                분류 대상 색상
              </div>

              <div className="button-grid two">
                <button
                  className={
                    state.color === 'RED'
                      ? 'selected'
                      : ''
                  }
                  disabled={busy}
                  onClick={() =>
                    run(
                      '/color?value=RED',
                      {
                        color: 'RED',
                      },
                      '빨간색 분류'
                    )
                  }
                >
                  RED
                </button>

                <button
                  className={
                    state.color === 'BLUE'
                      ? 'selected'
                      : ''
                  }
                  disabled={busy}
                  onClick={() =>
                    run(
                      '/color?value=BLUE',
                      {
                        color: 'BLUE',
                      },
                      '파란색 분류'
                    )
                  }
                >
                  BLUE
                </button>
              </div>
            </div>
          )}

          <div className="device-state">
            <span
              className={`dot ${
                state.running ? 'running' : ''
              }`}
            />

            {state.running ? '가동 중' : '정지'}

            <span className="divider">·</span>

            {state.direction === 'FORWARD'
              ? '정방향'
              : '역방향'}
          </div>
        </>
      )}

      {error && (
        <p className="error">
          {error}
        </p>
      )}
    </section>
  );
}

function Dashboard({
  devices,
  states,
  logs,
  onCheckStatus,
}) {
  const entries = Object.values(devices);

  const configured = entries.filter(
    (d) => d.ip
  );

  const connected = configured.filter(
    (d) => states[d.id].connected
  ).length;

  const running = entries.filter(
    (d) => states[d.id].running
  ).length;

  const alerts =
    configured.length - connected;

  return (
    <>
      <section className="metric-grid">
        <article className="metric-card">
          <span className="metric-icon">
            <Boxes size={21} />
          </span>

          <div>
            <span>등록 설비</span>
            <strong>{entries.length}</strong>
            <small>ESP 기반 제어 노드</small>
          </div>
        </article>

        <article className="metric-card">
          <span className="metric-icon">
            <Wifi size={21} />
          </span>

          <div>
            <span>연결 설비</span>
            <strong>
              {connected}/{configured.length}
            </strong>
            <small>
              최근 상태 확인 기준
            </small>
          </div>
        </article>

        <article className="metric-card">
          <span className="metric-icon">
            <Activity size={21} />
          </span>

          <div>
            <span>가동 설비</span>
            <strong>{running}</strong>
            <small>UI 상태 기준</small>
          </div>
        </article>

        <article className="metric-card">
          <span className="metric-icon">
            <WifiOff size={21} />
          </span>

          <div>
            <span>확인 필요</span>
            <strong>{alerts}</strong>
            <small>미응답 또는 미확인</small>
          </div>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>공정 설비 현황</h2>
              <p>
                각 ESP의 연결 및 가동 상태
              </p>
            </div>

            <button onClick={onCheckStatus}>
              <RefreshCw size={17} />
              새로고침
            </button>
          </div>

          <div className="status-list">
            {entries.map((d) => (
              <div
                className="status-row"
                key={d.id}
              >
                <div className="status-name">
                  {d.kind === 'agv' ? (
                    <Truck size={19} />
                  ) : (
                    <Factory size={19} />
                  )}

                  <div>
                    <strong>
                      {d.name}
                    </strong>

                    <span>
                      {d.ip || 'IP 미설정'}
                    </span>
                  </div>
                </div>

                <div className="status-tags">
                  <ConnectionBadge
                    connected={
                      states[d.id].connected
                    }
                    configured={
                      Boolean(d.ip)
                    }
                  />

                  <span
                    className={`run-chip ${
                      states[d.id].running
                        ? 'on'
                        : ''
                    }`}
                  >
                    {states[d.id].running
                      ? '가동'
                      : '정지'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head">
            <div>
              <h2>최근 제어 로그</h2>
              <p>
                브라우저에서 전송한 최근 명령
              </p>
            </div>
          </div>

          <div className="log-list">
            {logs.length === 0 ? (
              <p className="empty">
                아직 실행된 명령이 없습니다.
              </p>
            ) : (
              logs
                .slice(0, 8)
                .map((log) => (
                  <div
                    className="log-row"
                    key={log.id}
                  >
                    <span
                      className={`log-dot ${log.type}`}
                    />

                    <div>
                      <strong>
                        {log.device}
                      </strong>

                      <span>
                        {log.message}
                      </span>
                    </div>

                    <time>
                      {log.time}
                    </time>
                  </div>
                ))
            )}
          </div>
        </article>
      </section>
    </>
  );
}

export default function App() {
  const [activeTab, setActiveTab] =
    useState('dashboard');

  const [devices, setDevices] = useState(loadDeviceIps);

  const [states, setStates] = useState(
    () =>
      Object.fromEntries(
        Object.values(
          DEVICE_DEFS
        ).map((d) => [
          d.id,
          blankState(d),
        ])
      )
  );

  const [globalBusy, setGlobalBusy] =
    useState(false);

  const [message, setMessage] =
    useState(
      '기존 3대 ESP IP는 등록되어 있습니다. AGV IP만 입력하면 됩니다.'
    );

  const [logs, setLogs] =
    useState([]);

  const [ipDrafts, setIpDrafts] = useState(() =>
    Object.fromEntries(Object.values(loadDeviceIps()).map((device) => [device.id, device.ip]))
  );

  const [textCommand, setTextCommand] =
    useState('');

  const addLog = (
    device,
    messageText,
    type = 'info'
  ) => {
    setLogs((prev) =>
      [
        {
          id: `${Date.now()}-${Math.random()}`,
          device,
          message: messageText,
          type,
          time: formatTime(),
        },
        ...prev,
      ].slice(0, 50)
    );
  };

  const patchState = (
    id,
    patch
  ) => {
    setStates((prev) => ({
      ...prev,
      [id]: {
        ...prev[id],
        ...patch,
      },
    }));
  };

  useEffect(() => {
    const ips = Object.fromEntries(Object.values(devices).map((device) => [device.id, device.ip]));
    window.localStorage.setItem('manufacturing-device-ips', JSON.stringify(ips));
  }, [devices]);

  const saveDeviceIp = (deviceId) => {
    const value = normalizeDeviceIp(ipDrafts[deviceId] || '');
    const device = devices[deviceId];

    if (!value) {
      setMessage(`${device.name} IP 주소를 입력하세요.`);
      return;
    }

    setDevices((prev) => ({
      ...prev,
      [deviceId]: {
        ...prev[deviceId],
        ip: value,
      },
    }));

    setIpDrafts((prev) => ({ ...prev, [deviceId]: value }));
    patchState(deviceId, {
      connected: false,
    });

    setMessage(`${device.name} IP를 ${value}(으)로 설정했습니다. 상태를 확인하세요.`);

    addLog(device.name, `IP 설정: ${value}`, 'info');
  };

  const submitTextCommand = () => {
    const value =
      textCommand.trim();

    if (!value) {
      setMessage(
        '명령을 입력하세요.'
      );
      return;
    }

    setMessage(
      `텍스트 명령 입력: ${value}`
    );

    addLog(
      '텍스트 명령',
      value,
      'info'
    );

    setTextCommand('');
  };

  const commandableDevices =
    useMemo(
      () =>
        Object.values(
          devices
        ).filter((d) => d.ip),
      [devices]
    );

  const allCommand = async (
    command,
    running
  ) => {
    setGlobalBusy(true);

    setMessage(
      `${
        command === 'start'
          ? '전체 시작'
          : '전체 정지'
      } 명령 전송 중...`
    );

    const results =
      await Promise.allSettled(
        commandableDevices.map(
          (d) =>
            request(
              d,
              `/${command}`
            )
        )
      );

    let ok = 0;

    results.forEach(
      (result, index) => {
        const d =
          commandableDevices[index];

        if (
          result.status ===
          'fulfilled'
        ) {
          ok += 1;

          patchState(d.id, {
            connected: true,
            running,
            ...(d.kind === 'agv'
              ? {
                  agvState: running
                    ? 'MISSION'
                    : 'STOPPED',
                }
              : {}),
          });

          addLog(
            d.name,
            `전체 ${command.toUpperCase()} 성공`,
            'success'
          );
        } else {
          patchState(d.id, {
            connected: false,
          });

          addLog(
            d.name,
            `전체 ${command.toUpperCase()} 실패`,
            'error'
          );
        }
      }
    );

    setMessage(
      `${commandableDevices.length}대 중 ${ok}대 명령 성공`
    );

    setGlobalBusy(false);
  };

  const checkStatus = async () => {
    setGlobalBusy(true);

    setMessage(
      '장비 연결 상태 확인 중...'
    );

    const entries =
      Object.values(
        devices
      ).filter((d) => d.ip);

    const results =
      await Promise.allSettled(
        entries.map((d) => statusRequest(d))
      );

    let ok = 0;

    for (
      let i = 0;
      i < results.length;
      i += 1
    ) {
      const d = entries[i];
      const r = results[i];

      if (
        r.status ===
        'fulfilled'
      ) {
        ok += 1;

        try {
          const data =
            await r.value.json();

          patchState(d.id, {
            connected: true,

            running:
              typeof data.running ===
              'boolean'
                ? data.running
                : states[d.id]
                    .running,

            speed:
              typeof data.speed ===
              'number'
                ? data.speed
                : states[d.id]
                    .speed,

            direction:
              data.direction ||
              states[d.id]
                .direction,

            color:
              data.color ||
              states[d.id]
                .color,

            agvState:
              data.state ||
              states[d.id]
                .agvState,
          });
        } catch {
          patchState(d.id, {
            connected: true,
          });
        }
      } else {
        patchState(d.id, {
          connected: false,
        });
      }
    }

    setMessage(
      `${entries.length}대 중 ${ok}대 응답`
    );

    setGlobalBusy(false);
  };

  useEffect(() => {
    checkStatus();
    // Initial availability check only. Subsequent checks are user initiated.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="app-shell">

      <header className="topbar">
        <div className="brand">

          <div className="brand-icon">
            <Factory size={24} />
          </div>

          <div>
            <div className="eyebrow">OPERATIONS CENTER <span>•</span> LIVE</div>
            <h1>Smart Manufacturing Navi</h1>

            <p>
              HTTP 기반 스마트 제조 통합 관제 프로토타입
            </p>
          </div>

        </div>

        <button
          className="outline status-button"
          disabled={globalBusy}
          onClick={checkStatus}
        >
          <Activity size={18} />
          연결 확인
        </button>
      </header>

      <nav
        className="tabs"
        aria-label="화면 전환"
      >
        <button
          className={
            activeTab ===
            'dashboard'
              ? 'active'
              : ''
          }
          onClick={() =>
            setActiveTab(
              'dashboard'
            )
          }
        >
          <LayoutDashboard size={18} />
          대시보드
        </button>

        <button
          className={
            activeTab ===
            'control'
              ? 'active'
              : ''
          }
          onClick={() =>
            setActiveTab(
              'control'
            )
          }
        >
          <Settings2 size={18} />
          설비 제어
        </button>
      </nav>

      <section className="global-panel">
        <div>
          <span className="section-kicker">MASTER CONTROL</span>
          <h2>
            전체 공정 제어
          </h2>

          <p>
            {message}
          </p>
        </div>

        <div className="global-actions">
          <button
            className="primary"
            disabled={globalBusy}
            onClick={() =>
              allCommand(
                'start',
                true
              )
            }
          >
            <Play size={18} />
            전체 START
          </button>

          <button
            className="danger"
            disabled={globalBusy}
            onClick={() =>
              allCommand(
                'stop',
                false
              )
            }
          >
            <CircleStop size={18} />
            전체 STOP
          </button>
        </div>
      </section>

      <section className="text-command-panel">
        <div>
          <strong>
            빠른 명령
          </strong>

          <span>
            명령을 기록하고 다음 작업으로 이어가세요.
          </span>
        </div>

        <div className="text-command-editor">
          <input
            type="text"
            value={textCommand}
            onChange={(e) =>
              setTextCommand(
                e.target.value
              )
            }
            onKeyDown={(e) => {
              if (
                e.key === 'Enter'
              ) {
                submitTextCommand();
              }
            }}
            placeholder="예: 컨베이어 시작해줘"
            aria-label="텍스트 명령 입력"
          />

          <button
            type="button"
            onClick={
              submitTextCommand
            }
          >
            전송
          </button>
        </div>
      </section>

      <section className="device-ip-config">
        <div>
          <strong>장치별 ESP IP</strong>

          <span>각 장치의 Wi-Fi IP를 설정한 뒤 상태 확인을 실행하세요.</span>
        </div>

        <div className="device-ip-list">
          {Object.values(devices).map((device) => (
            <label className="device-ip-row" key={device.id}>
              <span>{device.name}</span>
              <input
                value={ipDrafts[device.id] || ''}
                onChange={(event) => setIpDrafts((prev) => ({
                  ...prev,
                  [device.id]: event.target.value,
                }))}
                placeholder="예: 172.20.10.14"
              />
              <button type="button" onClick={() => saveDeviceIp(device.id)}>IP 적용</button>
            </label>
          ))}
        </div>
      </section>

      {activeTab ===
      'dashboard' ? (
        <Dashboard
          devices={devices}
          states={states}
          logs={logs}
          onCheckStatus={
            checkStatus
          }
        />
      ) : (
        <section className="device-grid">
          {Object.values(
            devices
          ).map((device) => (
            <DeviceCard
              key={device.id}
              device={device}
              state={
                states[
                  device.id
                ]
              }
              onState={
                patchState
              }
              onLog={addLog}
            />
          ))}
        </section>
      )}

      <footer>
        프로토타입용 소프트웨어 제어 화면입니다. 실제 산업용 비상정지는 별도의 하드웨어 안전회로가 필요합니다.
      </footer>

      <Chatbot devices={devices} states={states} />

    </main>
  );
}
