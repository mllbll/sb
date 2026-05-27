type EventHandler = (payload: unknown) => void;

const MAX_BACKOFF = 30000;
const MAX_RETRIES = 5;

function getWsUrl(path: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}${path}`;
}

class WebSocketManager {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;
  private shouldReconnect = false;
  private retryCount = 0;
  private readonly path: string;

  constructor(path: string) {
    this.path = path;
  }

  connect() {
    this.shouldReconnect = true;
    this.retryCount = 0;
    this.reconnectDelay = 1000;
    this.tryConnect();
  }

  reconnect() {
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.retryCount = 0;
    this.reconnectDelay = 1000;
    this.shouldReconnect = true;
    this.tryConnect();
  }

  private tryConnect() {
    const url = getWsUrl(this.path);
    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log('[WS] Connected to', url);
        this.retryCount = 0;
        this.reconnectDelay = 1000;
        this.emit('ws.status', { status: 'connected', retryCount: 0 });
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data as string);
          if (msg.type) {
            this.emit(msg.type as string, msg.payload ?? null);
          }
        } catch {
          console.warn('[WS] Failed to parse message:', event.data);
        }
      };

      this.ws.onerror = () => {
        console.warn('[WS] Connection error on', url);
      };

      this.ws.onclose = () => {
        console.log('[WS] Disconnected from', url);
        this.ws = null;
        if (this.shouldReconnect && this.retryCount < MAX_RETRIES) {
          this.scheduleReconnect();
        } else {
          this.emit('ws.status', { status: 'disconnected', retryCount: this.retryCount });
        }
      };
    } catch (err) {
      console.warn('[WS] Failed to connect to', url, err);
      if (this.shouldReconnect && this.retryCount < MAX_RETRIES) {
        this.scheduleReconnect();
      } else {
        this.emit('ws.status', { status: 'disconnected', retryCount: this.retryCount });
      }
    }
  }

  private scheduleReconnect() {
    this.retryCount++;
    this.emit('ws.status', { status: 'reconnecting', retryCount: this.retryCount });
    console.log(`[WS] Reconnecting to ${this.path} attempt ${this.retryCount}/${MAX_RETRIES} in ${this.reconnectDelay}ms...`);
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, MAX_BACKOFF);
      this.tryConnect();
    }, this.reconnectDelay);
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.close();
      this.ws = null;
    }
    this.emit('ws.status', { status: 'disconnected', retryCount: 0 });
  }

  getPath(): string {
    return this.path;
  }

  subscribe(eventType: string, handler: EventHandler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType)!.add(handler);
  }

  unsubscribe(eventType: string, handler: EventHandler) {
    this.handlers.get(eventType)?.delete(handler);
  }

  private emit(eventType: string, payload: unknown) {
    this.handlers.get(eventType)?.forEach(h => h(payload));
  }
}

export const crowdWsManager = new WebSocketManager('/ws/crowd');
export const fightWsManager = new WebSocketManager('/ws/fight');
export const fallWsManager = new WebSocketManager('/ws/fall');
