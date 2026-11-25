import { useEffect, useState } from 'react';
import { Navbar, Footer, PlannerModal, SavedTripsModal } from './components';
import LandingPage from './pages/LandingPage';
import { getTrip } from './api';
import type { TripResult } from './api';

export default function App() {
  const [isPlannerOpen, setIsPlannerOpen] = useState(false);
  const [isSavedTripsOpen, setIsSavedTripsOpen] = useState(false);
  const [activeTrip, setActiveTrip] = useState<TripResult | null>(null);

  // Check URL query parameters on initial mount (e.g., ?trip=trip_xxx)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tripId = params.get('trip');
    if (tripId) {
      getTrip(tripId).then((res) => {
        if (res.data) {
          setActiveTrip(res.data);
          setIsPlannerOpen(true);
        }
      });
    }
  }, []);

  const handleOpenPlanner = () => {
    setActiveTrip(null);
    setIsPlannerOpen(true);
  };

  const handleSelectTrip = (trip: TripResult) => {
    setActiveTrip(trip);
    setIsSavedTripsOpen(false);
    setIsPlannerOpen(true);
  };

  return (
    <>
      <Navbar
        onOpenPlanner={handleOpenPlanner}
        onOpenSavedTrips={() => setIsSavedTripsOpen(true)}
      />
      <main>
        <LandingPage onOpenPlanner={handleOpenPlanner} />
      </main>
      <Footer />

      <PlannerModal
        isOpen={isPlannerOpen}
        onClose={() => {
          setIsPlannerOpen(false);
          setActiveTrip(null);
        }}
        initialResult={activeTrip}
      />

      <SavedTripsModal
        isOpen={isSavedTripsOpen}
        onClose={() => setIsSavedTripsOpen(false)}
        onSelectTrip={handleSelectTrip}
      />
    </>
  );
}
