import { useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';
import type { Game, BracketRounds } from '../types/espn';
import styles from './Bracket.module.css';

const POLL_INTERVAL = 30_000;

const ROUND_ORDER = [
  'First Four',
  'First Round',
  'Second Round',
  'Sweet 16',
  'Elite Eight',
  'Final Four',
  'Championship',
];

const WORK_NAMES: Record<string, string> = {
  'First Four': 'Preliminary',
  'First Round': 'Round 1 Review',
  'Second Round': 'Round 2 Review',
  'Sweet 16': 'Regional QBR',
  'Elite Eight': 'Regional Finals',
  'Final Four': 'National Semi',
  'Championship': 'National Final',
};

const REGIONS = ['all', 'south', 'east', 'west', 'midwest'];

function classifyRound(note: string, name: string): string {
  const s = (note + ' ' + name).toLowerCase();
  if (s.includes('first four')) return 'First Four';
  if (s.includes('1st round') || s.includes('first round')) return 'First Round';
  if (s.includes('2nd round') || s.includes('second round')) return 'Second Round';
  if (s.includes('sweet 16') || s.includes('sweet sixteen')) return 'Sweet 16';
  if (s.includes('elite eight') || s.includes('elite 8')) return 'Elite Eight';
  if (s.includes('final four') || s.includes('semifinal')) return 'Final Four';
  if (s.includes('championship') || s.includes('national championship')) return 'Championship';
  return 'Other';
}

function organizeByRound(games: Game[], region: string): BracketRounds {
  const rounds: BracketRounds = {};
  for (const r of ROUND_ORDER) rounds[r] = [];

  for (const g of games) {
    const round = classifyRound(g.note, g.name);
    if (!rounds[round]) rounds[round] = [];

    // Region filter (Final Four and Championship are region-agnostic)
    if (region !== 'all' && round !== 'Final Four' && round !== 'Championship') {
      if (!g.note.toLowerCase().includes(region)) continue;
    }

    rounds[round].push(g);
  }

  return rounds;
}

function BracketGame({ game }: { game: Game }) {
  const isLive = game.status.state === 'in';
  const isFinal = game.status.state === 'post';
  const isPre = game.status.state === 'pre';

  return (
    <div className={`${styles.game} ${isLive ? styles.gameActive : ''}`}>
      {[game.away, game.home].map((team, i) => {
        let cls = styles.team;
        if (isFinal && team.winner) cls += ' ' + styles.teamWinner;
        if (isFinal && !team.winner) cls += ' ' + styles.teamLoser;

        return (
          <div key={i} className={cls}>
            <span className={styles.seed}>{team.seed || '-'}</span>
            {team.logo && (
              <img
                className={styles.logo}
                src={team.logo}
                alt=""
                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
              />
            )}
            <span className={styles.name}>{team.shortName || team.name}</span>
            <span className={styles.pts}>
              {isPre ? '' : team.score}
            </span>
          </div>
        );
      })}
      {isLive && (
        <div className={styles.gameLiveBadge}>
          <span className={styles.liveDot} />
          {game.status.shortDetail}
        </div>
      )}
    </div>
  );
}

export default function Bracket() {
  const {
    bracketGames, bracketLoading, bracketError,
    bracketRegion, lastBracketUpdate,
    setBracketRegion, loadBracket,
  } = useStore();

  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  useEffect(() => {
    loadBracket();
    intervalRef.current = setInterval(loadBracket, POLL_INTERVAL);
    return () => clearInterval(intervalRef.current);
  }, []);

  const rounds = organizeByRound(bracketGames, bracketRegion);
  const hasGames = bracketGames.length > 0;

  return (
    <div className={styles.container}>
      <div className={styles.filterBar}>
        <div className={styles.regionTabs}>
          {REGIONS.map((r) => (
            <button
              key={r}
              className={`${styles.regionTab} ${bracketRegion === r ? styles.regionTabActive : ''}`}
              onClick={() => setBracketRegion(r)}
            >
              {r === 'all' ? 'Full Bracket' : r.charAt(0).toUpperCase() + r.slice(1) + ' Region'}
            </button>
          ))}
        </div>
        <button className={styles.refreshBtn} onClick={loadBracket}>
          ↻ Refresh Bracket
        </button>
      </div>

      {bracketError && (
        <div className={styles.errorBanner}>⚠ Bracket sync failed: {bracketError}</div>
      )}

      {bracketLoading && bracketGames.length === 0 ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          Loading bracket structure...
        </div>
      ) : !hasGames ? (
        <div className={styles.placeholder}>
          <div className={styles.errorBanner}>
            The 2026 NCAA Tournament bracket has not been announced yet or no games are currently available.
            Bracket data will auto-populate once tournament games are scheduled.
            Check the "Live Metrics" tab for today's scores.
          </div>
          <div className={styles.dates}>
            <p className={styles.datesTitle}>2026 NCAA Tournament Key Dates</p>
            <p>Selection Sunday: March 15, 2026</p>
            <p>First Four: March 17-18, 2026</p>
            <p>First Round: March 19-20, 2026</p>
            <p>Second Round: March 21-22, 2026</p>
            <p>Sweet 16: March 26-27, 2026</p>
            <p>Elite Eight: March 28-29, 2026</p>
            <p>Final Four: April 4, 2026</p>
            <p>Championship: April 6, 2026</p>
          </div>
        </div>
      ) : (
        <div className={styles.bracketScroll}>
          <div className={styles.bracketWrapper}>
            {ROUND_ORDER.map((roundName) => {
              const games = rounds[roundName] || [];
              if (games.length === 0 && roundName === 'First Four') return null;

              return (
                <div key={roundName} className={styles.round}>
                  <div className={styles.roundHeader}>
                    <div>{WORK_NAMES[roundName]}</div>
                    <div className={styles.roundSub}>{roundName}</div>
                  </div>
                  <div className={styles.roundGames}>
                    {games.length === 0 ? (
                      <div className={styles.noData}>No data yet</div>
                    ) : (
                      games.map((g) => <BracketGame key={g.id} game={g} />)
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {lastBracketUpdate && (
        <div className={styles.lastUpdated}>
          Last sync: {lastBracketUpdate.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
