import React, { useEffect, useState } from 'react';
import {
  planTrip,
  planStageDestination,
  planStageTransport,
  planStageStayActivity,
  planStageBudget,
  planStageItinerary,
} from '../api';
import type {
  Accommodation,
  TripPreferences,
  TripResult,
  DestinationAgentOutput,
  TransportStageResponse,
  StayActivityStageResponse,
  BudgetAgentOutput,
} from '../api';

interface PlannerModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialResult?: TripResult | null;
}

type WizardStep = 'setup' | 'destination' | 'transport' | 'stay' | 'budget' | 'final';

function getDefaultDates() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const startDate = tomorrow.toISOString().split('T')[0];

  const endDateDate = new Date(tomorrow);
  endDateDate.setDate(endDateDate.getDate() + 5);
  const endDate = endDateDate.toISOString().split('T')[0];

  return { startDate, endDate };
}

export default function PlannerModal({ isOpen, onClose, initialResult }: PlannerModalProps) {
  // Setup inputs
  const [origin, setOrigin] = useState('New Delhi, India');
  const [destination, setDestination] = useState('');
  const [startDate, setStartDate] = useState(() => getDefaultDates().startDate);
  const [endDate, setEndDate] = useState(() => getDefaultDates().endDate);
  const [budgetMax, setBudgetMax] = useState<number | ''>(2500);
  const [currency, setCurrency] = useState('USD');
  const [travelers, setTravelers] = useState(2);
  const [travelStyle, setTravelStyle] = useState('cultural');
  const [preferredTransport, setPreferredTransport] = useState('mixed');
  const [interests, setInterests] = useState('history, food, temples');

  // Step state
  const [wizardStep, setWizardStep] = useState<WizardStep>('setup');
  const [activeAgentName, setActiveAgentName] = useState<string | null>(null);

  // Intermediate agent outputs
  const [destinationData, setDestinationData] = useState<DestinationAgentOutput | null>(null);
  const [selectedDestination, setSelectedDestination] = useState('Kyoto, Japan');
  const [transportData, setTransportData] = useState<TransportStageResponse | null>(null);
  const [stayData, setStayData] = useState<StayActivityStageResponse | null>(null);
  const [budgetData, setBudgetData] = useState<BudgetAgentOutput | null>(null);

  // Final result & UI state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TripResult | null>(initialResult ?? null);
  const [copied, setCopied] = useState(false);
  const [prevInitialResult, setPrevInitialResult] = useState<TripResult | null | undefined>(initialResult);

  if (initialResult !== prevInitialResult) {
    setPrevInitialResult(initialResult);
    setResult(initialResult ?? null);
    if (initialResult) {
      setWizardStep('final');
    }
  }

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getCurrencySymbol = (curr?: string) => {
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
  };

  const currSymbol = getCurrencySymbol(result?.currency || budgetData?.breakdown.currency || currency);

  const handleCopyId = () => {
    if (result) {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(result.trip_id);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleApplyPreset = (
    orig: string,
    dest: string,
    curr: string,
    budget: number,
    style: string,
    transport: string,
    keywords: string,
  ) => {
    setOrigin(orig);
    setDestination(dest);
    setCurrency(curr);
    setBudgetMax(budget);
    setTravelStyle(style);
    setPreferredTransport(transport);
    setInterests(keywords);
    setError(null);
  };

  // ─── 1-Click Batch Execution (Legacy/Fast fallback) ─────────────────────
  const handleBatchSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    setActiveAgentName('All Five AI Agents Collaborating…');

    const payload: TripPreferences = {
      origin: origin.trim(),
      destinations: destination.trim() ? [destination.trim()] : null,
      start_date: startDate,
      end_date: endDate,
      budget_max: budgetMax !== '' ? Number(budgetMax) : null,
      currency: currency,
      travelers: Number(travelers),
      travel_style: travelStyle,
      preferred_transport: preferredTransport,
      interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
    };

    const res = await planTrip(payload);
    setLoading(false);
    setActiveAgentName(null);

    if (res.error) {
      setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
    } else if (res.data) {
      setResult(res.data);
      setWizardStep('final');
    }
  };

  // ─── Stage 1: Run Destination Agent ────────────────────────────────────
  const handleRunStage1 = async () => {
    setLoading(true);
    setError(null);
    setActiveAgentName('Agent 1: Destination Specialist (Analyzing style, RAG guidebooks & catalog)');

    const res = await planStageDestination({
      origin: origin.trim(),
      destinations: destination.trim() ? [destination.trim()] : null,
      start_date: startDate,
      end_date: endDate,
      budget_max: budgetMax !== '' ? Number(budgetMax) : null,
      currency: currency,
      travel_style: travelStyle,
      interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
    });

    setLoading(false);
    setActiveAgentName(null);

    if (res.error) {
      setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
    } else if (res.data) {
      setDestinationData(res.data);
      setSelectedDestination(res.data.selected_destination);
      setWizardStep('destination');
    }
  };

  // ─── Stage 2: Run Transport Agent ──────────────────────────────────────
  const handleRunStage2 = async () => {
    setLoading(true);
    setError(null);
    setActiveAgentName('Agent 2: Transport Specialist (Calculating routing corridor & round-trip fares)');

    const res = await planStageTransport({
      origin: origin.trim(),
      destination: selectedDestination,
      start_date: startDate,
      end_date: endDate,
      travelers: Number(travelers),
      preferred_transport: preferredTransport,
      travel_style: travelStyle,
      currency: currency,
    });

    setLoading(false);
    setActiveAgentName(null);

    if (res.error) {
      setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
    } else if (res.data) {
      setTransportData(res.data);
      setWizardStep('transport');
    }
  };

  // ─── Stage 3: Run Stay & Activity Agent ──────────────────────────────────
  const handleRunStage3 = async () => {
    setLoading(true);
    setError(null);
    setActiveAgentName('Agent 3: Stay & Activity Specialist (Curating hotels, daily sights & live weather)');

    const res = await planStageStayActivity({
      destination: selectedDestination,
      start_date: startDate,
      end_date: endDate,
      travelers: Number(travelers),
      travel_style: travelStyle,
      interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
      currency: currency,
    });

    setLoading(false);
    setActiveAgentName(null);

    if (res.error) {
      setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
    } else if (res.data) {
      setStayData(res.data);
      setWizardStep('stay');
    }
  };

  const handleSelectHotel = (hotel: Accommodation) => {
    if (!stayData) return;
    const durationDays = Math.max(1, Math.round((new Date(endDate).getTime() - new Date(startDate).getTime()) / (1000 * 60 * 60 * 24)));
    const nights = Math.max(1, durationDays - 1);
    const roomsNeeded = Math.max(1, Math.ceil(Number(travelers) / 2));
    const roomSuffix = ` (${roomsNeeded} room${roomsNeeded > 1 ? 's' : ''} for ${travelers} guest${Number(travelers) > 1 ? 's' : ''})`;
    const updatedName = `${hotel.name}${roomSuffix}`;
    const unitPrice = hotel.cost_per_night || 2000;
    const nightlyTotal = unitPrice * roomsNeeded;
    const totalCost = nightlyTotal * nights;

    setStayData({
      ...stayData,
      stay_activity: {
        ...stayData.stay_activity,
        accommodation_name: updatedName,
        accommodation_category: hotel.category || 'midscale',
        cost_per_night: nightlyTotal,
        total_accommodation_cost: totalCost,
      },
    });
  };

  // ─── Stage 4: Run Budget Agent ──────────────────────────────────────────
  const handleRunStage4 = async () => {
    if (!transportData || !stayData) return;
    setLoading(true);
    setError(null);
    setActiveAgentName('Agent 4: Budget Specialist (Auditing itemized expenses & 8% emergency buffer)');

    const res = await planStageBudget({
      transport_cost: transportData.transport.total_cost,
      accommodation_cost: stayData.stay_activity.total_accommodation_cost,
      activities_cost: stayData.stay_activity.total_activities_cost,
      food_cost: stayData.stay_activity.total_food_cost,
      budget_max: budgetMax !== '' ? Number(budgetMax) : null,
      currency: currency,
    });

    setLoading(false);
    setActiveAgentName(null);

    if (res.error) {
      setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
    } else if (res.data) {
      setBudgetData(res.data);
      setWizardStep('budget');
    }
  };

  // ─── Stage 5: Run Itinerary Agent & Finalize ────────────────────────────
  const handleRunStage5 = async () => {
    if (!transportData || !stayData || !budgetData) return;
    setLoading(true);
    setError(null);
    setActiveAgentName('Agent 5: Itinerary Specialist (Synthesizing master narrative with OpenRouter AI)');

    const preferencesPayload: TripPreferences = {
      origin: origin.trim(),
      destinations: [selectedDestination],
      start_date: startDate,
      end_date: endDate,
      budget_max: budgetMax !== '' ? Number(budgetMax) : null,
      currency: currency,
      travelers: Number(travelers),
      travel_style: travelStyle,
      preferred_transport: preferredTransport,
      interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
    };

    const res = await planStageItinerary({
      preferences: preferencesPayload,
      destination: selectedDestination,
      transport: transportData.transport,
      stay_activity: stayData.stay_activity,
      budget: budgetData,
      weather: stayData.weather,
      route_estimate: transportData.route_estimate,
      rag_sources: stayData.rag_sources,
      destination_guidance: stayData.destination_guidance,
    });

    setLoading(false);
    setActiveAgentName(null);

    if (res.error) {
      setError(typeof res.error === 'string' ? res.error : JSON.stringify(res.error));
    } else if (res.data) {
      setResult(res.data);
      setWizardStep('final');
    }
  };

  const stepsList = [
    { key: 'setup', label: '1. Setup' },
    { key: 'destination', label: '2. Destination' },
    { key: 'transport', label: '3. Transport' },
    { key: 'stay', label: '4. Stays & Sights' },
    { key: 'budget', label: '5. Budget' },
    { key: 'final', label: '6. Master Itinerary' },
  ];

  const currentStepIdx = stepsList.findIndex((s) => s.key === wizardStep);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="planner-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md overflow-y-auto"
    >
      <div className="relative w-full max-w-4xl max-h-[92vh] overflow-y-auto glass bg-surface-900 border border-white/10 rounded-3xl p-6 sm:p-8 text-white shadow-2xl animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <span className="text-2xl" aria-hidden="true">✈️</span>
            <div>
              <h2 id="planner-modal-title" className="text-xl sm:text-2xl font-bold gradient-text">
                {result ? 'Your AI Travel Plan' : 'Multi-Agent Sequential Travel Planner'}
              </h2>
              <p className="text-xs text-surface-100/50">
                {wizardStep === 'setup' && 'Configure traveler preferences to begin'}
                {wizardStep === 'destination' && 'Step 1/5: Review & Validate Destination Candidates'}
                {wizardStep === 'transport' && 'Step 2/5: Review Transit Corridors & Fares'}
                {wizardStep === 'stay' && 'Step 3/5: Review Curated Lodging & Daily Activities'}
                {wizardStep === 'budget' && 'Step 4/5: Audit Itemized Expenses & Emergency Buffer'}
                {wizardStep === 'final' && 'Complete AI Master Itinerary & Persistence'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-surface-100/60 hover:text-white rounded-xl hover:bg-white/10 transition-colors"
            aria-label="Close planner modal"
          >
            ✕
          </button>
        </div>

        {/* Stepper Progress Bar */}
        <div className="py-3 px-1 border-b border-white/10 flex items-center justify-between overflow-x-auto gap-2">
          {stepsList.map((st, idx) => {
            const isActive = st.key === wizardStep;
            const isCompleted = idx < currentStepIdx;
            return (
              <div key={st.key} className="flex items-center gap-1.5 shrink-0">
                <span
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                    isActive
                      ? 'bg-primary-500 text-white shadow-glow'
                      : isCompleted
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : 'bg-white/5 text-surface-100/40 border border-white/10'
                  }`}
                >
                  {isCompleted ? '✓' : idx + 1}
                </span>
                <span
                  className={`text-xs font-medium ${
                    isActive ? 'text-white font-bold' : isCompleted ? 'text-surface-100/80' : 'text-surface-100/40'
                  }`}
                >
                  {st.label}
                </span>
                {idx < stepsList.length - 1 && <span className="text-white/20 ml-2">→</span>}
              </div>
            );
          })}
        </div>

        {/* Error Banner */}
        {error && (
          <div
            role="alert"
            className="mt-4 p-4 rounded-xl bg-red-500/20 border border-red-500/40 text-red-200 text-sm flex items-start justify-between gap-2 animate-fade-in"
          >
            <div>
              <span className="font-semibold block">⚠️ Planning Request Error:</span>
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

        {/* Loading Spinner with Agent Mission */}
        {loading && (
          <div className="my-8 p-6 rounded-2xl bg-white/5 border border-primary-500/30 flex flex-col items-center justify-center gap-3 animate-pulse text-center">
            <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
            <h4 className="text-base font-bold text-white">{activeAgentName || 'Agent Working…'}</h4>
            <p className="text-xs text-surface-100/60 max-w-md">
              Validating deterministic constraints, retrieving RAG knowledge, and generating structured output.
            </p>
          </div>
        )}

        {/* ─── STEP 0: SETUP FORM ───────────────────────────────────────────── */}
        {wizardStep === 'setup' && !loading && (
          <form onSubmit={handleBatchSubmit} className="mt-6 space-y-6">
            {/* Quick Presets */}
            <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10">
              <span className="text-[11px] font-semibold text-surface-100/60 uppercase tracking-wider block mb-2">
                ⚡ Quick Trip Presets:
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'Tokyo, Japan',
                      'Kyoto, Japan',
                      'USD',
                      2800,
                      'cultural',
                      'train',
                      'temples, matcha, history, zen gardens',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-all cursor-pointer"
                >
                  🇯🇵 Kyoto Cultural ($)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'New Delhi, India',
                      'Kasol, India',
                      'INR',
                      22000,
                      'adventure',
                      'bus',
                      'trekking, parvati river, cafes, pine trails',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-primary-600/30 hover:bg-primary-600/50 border border-primary-500/40 text-primary-200 transition-all cursor-pointer"
                >
                  🇮🇳 Kasol Parvati Trail (₹)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'Milan, Italy',
                      'Rome, Italy',
                      'EUR',
                      2200,
                      'cultural',
                      'train',
                      'colosseum, vatican, pasta, architecture',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-all cursor-pointer"
                >
                  🇮🇹 Rome Highlights (€)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'London, UK',
                      'Paris, France',
                      'EUR',
                      1800,
                      'romantic',
                      'train',
                      'louvre, eiffel tower, cafes, pastry',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-all cursor-pointer"
                >
                  🇫🇷 Paris Romance (€)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleApplyPreset(
                      'Jakarta, Indonesia',
                      'Bali, Indonesia',
                      'USD',
                      1900,
                      'relaxation',
                      'flight',
                      'beaches, ubud rice terraces, snorkeling, temples',
                    )
                  }
                  className="text-xs px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-white transition-all cursor-pointer"
                >
                  🇮🇩 Bali Wellness ($)
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">Origin City *</label>
                <input
                  type="text"
                  required
                  value={origin}
                  onChange={(e) => setOrigin(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                  placeholder="e.g. New Delhi, India"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Preferred Destination (Optional)
                </label>
                <input
                  type="text"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                  placeholder="e.g. Kasol, India (or leave empty for AI selection)"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">Start Date *</label>
                <input
                  type="date"
                  required
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">End Date *</label>
                <input
                  type="date"
                  required
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                  Maximum Budget ({currSymbol})
                </label>
                <input
                  type="number"
                  min="50"
                  value={budgetMax}
                  onChange={(e) => setBudgetMax(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                  placeholder={currency === 'INR' ? 'e.g. 25000' : 'e.g. 2500'}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">Currency</label>
                <select
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-800 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="USD">USD ($ - US Dollar)</option>
                  <option value="INR">INR (₹ - Indian Rupee)</option>
                  <option value="EUR">EUR (€ - Euro)</option>
                  <option value="GBP">GBP (£ - British Pound)</option>
                  <option value="JPY">JPY (¥ - Japanese Yen)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">Travelers</label>
                <input
                  type="number"
                  min="1"
                  max="50"
                  value={travelers}
                  onChange={(e) => setTravelers(Math.max(1, Number(e.target.value)))}
                  className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">Travel Style</label>
                <select
                  value={travelStyle}
                  onChange={(e) => setTravelStyle(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-800 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="cultural">Cultural & Historic</option>
                  <option value="relaxation">Relaxation & Wellness</option>
                  <option value="adventure">Outdoor & Adventure</option>
                  <option value="budget">Budget Backpacker</option>
                  <option value="luxury">Luxury & Fine Living</option>
                  <option value="romantic">Romantic Getaway</option>
                  <option value="family">Family Friendly</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-surface-100/70 mb-1">Preferred Transport</label>
                <select
                  value={preferredTransport}
                  onChange={(e) => setPreferredTransport(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl bg-surface-800 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                >
                  <option value="mixed">Mixed (Flight / Train / Bus)</option>
                  <option value="flight">Flight</option>
                  <option value="train">Train</option>
                  <option value="bus">Bus / Coach</option>
                  <option value="car">Car / Drive</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-surface-100/70 mb-1">
                Interests & Keywords (comma-separated)
              </label>
              <input
                type="text"
                value={interests}
                onChange={(e) => setInterests(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:border-primary-500"
                placeholder="e.g. trekking, rivers, cafes, local culture"
              />
            </div>

            <div className="pt-4 flex flex-wrap items-center justify-between gap-3 border-t border-white/10">
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl border border-white/10 text-sm text-surface-100/70 hover:text-white hover:border-white/20 transition-colors"
              >
                Cancel
              </button>

              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  className="px-5 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm font-semibold transition-all cursor-pointer"
                >
                  ⚡ Generate AI Itinerary (1-Click)
                </button>
                <button
                  type="button"
                  onClick={handleRunStage1}
                  className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-bold transition-all shadow-glow active:scale-95 cursor-pointer flex items-center gap-2"
                >
                  <span>🚀 Start Step-by-Step Wizard</span>
                  <span>→</span>
                </button>
              </div>
            </div>
          </form>
        )}

        {/* ─── STEP 1: DESTINATION AGENT OUTPUT REVIEW ──────────────────────── */}
        {wizardStep === 'destination' && destinationData && !loading && (
          <div className="mt-6 space-y-5 animate-fade-in">
            <div className="p-4 rounded-2xl bg-primary-600/15 border border-primary-500/30 flex items-start gap-3">
              <span className="text-3xl">🗺️</span>
              <div>
                <h3 className="text-base font-bold text-white">Agent 1: Destination Specialist Matchmaking</h3>
                <p className="text-xs text-surface-100/70 mt-1 leading-relaxed">
                  {destinationData.rationale}
                </p>
              </div>
            </div>

            {/* Custom Destination Input */}
            <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 space-y-1.5">
              <label className="block text-xs font-semibold text-surface-100/70">
                Selected Destination (Click any candidate card below or edit directly):
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={selectedDestination}
                  onChange={(e) => setSelectedDestination(e.target.value)}
                  placeholder="e.g. Ghaziabad, India or Kyoto, Japan"
                  className="flex-1 px-4 py-2.5 rounded-xl bg-surface-900 border border-white/20 text-white text-sm focus:outline-none focus:border-primary-500 font-medium"
                />
              </div>
            </div>

            <div>
              <span className="text-xs font-semibold text-surface-100/70 uppercase tracking-wider block mb-3">
                Or Choose from Ranked Candidates & Alternatives:
              </span>
              <div className="grid gap-3 sm:grid-cols-2">
                {destinationData.candidates.map((cand) => {
                  const isSelected = selectedDestination === cand.name;
                  return (
                    <div
                      key={cand.name}
                      onClick={() => setSelectedDestination(cand.name)}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer text-left ${
                        isSelected
                          ? 'bg-primary-600/25 border-primary-500 ring-2 ring-primary-500/30'
                          : 'bg-white/5 border-white/10 hover:border-white/20 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-bold text-white text-sm">{cand.name}</span>
                        <span className="text-xs px-2 py-0.5 rounded-full font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          {cand.match_score.toFixed(0)}% Match
                        </span>
                      </div>
                      <p className="text-xs text-surface-100/60 mb-2">{cand.why_matched}</p>
                      <div className="flex flex-wrap gap-1.5">
                        {cand.highlights.slice(0, 3).map((h) => (
                          <span key={h} className="text-[10px] px-2 py-0.5 rounded-md bg-white/10 text-surface-100/70">
                            {h}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="pt-4 flex items-center justify-between border-t border-white/10">
              <button
                type="button"
                onClick={() => setWizardStep('setup')}
                className="px-5 py-2.5 rounded-xl border border-white/10 text-sm text-surface-100/70 hover:text-white"
              >
                ← Back to Preferences
              </button>
              <button
                type="button"
                onClick={handleRunStage2}
                className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-bold shadow-glow flex items-center gap-2 cursor-pointer"
              >
                <span>Confirm: {selectedDestination} & Plan Transit</span>
                <span>→</span>
              </button>
            </div>
          </div>
        )}

        {/* ─── STEP 2: TRANSPORT AGENT OUTPUT REVIEW ────────────────────────── */}
        {wizardStep === 'transport' && transportData && !loading && (
          <div className="mt-6 space-y-5 animate-fade-in">
            <div className="p-4 rounded-2xl bg-sky-600/15 border border-sky-500/30 flex items-start gap-3">
              <span className="text-3xl">🚆</span>
              <div>
                <h3 className="text-base font-bold text-white">Agent 2: Transit & Corridor Routing</h3>
                <p className="text-xs text-surface-100/70 mt-1">
                  Estimated round-trip route between <span className="text-white font-medium">{origin}</span> and{' '}
                  <span className="text-white font-medium">{selectedDestination}</span> for {travelers} traveler(s).
                </p>
              </div>
            </div>

            {/* Route Stats */}
            {transportData.route_estimate && (
              <div className="p-3.5 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between text-xs">
                <div>
                  <span className="text-surface-100/50 block">Transit Distance & Time</span>
                  <span className="font-bold text-white text-sm">
                    {transportData.route_estimate.distance_km.toLocaleString()} km (~
                    {transportData.route_estimate.duration_hours}h {transportData.route_estimate.mode})
                  </span>
                </div>
                <span
                  className={`text-[10px] px-2.5 py-1 rounded-full font-bold border ${
                    transportData.route_estimate.is_live
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                  }`}
                >
                  {transportData.route_estimate.is_live ? '🟢 Verified Live' : 'Estimated Baseline'}
                </span>
              </div>
            )}

            {/* Transit Legs */}
            <div className="space-y-3">
              <span className="text-xs font-semibold text-surface-100/70 uppercase tracking-wider block">
                Estimated Transit Legs:
              </span>
              {transportData.transport.legs.map((leg, idx) => (
                <div key={idx} className="p-4 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{leg.mode === 'flight' ? '✈️' : leg.mode === 'train' ? '🚆' : leg.mode === 'car' ? '🚗' : '🚌'}</span>
                    <div>
                      <span className="text-xs font-bold text-white block">
                        {leg.origin} → {leg.destination}
                      </span>
                      <span className="text-[11px] text-surface-100/70 block">
                        {leg.departure ? `${leg.departure} → ${leg.arrival}` : ''}
                      </span>
                      {leg.notes && (
                        <span className="text-[10px] text-primary-300/90 block mt-0.5">
                          {leg.notes}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-bold text-white block">
                      {currSymbol}
                      {leg.cost_estimate?.toFixed(2)}
                    </span>
                    <span className="text-[10px] text-surface-100/40 uppercase">{leg.mode}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-3.5 rounded-2xl bg-primary-600/10 border border-primary-500/20 flex items-center justify-between text-xs">
              <span className="text-surface-100/70">Total Estimated Round-Trip Transit:</span>
              <span className="text-base font-extrabold gradient-text">
                {currSymbol}
                {transportData.transport.total_cost.toFixed(2)} {currency}
              </span>
            </div>

            <div className="pt-4 flex items-center justify-between border-t border-white/10">
              <button
                type="button"
                onClick={() => setWizardStep('destination')}
                className="px-5 py-2.5 rounded-xl border border-white/10 text-sm text-surface-100/70 hover:text-white"
              >
                ← Back to Destination
              </button>
              <button
                type="button"
                onClick={handleRunStage3}
                className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-bold shadow-glow flex items-center gap-2 cursor-pointer"
              >
                <span>Confirm Transit & Curate Lodging</span>
                <span>→</span>
              </button>
            </div>
          </div>
        )}

        {/* ─── STEP 3: STAY & ACTIVITY AGENT OUTPUT REVIEW ──────────────────── */}
        {wizardStep === 'stay' && stayData && !loading && (
          <div className="mt-6 space-y-5 animate-fade-in">
            <div className="p-4 rounded-2xl bg-amber-600/15 border border-amber-500/30 flex items-start gap-3">
              <span className="text-3xl">🏨</span>
              <div>
                <h3 className="text-base font-bold text-white">Agent 3: Lodging, Activities & Weather</h3>
                <p className="text-xs text-surface-100/70 mt-1">
                  Curated accommodation, daily highlights, and weather forecasts for {selectedDestination}.
                </p>
              </div>
            </div>

            {/* Hotel & Weather Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                <span className="text-[10px] uppercase font-bold text-surface-100/40 block mb-1">
                  Selected Accommodation
                </span>
                <h4 className="text-sm font-bold text-white">{stayData.stay_activity.accommodation_name}</h4>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] px-2 py-0.5 rounded-md font-semibold bg-primary-500/20 text-primary-300">
                    {stayData.stay_activity.accommodation_category.toUpperCase()}
                  </span>
                  <span className="text-xs text-surface-100/70">
                    {currSymbol}
                    {stayData.stay_activity.cost_per_night.toFixed(2)} / night
                  </span>
                </div>
                <p className="text-[11px] text-surface-100/50 mt-2">
                  Total Lodging: {currSymbol}
                  {stayData.stay_activity.total_accommodation_cost.toFixed(2)}
                </p>
              </div>

              {stayData.weather && (
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] uppercase font-bold text-surface-100/40">Weather Forecast</span>
                    <span
                      className={`text-[9px] px-2 py-0.5 rounded-full font-bold border ${
                        stayData.weather.is_live
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}
                    >
                      {stayData.weather.is_live ? '🟢 Verified Live' : 'Estimated Seasonal'}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold text-white">
                    {stayData.weather.temperature_c}°C — {stayData.weather.condition}
                  </h4>
                  <p className="text-[11px] text-surface-100/60 mt-1">{stayData.weather.summary}</p>
                </div>
              )}
            </div>

            {/* List of Real Hotels in Destination */}
            {stayData.stay_activity.hotel_options && stayData.stay_activity.hotel_options.length > 0 && (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-surface-100/70 uppercase tracking-wider block">
                    Available Hotels in {selectedDestination} ({stayData.stay_activity.hotel_options.length} Verified Properties):
                  </span>
                  <span className="text-[10px] text-surface-100/50">Click &apos;Select Hotel&apos; to switch lodging</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {stayData.stay_activity.hotel_options.map((h, idx) => {
                    const isSelected = stayData.stay_activity.accommodation_name.includes(h.name);
                    return (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-2xl border transition-all flex flex-col justify-between ${
                          isSelected
                            ? 'bg-primary-950/40 border-primary-500/50 shadow-glow'
                            : 'bg-white/5 border-white/10 hover:border-white/20'
                        }`}
                      >
                        <div>
                          <div className="flex items-start justify-between gap-2">
                            <h5 className="text-xs font-bold text-white leading-tight">{h.name}</h5>
                            <span className="text-[10px] px-2 py-0.5 rounded-md font-semibold bg-primary-500/20 text-primary-300 uppercase shrink-0">
                              {h.category}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-1.5 text-[11px] text-surface-100/70">
                            <span>⭐ {h.rating?.toFixed(1) || '4.2'}</span>
                            <span>•</span>
                            <span className="font-bold text-white">
                              {currSymbol}{h.cost_per_night?.toFixed(2)}
                            </span>
                            <span className="text-surface-100/50 text-[10px]">/ room / night</span>
                          </div>
                          {h.amenities && h.amenities.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-2">
                              {h.amenities.slice(0, 3).map((am, aIdx) => (
                                <span key={aIdx} className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-surface-100/60 border border-white/5">
                                  {am}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="pt-3 mt-2 border-t border-white/10 flex items-center justify-between gap-2">
                          {h.booking_url ? (
                            <a
                              href={h.booking_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[11px] text-sky-400 hover:text-sky-300 font-semibold inline-flex items-center gap-1"
                            >
                              <span>🔗 View on Google Travel</span>
                              <span className="text-[9px]">↗</span>
                            </a>
                          ) : (
                            <span className="text-[10px] text-surface-100/40 italic">Direct Booking Available</span>
                          )}
                          <button
                            type="button"
                            onClick={() => handleSelectHotel(h)}
                            className={`px-2.5 py-1 rounded-xl text-[11px] font-semibold transition-all cursor-pointer ${
                              isSelected
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                                : 'bg-white/10 hover:bg-white/15 text-white border border-white/10'
                            }`}
                          >
                            {isSelected ? '✓ Selected' : 'Select Hotel'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Curated Activities */}
            <div>
              <span className="text-xs font-semibold text-surface-100/70 uppercase tracking-wider block mb-2">
                Curated Excursions & Sights:
              </span>
              <div className="space-y-2.5">
                {stayData.stay_activity.activities.map((act, idx) => (
                  <div key={idx} className="p-3.5 rounded-2xl bg-white/5 border border-white/10 flex items-start justify-between text-xs gap-3">
                    <div className="space-y-1">
                      <span className="font-bold text-white block text-sm">{act.name}</span>
                      <p className="text-surface-100/75 text-xs leading-relaxed">{act.description}</p>
                      {act.source_url && (
                        <a
                          href={act.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 mt-1 text-[11px] text-sky-400 hover:text-sky-300 font-medium bg-white/5 px-2 py-0.5 rounded-md border border-white/10"
                        >
                          <span>🔗</span>
                          <span>Source: {act.source_label || 'Wikipedia & Historic Record'}</span>
                          <span className="text-[9px]">↗</span>
                        </a>
                      )}
                    </div>
                    <span className="font-bold text-emerald-400 shrink-0 ml-2 text-sm">
                      {act.cost_estimate === 0 ? 'Free' : `${currSymbol}${act.cost_estimate?.toFixed(2)}`}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 flex items-center justify-between border-t border-white/10">
              <button
                type="button"
                onClick={() => setWizardStep('transport')}
                className="px-5 py-2.5 rounded-xl border border-white/10 text-sm text-surface-100/70 hover:text-white"
              >
                ← Back to Transport
              </button>
              <button
                type="button"
                onClick={handleRunStage4}
                className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-bold shadow-glow flex items-center gap-2 cursor-pointer"
              >
                <span>Confirm Lodging & Audit Budget</span>
                <span>→</span>
              </button>
            </div>
          </div>
        )}

        {/* ─── STEP 4: BUDGET AGENT OUTPUT REVIEW ───────────────────────────── */}
        {wizardStep === 'budget' && budgetData && !loading && (
          <div className="mt-6 space-y-5 animate-fade-in">
            <div className="p-4 rounded-2xl bg-emerald-600/15 border border-emerald-500/30 flex items-start gap-3">
              <span className="text-3xl">💰</span>
              <div>
                <h3 className="text-base font-bold text-white">Agent 4: Deterministic Budget Audit</h3>
                <p className="text-xs text-surface-100/70 mt-1">
                  Pure Python financial arithmetic with an 8% emergency contingency buffer.
                </p>
              </div>
            </div>

            {/* Status Alert */}
            <div
              className={`p-4 rounded-2xl border flex items-center justify-between ${
                budgetData.is_within_budget
                  ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-200'
                  : 'bg-amber-500/15 border-amber-500/30 text-amber-200'
              }`}
            >
              <div>
                <span className="font-bold text-sm block">
                  {budgetData.is_within_budget ? '🟢 Within Budget Target' : '⚠️ Exceeds Budget Target'}
                </span>
                <span className="text-xs opacity-80">
                  {budgetData.is_within_budget
                    ? `Total expenses are well within your limit of ${currSymbol}${budgetMax}`
                    : `Total exceeds target by ${currSymbol}${budgetData.overflow_amount.toFixed(2)}`}
                </span>
              </div>
              <span className="text-xl font-black">
                {currSymbol}
                {budgetData.breakdown.total.toFixed(2)}
              </span>
            </div>

            {/* Itemized Table */}
            <div className="p-4 rounded-2xl bg-white/5 border border-white/10 space-y-2.5 text-xs">
              <div className="flex justify-between py-1 border-b border-white/5 text-surface-100/70">
                <span>🚆 Transport & Transit:</span>
                <span className="font-semibold text-white">
                  {currSymbol}
                  {budgetData.breakdown.transport.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5 text-surface-100/70">
                <span>🏨 Lodging & Accommodation:</span>
                <span className="font-semibold text-white">
                  {currSymbol}
                  {budgetData.breakdown.accommodation.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5 text-surface-100/70">
                <span>🎟️ Sights & Activities:</span>
                <span className="font-semibold text-white">
                  {currSymbol}
                  {budgetData.breakdown.activities.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5 text-surface-100/70">
                <span>🍽️ Food & Dining Allowance:</span>
                <span className="font-semibold text-white">
                  {currSymbol}
                  {budgetData.breakdown.food_estimate.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-white/5 text-surface-100/70">
                <span>🛡️ Emergency Contingency Buffer (8%):</span>
                <span className="font-semibold text-amber-300">
                  {currSymbol}
                  {budgetData.breakdown.miscellaneous.toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between pt-2 text-sm font-bold text-white">
                <span>Total Estimated Cost:</span>
                <span className="gradient-text text-base">
                  {currSymbol}
                  {budgetData.breakdown.total.toFixed(2)} {currency}
                </span>
              </div>
            </div>

            {/* Reduction proposals if over budget */}
            {budgetData.reduction_proposals.length > 0 && (
              <div className="p-4 rounded-2xl bg-white/5 border border-white/10 space-y-2">
                <span className="text-xs font-semibold text-surface-100/70 uppercase tracking-wider block">
                  Recommended Optimizations:
                </span>
                {budgetData.reduction_proposals.map((prop, idx) => (
                  <div key={idx} className="p-2.5 rounded-xl bg-white/5 flex items-center justify-between text-xs">
                    <div>
                      <span className="font-semibold text-white">{prop.action}</span>
                      <p className="text-[11px] text-surface-100/50">{prop.description}</p>
                    </div>
                    <span className="font-bold text-emerald-400">-{currSymbol}{prop.estimated_savings.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="pt-4 flex items-center justify-between border-t border-white/10">
              <button
                type="button"
                onClick={() => setWizardStep('stay')}
                className="px-5 py-2.5 rounded-xl border border-white/10 text-sm text-surface-100/70 hover:text-white"
              >
                ← Back to Lodging
              </button>
              <button
                type="button"
                onClick={handleRunStage5}
                className="px-6 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-bold shadow-glow flex items-center gap-2 cursor-pointer"
              >
                <span>Approve Budget & Synthesize Master Itinerary</span>
                <span>→</span>
              </button>
            </div>
          </div>
        )}

        {/* ─── STEP 5: FINAL MASTER ITINERARY VIEW ──────────────────────────── */}
        {wizardStep === 'final' && result && !loading && (
          <div className="mt-6 space-y-6 animate-fade-in">
            {/* Top Bar with ID and Copy */}
            <div className="flex flex-wrap items-center justify-between gap-3 p-4 rounded-2xl bg-white/5 border border-white/10">
              <div>
                <span className="text-[10px] uppercase font-bold tracking-wider text-surface-100/40 block">
                  Trip Identifier (Persisted to Store)
                </span>
                <span className="font-mono text-sm text-white font-bold">ID: {result.trip_id}</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopyId}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-white/10 hover:bg-white/20 text-white transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <span>{copied ? '✓ Copied!' : '📋 Copy ID'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setResult(null);
                    setWizardStep('setup');
                  }}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-primary-600/30 hover:bg-primary-600/50 text-primary-200 border border-primary-500/30 transition-all cursor-pointer"
                >
                  Plan Another Trip
                </button>
              </div>
            </div>

            {/* AI Summary Banner */}
            <div className="p-5 rounded-2xl bg-primary-600/10 border border-primary-500/30">
              <span className="text-[10px] uppercase font-bold tracking-wider text-primary-400 block mb-1">
                AI Agent Master Synthesis
              </span>
              <p className="text-sm sm:text-base text-white/95 leading-relaxed font-medium">
                {result.summary}
              </p>
            </div>

            {/* Curated Destination Guidance (RAG Verified) */}
            {((result.destination_guidance && result.destination_guidance.length > 0) ||
              (result.rag_sources && result.rag_sources.length > 0)) && (
              <div className="p-4 rounded-2xl bg-primary-950/40 border border-primary-500/20 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-primary-300 flex items-center gap-1.5">
                    <span>📚</span> Curated Destination Guidance (RAG Verified)
                  </span>
                  {result.rag_sources && result.rag_sources.length > 0 && (
                    <span className="text-[10px] text-surface-100/50">
                      {result.rag_sources.length} guidebook source(s)
                    </span>
                  )}
                </div>

                {result.destination_guidance && result.destination_guidance.length > 0 && (
                  <ul className="space-y-2 text-xs text-surface-100/70">
                    {result.destination_guidance.map((guide, idx) => (
                      <li key={idx} className="bg-white/5 p-2.5 rounded-xl border border-white/5">
                        {guide}
                      </li>
                    ))}
                  </ul>
                )}

                {result.rag_sources && result.rag_sources.length > 0 && (
                  <div className="pt-2 border-t border-white/10 flex flex-wrap gap-1.5 items-center">
                    <span className="text-[10px] text-surface-100/40 uppercase font-semibold">Sources:</span>
                    {result.rag_sources.map((src, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-white/10 text-surface-100/80 border border-white/10"
                      >
                        {src}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Weather & Transit Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Weather Forecast */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-surface-100/80 flex items-center gap-1.5">
                    <span>🌦️</span> Weather Forecast
                  </span>
                  {result.weather && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                        result.weather.is_live
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}
                    >
                      {result.weather.is_live ? '🟢 Verified Live' : 'Estimated Seasonal'}
                    </span>
                  )}
                </div>

                {result.weather ? (
                  <div className="space-y-1 text-xs text-surface-100/70">
                    <p className="text-white font-medium text-sm">
                      {result.weather.temperature_c}°C — {result.weather.condition}
                    </p>
                    <p className="text-xs text-surface-100/60 leading-relaxed">{result.weather.summary}</p>
                    <p className="text-[11px] text-surface-100/60">Source: {result.weather.provider_name}</p>
                  </div>
                ) : (
                  <p className="text-xs text-surface-100/50 italic">
                    Live weather forecast currently unavailable for this destination.
                  </p>
                )}
              </div>

              {/* Transit & Routing */}
              <div className="p-4 rounded-2xl bg-white/5 border border-white/10">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-surface-100/80 flex items-center gap-1.5">
                    <span>🗺️</span> Transit & Route Estimate
                  </span>
                  {result.route_estimate && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border ${
                        result.route_estimate.is_live
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}
                    >
                      {result.route_estimate.is_live ? '🟢 Verified Route' : 'Estimated Baseline'}
                    </span>
                  )}
                </div>

                {result.route_estimate ? (
                  <div className="space-y-1 text-xs text-surface-100/70">
                    <p className="text-white font-medium text-sm">
                      {result.route_estimate.distance_km.toLocaleString()} km (~
                      {result.route_estimate.duration_hours}h {result.route_estimate.mode})
                    </p>
                    <p className="text-xs text-surface-100/60 leading-relaxed">
                      {result.route_estimate.route_summary}
                    </p>
                    <p className="text-[11px] text-surface-100/60">Source: {result.route_estimate.provider_name}</p>
                  </div>
                ) : (
                  <p className="text-xs text-surface-100/50 italic">
                    Direct route estimation unavailable.
                  </p>
                )}
              </div>
            </div>

            {/* Budget Breakdown */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Budget Breakdown</h3>
                <span className="text-[10px] text-surface-100/50 italic">
                  *Curated prices remain estimates unless verified live
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-2 text-center text-xs">
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Transit</span>
                  <span className="font-semibold text-white">
                    {currSymbol}{result.budget.transport.toFixed(2)}
                  </span>
                </div>
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Lodging</span>
                  <span className="font-semibold text-white">
                    {currSymbol}{result.budget.accommodation.toFixed(2)}
                  </span>
                </div>
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Activities</span>
                  <span className="font-semibold text-white">
                    {currSymbol}{result.budget.activities.toFixed(2)}
                  </span>
                </div>
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Dining (Est.)</span>
                  <span className="font-semibold text-white">
                    {currSymbol}{result.budget.food_estimate.toFixed(2)}
                  </span>
                </div>
                <div className="bg-white/5 p-2.5 rounded-xl">
                  <span className="text-surface-100/50 block text-[10px]">Misc (8%)</span>
                  <span className="font-semibold text-white">
                    {currSymbol}{result.budget.miscellaneous.toFixed(2)}
                  </span>
                </div>
                <div className="bg-primary-600/20 border border-primary-500/30 p-2.5 rounded-xl">
                  <span className="text-primary-300 block text-[10px] font-semibold">Total</span>
                  <span className="font-bold text-white text-sm">
                    {currSymbol}{result.budget.total.toFixed(2)}
                  </span>
                </div>
              </div>
            </div>

            {/* Daily Itinerary */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-white">Daily Itinerary</h3>
              <div className="space-y-3">
                {result.itinerary.map((day) => (
                  <div
                    key={day.day}
                    className="p-3.5 rounded-2xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors"
                  >
                    <div className="flex items-center justify-between text-xs font-semibold text-primary-400 mb-2">
                      <span>Day {day.day} — {day.date}</span>
                      {day.daily_budget && (
                        <span className="text-surface-100/50 font-normal">
                          Daily Target: {currSymbol}{day.daily_budget.toFixed(2)}
                        </span>
                      )}
                    </div>

                    {/* Accommodation */}
                    {day.accommodation && (
                      <div className="text-xs text-surface-100/70 mb-2 flex items-center justify-between flex-wrap gap-2">
                        <p>
                          🏨 <strong>Stay:</strong> {day.accommodation.name} ({currSymbol}{day.accommodation.cost_per_night}/night)
                        </p>
                        {day.accommodation.booking_url && (
                          <a
                            href={day.accommodation.booking_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[11px] text-sky-400 hover:text-sky-300 font-medium inline-flex items-center gap-1"
                          >
                            <span>🔗 View on Google Travel</span>
                            <span className="text-[9px]">↗</span>
                          </a>
                        )}
                      </div>
                    )}

                    {/* Transport legs */}
                    {day.transport && day.transport.length > 0 && (
                      <div className="text-xs text-surface-100/70 mb-2 space-y-1">
                        {day.transport.map((t, idx) => (
                          <p key={idx}>
                            🚆 <strong>Transit:</strong> {t.origin} → {t.destination} ({t.departure} - {t.arrival})
                          </p>
                        ))}
                      </div>
                    )}

                    {/* Activities */}
                    {day.activities && day.activities.length > 0 && (
                      <div className="space-y-2 pt-2 border-t border-white/5">
                        {day.activities.map((act, idx) => (
                          <div key={idx} className="p-2.5 rounded-xl bg-white/5 border border-white/5 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-bold text-white">📍 {act.name} ({act.duration_hours}h)</span>
                              <span className="font-semibold text-emerald-400 shrink-0">
                                {act.cost_estimate === 0 ? 'Free' : `${currSymbol}${act.cost_estimate ?? 0}`}
                              </span>
                            </div>
                            {act.description && (
                              <p className="text-[11px] text-surface-100/75 mt-1 leading-relaxed">
                                {act.description}
                              </p>
                            )}
                            {act.source_url && (
                              <a
                                href={act.source_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 mt-1.5 text-[10px] text-sky-400 hover:text-sky-300 font-medium"
                              >
                                <span>🔗</span>
                                <span>Source: {act.source_label || 'Wikipedia & Historic Record'}</span>
                                <span className="text-[9px]">↗</span>
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Footer action */}
            <div className="pt-4 flex justify-between items-center border-t border-white/10">
              <button
                type="button"
                onClick={() => {
                  setResult(null);
                  setWizardStep('setup');
                }}
                className="text-xs text-surface-100/60 hover:text-white transition-colors cursor-pointer"
              >
                ← Plan Another Trip
              </button>
              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-xs font-semibold text-white transition-colors cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
