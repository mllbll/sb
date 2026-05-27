import { useEffect, useRef } from "react";
import { crowdWsManager, fallWsManager, fightWsManager } from "../services/websocket";
import { useAppStore } from "../store/appStore";
import type { WsStatus } from "../store/appStore";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export function useWebSocket() {
  const { dispatch } = useAppStore();
  const crowdStatus = useRef<WsStatus>('disconnected');
  const fightStatus = useRef<WsStatus>('disconnected');
  const fallStatus = useRef<WsStatus>('disconnected');

  useEffect(() => {
    if (USE_MOCK) return;

    const dispatchCombined = (retryCount: number) => {
      const statuses = [crowdStatus.current, fightStatus.current, fallStatus.current];
      let combined: WsStatus;
      if (statuses.every(status => status === 'connected')) {
        combined = 'connected';
      } else if (statuses.some(status => status === 'reconnecting')) {
        combined = 'reconnecting';
      } else {
        combined = 'disconnected';
      }
      dispatch({ type: 'WS_STATUS', status: combined, retryCount });
    };

    const onCrowdStatus = (payload: unknown) => {
      const p = payload as { status: WsStatus; retryCount: number };
      crowdStatus.current = p.status;
      dispatchCombined(p.retryCount);
    };

    const onFightStatus = (payload: unknown) => {
      const p = payload as { status: WsStatus; retryCount: number };
      fightStatus.current = p.status;
      dispatchCombined(p.retryCount);
    };
    const onFallStatus = (payload: unknown) => {
      const p = payload as { status: WsStatus; retryCount: number };
      fallStatus.current = p.status;
      dispatchCombined(p.retryCount);
    };

    const onCrowdUpdate = (payload: unknown) => {
      const p = payload as { total: number; zones: Array<{ id: string; current: number }> };
      dispatch({ type: 'CROWD_UPDATE', payload: p });
    };
    const onFightDetected = (payload: unknown) => {
      const p = payload as { id: string };
      dispatch({ type: 'FIGHT_DETECTED', payload: { id: p.id } });
    };
    const onFightResolved = (payload: unknown) => {
      const p = payload as { id: string };
      dispatch({ type: 'FIGHT_RESOLVED', payload: p });
    };
    const onFallDetected = (payload: unknown) => {
      const p = payload as { id: string };
      dispatch({ type: 'FALL_DETECTED', payload: { id: p.id } });
    };
    const onFallResolved = (payload: unknown) => {
      const p = payload as { id: string };
      dispatch({ type: 'FALL_RESOLVED', payload: p });
    };
    const onCameraStatus = (payload: unknown) => {
      const p = payload as { camera_id: string; online: boolean };
      dispatch({ type: 'CAMERA_STATUS', payload: p });
    };

    // Crowd WS: crowd density events
    crowdWsManager.subscribe('ws.status', onCrowdStatus);
    crowdWsManager.subscribe('crowd.update', onCrowdUpdate);

    // Fight WS: fight and camera events
    fightWsManager.subscribe('ws.status', onFightStatus);
    fightWsManager.subscribe('fight.detected', onFightDetected);
    fightWsManager.subscribe('fight.resolved', onFightResolved);
    fightWsManager.subscribe('camera.status', onCameraStatus);

    // Fall WS: fall and camera events
    fallWsManager.subscribe('ws.status', onFallStatus);
    fallWsManager.subscribe('fall.detected', onFallDetected);
    fallWsManager.subscribe('fall.resolved', onFallResolved);
    fallWsManager.subscribe('camera.status', onCameraStatus);

    crowdWsManager.connect();
    fightWsManager.connect();
    fallWsManager.connect();

    return () => {
      crowdWsManager.unsubscribe('ws.status', onCrowdStatus);
      crowdWsManager.unsubscribe('crowd.update', onCrowdUpdate);
      fightWsManager.unsubscribe('ws.status', onFightStatus);
      fightWsManager.unsubscribe('fight.detected', onFightDetected);
      fightWsManager.unsubscribe('fight.resolved', onFightResolved);
      fightWsManager.unsubscribe('camera.status', onCameraStatus);
      fallWsManager.unsubscribe('ws.status', onFallStatus);
      fallWsManager.unsubscribe('fall.detected', onFallDetected);
      fallWsManager.unsubscribe('fall.resolved', onFallResolved);
      fallWsManager.unsubscribe('camera.status', onCameraStatus);
      crowdWsManager.disconnect();
      fightWsManager.disconnect();
      fallWsManager.disconnect();
    };
  }, [dispatch]);
}
