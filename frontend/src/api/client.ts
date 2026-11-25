/**
 * TRIPPY API Client
 *
 * Configurable HTTP client for communicating with the TRIPPY backend.
 * Uses VITE_API_BASE_URL env var, falls back to '/api' (handled by Vite proxy in dev).
 */

const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? '/api';

interface RequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
  signal?: AbortSignal;
}

export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  status: number;
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<ApiResponse<T>> {
  const { method = 'GET', headers = {}, body, signal } = options;

  const url = `${API_BASE_URL}${endpoint}`;

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
    signal,
  };

  if (body !== undefined) {
    config.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, config);
    let data: any = null;
    const contentType =
      response.headers && typeof response.headers.get === 'function'
        ? response.headers.get('content-type') || ''
        : 'application/json';
    if (contentType.includes('application/json') || typeof response.json === 'function') {
      try {
        data = await response.json();
      } catch {
        data = null;
      }
    } else {
      const text = await response.text();
      data = { detail: text || `HTTP ${response.status}` };
    }

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}`;
      if (data && data.detail) {
        if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
        } else if (typeof data.detail === 'string') {
          errorMessage = data.detail;
        } else {
          errorMessage = JSON.stringify(data.detail);
        }
      }
      return {
        data: null,
        error: errorMessage,
        status: response.status,
      };
    }

    return { data: data as T, error: null, status: response.status };
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown network error';
    return { data: null, error: message, status: 0 };
  }
}

export const apiClient = {
  get: <T>(endpoint: string, signal?: AbortSignal) =>
    request<T>(endpoint, { signal }),

  post: <T>(endpoint: string, body: unknown, signal?: AbortSignal) =>
    request<T>(endpoint, { method: 'POST', body, signal }),

  put: <T>(endpoint: string, body: unknown, signal?: AbortSignal) =>
    request<T>(endpoint, { method: 'PUT', body, signal }),

  delete: <T>(endpoint: string, signal?: AbortSignal) =>
    request<T>(endpoint, { method: 'DELETE', signal }),
};

export interface WeatherForecast {
  destination: string;
  temperature_c: number;
  condition: string;
  precipitation_chance: number;
  summary: string;
  is_live: boolean;
  provider_name: string;
  recorded_at: string;
}

export interface RouteEstimate {
  origin: string;
  destination: string;
  distance_km: number;
  duration_hours: number;
  mode: string;
  is_live: boolean;
  provider_name: string;
  route_summary: string;
}

export interface Activity {
  name: string;
  location: string;
  date?: string;
  duration_hours?: number;
  cost_estimate?: number;
  description?: string;
  source_url?: string;
  source_label?: string;
}

export interface Accommodation {
  name: string;
  location: string;
  check_in?: string;
  check_out?: string;
  cost_per_night?: number;
  rating?: number;
  category?: string;
  booking_url?: string;
  source_url?: string;
  amenities?: string[];
}

export interface TransportLeg {
  mode: string;
  origin: string;
  destination: string;
  departure?: string;
  arrival?: string;
  cost_estimate?: number;
  notes?: string;
}

export interface DayPlan {
  day: number;
  date: string;
  activities: Activity[];
  accommodation?: Accommodation | null;
  transport: TransportLeg[];
  daily_budget?: number;
}

export interface BudgetBreakdown {
  currency?: string;
  transport: number;
  accommodation: number;
  activities: number;
  food_estimate: number;
  miscellaneous: number;
  total: number;
}

export interface TripPreferences {
  origin: string;
  destinations?: string[] | null;
  start_date: string;
  end_date: string;
  budget_min?: number | null;
  budget_max?: number | null;
  currency?: string;
  travelers?: number;
  travel_style?: string;
  preferred_transport?: string;
  interests?: string[];
  notes?: string | null;
}

export interface TripResult {
  trip_id: string;
  preferences: TripPreferences;
  destinations: string[];
  currency?: string;
  itinerary: DayPlan[];
  budget: BudgetBreakdown;
  summary: string;
  warnings: string[];
  weather?: WeatherForecast | null;
  route_estimate?: RouteEstimate | null;
  rag_sources?: string[];
  destination_guidance?: string[];
}

/** Health check convenience functions */
export interface HealthStatus {
  status: string;
  version: string;
}

export interface HealthReadyStatus {
  status: string;
  version: string;
  environment: string;
  rag_enabled: boolean;
  rag_documents_loaded: number;
  weather_provider: string;
  maps_provider: string;
  storage_writable: boolean;
  stored_trips_count: number;
}

export const checkHealth = () => apiClient.get<HealthStatus>('/health');
export const checkHealthReady = () => apiClient.get<HealthReadyStatus>('/health/ready');
export const planTrip = (preferences: TripPreferences) =>
  apiClient.post<TripResult>('/trips/plan', preferences);
export const getTrip = (tripId: string) =>
  apiClient.get<TripResult>(`/trips/${tripId}`);
export const listTrips = (limit = 10) =>
  apiClient.get<TripResult[]>(`/trips?limit=${limit}`);

// ─── Sequential Multi-Agent Stage Interfaces & APIs ──────────────────────

export interface DestinationCandidate {
  name: string;
  country: string;
  rank: number;
  match_score: number;
  highlights: string[];
  recommended_days: number;
  why_matched: string;
}

export interface DestinationAgentOutput {
  selected_destination: string;
  candidates: DestinationCandidate[];
  rationale: string;
}

export interface TransportAgentOutput {
  legs: TransportLeg[];
  total_cost: number;
  total_duration_hours: number;
  primary_mode: string;
  alternatives: string[];
}

export interface TransportStageResponse {
  transport: TransportAgentOutput;
  route_estimate?: RouteEstimate | null;
}

export interface StayActivityAgentOutput {
  accommodation_name: string;
  accommodation_category: string;
  cost_per_night: number;
  total_accommodation_cost: number;
  hotel_options?: Accommodation[];
  activities: Activity[];
  total_activities_cost: number;
  daily_food_cost: number;
  total_food_cost: number;
  food_highlights: string[];
}

export interface StayActivityStageResponse {
  stay_activity: StayActivityAgentOutput;
  weather?: WeatherForecast | null;
  rag_sources: string[];
  destination_guidance: string[];
}

export interface BudgetReductionProposal {
  category: string;
  action: string;
  estimated_savings: number;
  description: string;
}

export interface BudgetAgentOutput {
  breakdown: BudgetBreakdown;
  budget_max?: number | null;
  is_within_budget: boolean;
  overflow_amount: number;
  reduction_proposals: BudgetReductionProposal[];
  notes?: string;
}

export interface DestinationStageRequest {
  origin: string;
  destinations?: string[] | null;
  start_date: string;
  end_date: string;
  budget_max?: number | null;
  currency?: string;
  travel_style?: string;
  interests?: string[];
}

export interface TransportStageRequest {
  origin: string;
  destination: string;
  start_date: string;
  end_date: string;
  travelers?: number;
  preferred_transport?: string;
  travel_style?: string;
  currency?: string;
  refinement_level?: number;
}

export interface StayActivityStageRequest {
  destination: string;
  start_date: string;
  end_date: string;
  travelers?: number;
  travel_style?: string;
  interests?: string[];
  currency?: string;
  refinement_level?: number;
}

export interface BudgetStageRequest {
  transport_cost: number;
  accommodation_cost: number;
  activities_cost: number;
  food_cost: number;
  budget_max?: number | null;
  currency?: string;
}

export interface ItineraryStageRequest {
  preferences: TripPreferences;
  destination: string;
  transport: TransportAgentOutput;
  stay_activity: StayActivityAgentOutput;
  budget: BudgetAgentOutput;
  weather?: WeatherForecast | null;
  route_estimate?: RouteEstimate | null;
  rag_sources?: string[];
  destination_guidance?: string[];
}

export const planStageDestination = (data: DestinationStageRequest) =>
  apiClient.post<DestinationAgentOutput>('/trips/stages/destination', data);

export const planStageTransport = (data: TransportStageRequest) =>
  apiClient.post<TransportStageResponse>('/trips/stages/transport', data);

export const planStageStayActivity = (data: StayActivityStageRequest) =>
  apiClient.post<StayActivityStageResponse>('/trips/stages/stay-activity', data);

export const planStageBudget = (data: BudgetStageRequest) =>
  apiClient.post<BudgetAgentOutput>('/trips/stages/budget', data);

export const planStageItinerary = (data: ItineraryStageRequest) =>
  apiClient.post<TripResult>('/trips/stages/itinerary', data);



