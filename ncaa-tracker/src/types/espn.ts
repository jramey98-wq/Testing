export interface Game {
  id: string;
  name: string;
  shortName: string;
  home: Team;
  away: Team;
  status: GameStatus;
  broadcast: string;
  note: string;
  startDate: string;
}

export interface Team {
  id: string;
  name: string;
  shortName: string;
  logo: string;
  score: number;
  seed: string;
  record: string;
  winner: boolean;
}

export interface GameStatus {
  state: 'pre' | 'in' | 'post';
  detail: string;
  shortDetail: string;
  displayClock: string;
  period: number;
}

export type StatusFilter = 'all' | 'live' | 'final' | 'scheduled';

export interface BracketRounds {
  [roundName: string]: Game[];
}
