import { create } from 'zustand';
import { v4 as uuidv4 } from 'uuid';

interface SessionState {
  userId: string;
  sessionId: string;
  isConnected: boolean;
  currentTopic: string;
  uploadedMaterials: Array<{ id: string; name: string; type: string }>;
  isTutorAudioEnabled: boolean;
}

interface SessionStore extends SessionState {
  initSession: (topic?: string) => void;
  resetSession: () => void;
  setConnected: (connected: boolean) => void;
  setTopic: (topic: string) => void;
  addMaterial: (name: string, type: string) => void;
  removeMaterial: (id: string) => void;
  clearMaterials: () => void;
  toggleTutorAudio: () => void;
}

const getStoredUserId = () => {
  if (typeof window === 'undefined') return uuidv4();
  const stored = localStorage.getItem('agora_user_id');
  if (stored) return stored;
  const newId = uuidv4();
  localStorage.setItem('agora_user_id', newId);
  return newId;
};

export const useSessionStore = create<SessionStore>((set) => ({
  userId: getStoredUserId(),
  sessionId: uuidv4(),
  isConnected: false,
  currentTopic: 'General',
  uploadedMaterials: [],
  isTutorAudioEnabled: true,

  initSession: (topic = 'General') => {
    set({
      sessionId: uuidv4(),
      currentTopic: topic,
      uploadedMaterials: [],
      isConnected: false,
    });
  },

  resetSession: () => {
    set({
      sessionId: uuidv4(),
      uploadedMaterials: [],
      isConnected: false,
    });
  },

  setConnected: (connected) => {
    set({ isConnected: connected });
  },

  setTopic: (topic) => {
    set({ currentTopic: topic });
  },

  addMaterial: (name, type) => {
    set((state) => ({
      uploadedMaterials: [
        ...state.uploadedMaterials,
        {
          id: `mat-${Date.now()}`,
          name,
          type,
        },
      ],
    }));
  },

  removeMaterial: (id) => {
    set((state) => ({
      uploadedMaterials: state.uploadedMaterials.filter((m) => m.id !== id),
    }));
  },

  clearMaterials: () => {
    set({ uploadedMaterials: [] });
  },

  toggleTutorAudio: () => {
    set((state) => ({
      isTutorAudioEnabled: !state.isTutorAudioEnabled,
    }));
  },
}));