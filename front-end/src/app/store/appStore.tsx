import { createContext, useContext, useReducer, ReactNode } from "react";
import { zones, cameras, fallIncidents } from "../data/mock";

type WsStatus = 'connected' | 'reconnecting' | 'disconnected';

interface AppState {
  totalPeople: number;
  zoneStats: Record<string, { current: number }>;
  activeFightId: string | null;
  activeFallIds: string[];
  cameraStatuses: Record<string, boolean>;
  wsStatus: WsStatus;
  wsRetryCount: number;
  lastUpdate: Date | null;
}

type AppAction =
  | { type: 'CROWD_UPDATE'; payload: { total: number; zones: Array<{ id: string; current: number }> } }
  | { type: 'FIGHT_DETECTED'; payload: { id: string } }
  | { type: 'FIGHT_RESOLVED'; payload: { id: string } }
  | { type: 'FALL_DETECTED'; payload: { id: string } }
  | { type: 'FALL_RESOLVED'; payload: { id: string } }
  | { type: 'CAMERA_STATUS'; payload: { camera_id: string; online: boolean } }
  | { type: 'WS_STATUS'; status: WsStatus; retryCount?: number };

const initialState: AppState = {
  totalPeople: zones.reduce((a, z) => a + z.current, 0),
  zoneStats: Object.fromEntries(zones.map(z => [z.id, { current: z.current }])),
  activeFightId: "FGT-0047",
  activeFallIds: fallIncidents.filter(f => f.status === "active").map(f => f.id),
  cameraStatuses: Object.fromEntries(cameras.map(c => [c.id, c.online])),
  wsStatus: 'disconnected',
  wsRetryCount: 0,
  lastUpdate: null,
};

function reducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'CROWD_UPDATE': {
      const newZoneStats = { ...state.zoneStats };
      action.payload.zones.forEach(z => {
        newZoneStats[z.id] = { current: z.current };
      });
      return { ...state, totalPeople: action.payload.total, zoneStats: newZoneStats, lastUpdate: new Date() };
    }
    case 'FIGHT_DETECTED':
      return { ...state, activeFightId: action.payload.id, lastUpdate: new Date() };
    case 'FIGHT_RESOLVED':
      return {
        ...state,
        activeFightId: state.activeFightId === action.payload.id ? null : state.activeFightId,
        lastUpdate: new Date(),
      };
    case 'FALL_DETECTED':
      return {
        ...state,
        activeFallIds: [...state.activeFallIds.filter(id => id !== action.payload.id), action.payload.id],
        lastUpdate: new Date(),
      };
    case 'FALL_RESOLVED':
      return {
        ...state,
        activeFallIds: state.activeFallIds.filter(id => id !== action.payload.id),
        lastUpdate: new Date(),
      };
    case 'CAMERA_STATUS':
      return {
        ...state,
        cameraStatuses: { ...state.cameraStatuses, [action.payload.camera_id]: action.payload.online },
        lastUpdate: new Date(),
      };
    case 'WS_STATUS':
      return {
        ...state,
        wsStatus: action.status,
        wsRetryCount: action.retryCount ?? 0,
        lastUpdate: action.status === 'connected' ? new Date() : state.lastUpdate,
      };
    default:
      return state;
  }
}

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}

const AppContext = createContext<AppContextType>({
  state: initialState,
  dispatch: () => {},
});

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return <AppContext.Provider value={{ state, dispatch }}>{children}</AppContext.Provider>;
}

export function useAppStore() {
  return useContext(AppContext);
}

export type { AppState, AppAction, WsStatus };
