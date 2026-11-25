import { useEffect, useState } from 'react';
import { listTrips, getTrip } from '../api';
import type { TripResult } from '../api';

interface SavedTripsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTrip: (trip: TripResult) => void;
}

function getCurrencySymbol(curr?: string) {
  switch (curr?.toUpperCase()) {
    case 'INR':
      return '₹';
    case 'EUR':
      return '€';
    case 'GBP':
      return '£';
    case 'JPY':
      return '¥';
    default:
      return '$';
  }
}

export default function SavedTripsModal({ isOpen, onClose, onSelectTrip }: SavedTripsModalProps) {
  const [tripId, setTripId] = useState('');
  const [recentTrips, setRecentTrips] = useState<TripResult[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingLookup, setLoadingLookup] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    void (async () => {
      setLoadingList(true);
      setError(null);
      const res = await listTrips(50);
      if (active) {
        setLoadingList(false);
        if (res.error) {
          setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
        } else if (res.data) {
          setRecentTrips(res.data);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = tripId.trim();
    if (!id) return;
    setLoadingLookup(true);
    setError(null);
    const res = await getTrip(id);
    setLoadingLookup(false);
    if (res.error) {
      setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
    } else if (res.data) {
      onSelectTrip(res.data);
      onClose();
    }
  };

  const handleSelect = (trip: TripResult) => {
    onSelectTrip(trip);
    onClose();
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="saved-trips-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm overflow-y-auto"
    >
      <div className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto glass bg-surface-900 border border-white/10 rounded-3xl p-6 sm:p-8 text-white shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">🗂️</span>
            <h2 id="saved-trips-modal-title" className="text-xl sm:text-2xl font-bold gradient-text">
              My Saved Trips
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-surface-100/60 hover:text-white rounded-xl hover:bg-white/10 transition-colors"
            aria-label="Close saved trips modal"
          >
            ✕
          </button>
        </div>

        {/* Lookup by ID */}
        <form onSubmit={handleLookup} className="mt-6">
          <label className="block text-xs font-semibold text-surface-100/70 mb-1">
            Lookup Trip by ID
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={tripId}
              onChange={(e) => setTripId(e.target.value)}
              placeholder="e.g. trip_abc123"
              className="flex-1 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
            />
            <button
              type="submit"
              disabled={loadingLookup || !tripId.trim()}
              className="px-5 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 font-semibold text-white shadow-glow transition-all active:scale-95 disabled:opacity-50 flex items-center gap-2 cursor-pointer"
            >
              {loadingLookup && (
                <span
                  className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"
                  aria-hidden="true"
                />
              )}
              <span>{loadingLookup ? 'Loading…' : 'Load'}</span>
            </button>
          </div>
        </form>

        {/* Error display */}
        {error && (
          <div
            role="alert"
            className="mt-4 p-4 rounded-xl bg-red-500/20 border border-red-500/40 text-red-200 text-sm flex items-start justify-between gap-2"
          >
            <div>
              <span className="font-semibold block">⚠️ Lookup Error:</span>
              <p className="mt-1 leading-relaxed">{error}</p>
            </div>
            <button
              type="button"
              onClick={() => setError(null)}
              className="px-2 py-1 text-xs rounded bg-red-500/30 hover:bg-red-500/50 text-white transition-colors"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Recent Trips */}
        <div className="mt-6 space-y-3">
          <h3 className="text-sm font-semibold text-white">Recent Trips</h3>

          {loadingList ? (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="p-4 rounded-2xl bg-white/5 border border-white/5 animate-pulse"
                >
                  <div className="h-4 bg-white/10 rounded w-1/3 mb-2" />
                  <div className="h-3 bg-white/10 rounded w-1/2 mb-2" />
                  <div className="h-3 bg-white/10 rounded w-1/4" />
                </div>
              ))}
            </div>
          ) : recentTrips.length === 0 ? (
            <p className="text-xs text-surface-100/50 italic py-6 text-center">
              No saved trips yet. Plan a trip to see it here.
            </p>
          ) : (
            <div className="space-y-3">
              {recentTrips.map((trip) => {
                const curr = trip.currency || trip.budget?.currency || 'USD';
                const sym = getCurrencySymbol(curr);
                const dest = trip.destinations?.join(', ') || 'Unknown';
                const start = trip.preferences?.start_date || '';
                const end = trip.preferences?.end_date || '';
                const travelers = trip.preferences?.travelers ?? 1;
                const total = trip.budget?.total ?? 0;

                return (
                  <div
                    key={trip.trip_id}
                    className="p-4 rounded-2xl bg-white/5 border border-white/10 hover:border-primary-500/30 transition-colors"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                      <span className="text-sm font-semibold text-white">{dest}</span>
                      <span className="text-[10px] bg-white/10 px-2 py-0.5 rounded text-surface-100/60">
                        {trip.trip_id}
                      </span>
                    </div>
                    <div className="text-xs text-surface-100/60 space-y-0.5">
                      <p>📅 {start} → {end}</p>
                      <p>👥 {travelers} traveler{travelers > 1 ? 's' : ''}</p>
                      <p>💰 {sym}{total.toFixed(2)} {curr}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSelect(trip)}
                      className="mt-3 w-full px-4 py-2 rounded-xl bg-primary-600/20 border border-primary-500/30 text-primary-200 text-xs font-semibold hover:bg-primary-600/40 transition-colors cursor-pointer"
                    >
                      View Itinerary →
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}