import { create } from 'zustand';

export interface Message {
  id: string;
  from: 'student' | 'tutor';
  text: string;
  timestamp: Date;
}

interface MessageStore {
  messages: Message[];
  isLoading: boolean;
  addMessage: (from: 'student' | 'tutor', text: string) => void;
  clearMessages: () => void;
  setLoading: (loading: boolean) => void;
}

export const useMessageStore = create<MessageStore>((set) => ({
  messages: [],
  isLoading: false,

  addMessage: (from, text) => {
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: `msg-${Date.now()}-${Math.random()}`,
          from,
          text,
          timestamp: new Date(),
        },
      ],
    }));
  },

  clearMessages: () => {
    set({ messages: [] });
  },

  setLoading: (loading) => {
    set({ isLoading: loading });
  },
}));
