import { create } from 'zustand';
import type { Game, StatusFilter } from '../types/espn';
import { fetchScores, fetchBracket } from '../services/espn';

interface AppState {
  // Scores
  games: Game[];
  gamesLoading: boolean;
  gamesError: string | null;
  selectedDate: Date;
  statusFilter: StatusFilter;
  searchQuery: string;
  lastScoreUpdate: Date | null;

  // Bracket
  bracketGames: Game[];
  bracketLoading: boolean;
  bracketError: string | null;
  bracketRegion: string;
  lastBracketUpdate: Date | null;

  // Actions
  setSelectedDate: (d: Date) => void;
  setStatusFilter: (f: StatusFilter) => void;
  setSearchQuery: (q: string) => void;
  setBracketRegion: (r: string) => void;
  loadScores: () => Promise<void>;
  loadBracket: () => Promise<void>;
}

export const useStore = create<AppState>((set, get) => ({
  games: [],
  gamesLoading: false,
  gamesError: null,
  selectedDate: new Date(),
  statusFilter: 'all',
  searchQuery: '',
  lastScoreUpdate: null,

  bracketGames: [],
  bracketLoading: false,
  bracketError: null,
  bracketRegion: 'all',
  lastBracketUpdate: null,

  setSelectedDate: (d) => {
    set({ selectedDate: d });
    get().loadScores();
  },
  setStatusFilter: (f) => set({ statusFilter: f }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  setBracketRegion: (r) => set({ bracketRegion: r }),

  loadScores: async () => {
    set({ gamesLoading: true, gamesError: null });
    try {
      const games = await fetchScores(get().selectedDate);
      set({ games, gamesLoading: false, lastScoreUpdate: new Date() });
    } catch (e: any) {
      set({ gamesError: e.message, gamesLoading: false });
    }
  },

  loadBracket: async () => {
    set({ bracketLoading: true, bracketError: null });
    try {
      const bracketGames = await fetchBracket();
      set({ bracketGames, bracketLoading: false, lastBracketUpdate: new Date() });
    } catch (e: any) {
      set({ bracketError: e.message, bracketLoading: false });
    }
  },
}));
