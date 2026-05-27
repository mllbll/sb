import { useEffect } from "react";
import { useAppStore } from "../store/appStore";
import { zones } from "../data/mock";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

// Mutable zone currents so crowd updates accumulate correctly
const mockZoneCurrents: Record<string, number> = Object.fromEntries(
  zones.map(z => [z.id, z.current])
);

export function useMockData() {
  const { dispatch } = useAppStore();

  useEffect(() => {
    if (!USE_MOCK) return;

    dispatch({ type: 'WS_STATUS', status: 'connected', retryCount: 0 });

    // Crowd update every 3s
    const crowdTimer = setInterval(() => {
      zones.forEach(z => {
        mockZoneCurrents[z.id] = Math.max(
          1,
          Math.min(z.capacity, mockZoneCurrents[z.id] + Math.floor(Math.random() * 5) - 2)
        );
      });
      const updatedZones = zones.map(z => ({ id: z.id, current: mockZoneCurrents[z.id] }));
      const total = updatedZones.reduce((a, z) => a + z.current, 0);
      dispatch({ type: 'CROWD_UPDATE', payload: { total, zones: updatedZones } });
    }, 3000);

    // Random fight or fall every 30s
    const eventTimer = setInterval(() => {
      if (Math.random() < 0.5) {
        const id = `FGT-${Math.floor(Math.random() * 9000 + 1000)}`;
        dispatch({ type: 'FIGHT_DETECTED', payload: { id } });
      } else {
        const id = `FLL-${Math.floor(Math.random() * 9000 + 1000)}`;
        dispatch({ type: 'FALL_DETECTED', payload: { id } });
      }
    }, 30000);

    return () => {
      clearInterval(crowdTimer);
      clearInterval(eventTimer);
    };
  }, [dispatch]);
}
