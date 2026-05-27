export type WSEventType =
  | 'crowd.update'
  | 'fight.detected'
  | 'fight.resolved'
  | 'fall.detected'
  | 'fall.resolved'
  | 'camera.status'
  | 'ping';

export interface ZoneUpdate {
  id: string;
  current: number;
}

export interface CrowdUpdatePayload {
  total: number;
  zones: ZoneUpdate[];
}

export interface FightDetectedPayload {
  id: string;
  location: string;
  camera_id: string;
  participants: number;
}

export interface FightResolvedPayload {
  id: string;
}

export interface FallDetectedPayload {
  id: string;
  location: string;
  camera_id: string;
  person_type: string;
  age: number;
}

export interface FallResolvedPayload {
  id: string;
}

export interface CameraStatusPayload {
  camera_id: string;
  online: boolean;
}

export type WSMessage =
  | { type: 'crowd.update'; payload: CrowdUpdatePayload }
  | { type: 'fight.detected'; payload: FightDetectedPayload }
  | { type: 'fight.resolved'; payload: FightResolvedPayload }
  | { type: 'fall.detected'; payload: FallDetectedPayload }
  | { type: 'fall.resolved'; payload: FallResolvedPayload }
  | { type: 'camera.status'; payload: CameraStatusPayload }
  | { type: 'ping'; payload?: unknown };
