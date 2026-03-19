import { useEffect, useRef } from 'react';
import { useStore } from '../store/useStore';
import type { StatusFilter } from '../types/espn';
import styles from './LiveScores.module.css';

const POLL_INTERVAL = 15_000; // 15 seconds for live feel

function dateDelta(offset: number): Date {
  const d = new Date();
  d.setDate(d.getDate() + offset);
  return d;
}

function dateLabel(offset: number): string {
  if (offset === 0) return 'Today';
  if (offset === -1) return 'Yesterday';
  if (offset === 1) return 'Tomorrow';
  return dateDelta(offset).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function dateValue(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function StatusBadge({ state }: { state: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    in: { label: 'In Progress', cls: styles.badgeLive },
    post: { label: 'Completed', cls: styles.badgeFinal },
    pre: { label: 'Scheduled', cls: styles.badgeScheduled },
  };
  const info = map[state] || map.pre;
  return <span className={`${styles.badge} ${info.cls}`}>{info.label}</span>;
}

function GameRow({ game }: { game: Game }) {
  const isPre = game.status.state === 'pre';
  const isFinal = game.status.state === 'post';
  const isLive = game.status.state === 'in';

  return (
    <tr className={isLive ? styles.liveRow : ''}>
      <td><StatusBadge state={game.status.state} /></td>
      <td>
        <div className={styles.teamCell}>
          {game.away.logo && (
            <img
              className={styles.teamLogo}
              src={game.away.logo}
              alt=""
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
          <span className={styles.teamName}>{game.away.name}</span>
          {game.away.seed && <span className={styles.seed}>({game.away.seed})</span>}
          <span className={styles.record}>{game.away.record}</span>
        </div>
      </td>
      <td className={`${styles.score} ${isFinal && game.away.winner ? styles.winner : ''}`}>
        {isPre ? '-' : game.away.score}
      </td>
      <td className={styles.at}>@</td>
      <td className={`${styles.score} ${isFinal && game.home.winner ? styles.winner : ''}`}>
        {isPre ? '-' : game.home.score}
      </td>
      <td>
        <div className={styles.teamCell}>
          {game.home.logo && (
            <img
              className={styles.teamLogo}
              src={game.home.logo}
              alt=""
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          )}
          <span className={styles.teamName}>{game.home.name}</span>
          {game.home.seed && <span className={styles.seed}>({game.home.seed})</span>}
          <span className={styles.record}>{game.home.record}</span>
        </div>
      </td>
      <td className={styles.detail}>
        {isLive && <span className={styles.liveDot} />}
        {game.note || game.status.shortDetail || game.status.detail}
      </td>
      <td className={styles.broadcast}>{game.broadcast}</td>
    </tr>
  );
}

export default function LiveScores() {
  const {
    games, gamesLoading, gamesError, selectedDate,
    statusFilter, searchQuery, lastScoreUpdate,
    setSelectedDate, setStatusFilter, setSearchQuery, loadScores,
  } = useStore();

  const intervalRef = useRef<ReturnType<typeof setInterval>>();
  const countdownRef = useRef<ReturnType<typeof setInterval>>();
  const cdRef = useRef(POLL_INTERVAL / 1000);
  const cdDisplayRef = useRef<HTMLSpanElement>(null);

  // Initial load + polling
  useEffect(() => {
    loadScores();
    intervalRef.current = setInterval(() => {
      loadScores();
      cdRef.current = POLL_INTERVAL / 1000;
    }, POLL_INTERVAL);

    countdownRef.current = setInterval(() => {
      cdRef.current = Math.max(0, cdRef.current - 1);
      if (cdDisplayRef.current) cdDisplayRef.current.textContent = String(cdRef.current);
    }, 1000);

    return () => {
      clearInterval(intervalRef.current);
      clearInterval(countdownRef.current);
    };
  }, [selectedDate]);

  // Filter games
  let filtered = games;
  if (statusFilter === 'live') filtered = filtered.filter((g) => g.status.state === 'in');
  else if (statusFilter === 'final') filtered = filtered.filter((g) => g.status.state === 'post');
  else if (statusFilter === 'scheduled') filtered = filtered.filter((g) => g.status.state === 'pre');

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter(
      (g) =>
        g.home.name.toLowerCase().includes(q) ||
        g.away.name.toLowerCase().includes(q) ||
        g.home.shortName.toLowerCase().includes(q) ||
        g.away.shortName.toLowerCase().includes(q),
    );
  }

  // Count live games
  const liveCount = games.filter((g) => g.status.state === 'in').length;

  return (
    <div className={styles.container}>
      <div className={styles.filterBar}>
        <select
          className={styles.select}
          value={dateValue(selectedDate)}
          onChange={(e) => {
            setSelectedDate(new Date(e.target.value + 'T12:00:00'));
          }}
        >
          {[-3, -2, -1, 0, 1, 2, 3].map((off) => (
            <option key={off} value={dateValue(dateDelta(off))}>
              {dateLabel(off)}
            </option>
          ))}
        </select>

        <select
          className={styles.select}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
        >
          <option value="all">All Statuses</option>
          <option value="live">In Progress</option>
          <option value="final">Completed</option>
          <option value="scheduled">Scheduled</option>
        </select>

        <input
          className={styles.searchInput}
          type="text"
          placeholder="Search teams..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        <button className={styles.refreshBtn} onClick={loadScores}>
          ↻ Refresh
        </button>

        {liveCount > 0 && (
          <span className={styles.liveIndicator}>
            <span className={styles.liveDot} />
            {liveCount} live
          </span>
        )}

        <span className={styles.autoRefresh}>
          Auto-sync: <span ref={cdDisplayRef}>{POLL_INTERVAL / 1000}</span>s
        </span>
      </div>

      {gamesError && (
        <div className={styles.errorBanner}>⚠ Data sync failed: {gamesError}</div>
      )}

      {gamesLoading && games.length === 0 ? (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          Fetching performance data...
        </div>
      ) : filtered.length === 0 ? (
        <div className={styles.empty}>No matching events for this date/filter.</div>
      ) : (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Status</th>
              <th>Away</th>
              <th>PTS</th>
              <th></th>
              <th>PTS</th>
              <th>Home</th>
              <th>Detail</th>
              <th>Channel</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((g) => (
              <GameRow key={g.id} game={g} />
            ))}
          </tbody>
        </table>
      )}

      {lastScoreUpdate && (
        <div className={styles.lastUpdated}>
          Last sync: {lastScoreUpdate.toLocaleTimeString()}
        </div>
      )}
    </div>
  );
}
