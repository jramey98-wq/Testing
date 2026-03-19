import type { Game, Team, GameStatus } from '../types/espn';

const BASE_URL =
  'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard';

function parseTeam(raw: any): Team {
  return {
    id: raw.team?.id || '',
    name: raw.team?.displayName || raw.team?.name || 'TBD',
    shortName: raw.team?.abbreviation || '',
    logo: raw.team?.logo || '',
    score: parseInt(raw.score, 10) || 0,
    seed: raw.curatedRank?.current?.toString() || raw.team?.seed || '',
    record: raw.records?.[0]?.summary || '',
    winner: raw.winner || false,
  };
}

function parseStatus(raw: any): GameStatus {
  const t = raw?.type || {};
  return {
    state: t.state || 'pre',
    detail: t.detail || '',
    shortDetail: t.shortDetail || '',
    displayClock: raw.displayClock || '',
    period: raw.period || 0,
  };
}

function parseGame(ev: any): Game {
  const comp = ev.competitions?.[0] || {};
  const teams = comp.competitors || [];
  const home = teams.find((t: any) => t.homeAway === 'home') || teams[0] || {};
  const away = teams.find((t: any) => t.homeAway === 'away') || teams[1] || {};

  return {
    id: ev.id,
    name: ev.name || '',
    shortName: ev.shortName || '',
    home: parseTeam(home),
    away: parseTeam(away),
    status: parseStatus(comp.status || ev.status || {}),
    broadcast: comp.broadcasts?.[0]?.names?.[0] || '',
    note: comp.notes?.[0]?.headline || '',
    startDate: ev.date || '',
  };
}

function dateStr(d: Date): string {
  return d.toISOString().slice(0, 10).replace(/-/g, '');
}

export async function fetchScores(date: Date): Promise<Game[]> {
  const ds = dateStr(date);
  // Try tournament group first (group 100), fall back to all games
  let url = `${BASE_URL}?dates=${ds}&groups=100&limit=60`;
  let resp = await fetch(url);
  let data = await resp.json();

  if (!data.events || data.events.length === 0) {
    url = `${BASE_URL}?dates=${ds}&limit=60`;
    resp = await fetch(url);
    data = await resp.json();
  }

  return (data.events || []).map(parseGame);
}

export async function fetchBracket(): Promise<Game[]> {
  // Fetch a wide date range covering the full tournament window
  const now = new Date();
  const year = now.getMonth() >= 9 ? now.getFullYear() + 1 : now.getFullYear();
  const start = `${year}0301`;
  const end = `${year}0410`;

  const url = `${BASE_URL}?dates=${start}-${end}&groups=100&limit=200`;
  const resp = await fetch(url);
  const data = await resp.json();

  return (data.events || []).map(parseGame);
}
