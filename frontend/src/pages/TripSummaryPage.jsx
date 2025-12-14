import React, { useEffect, useState, useRef } from 'react';
import TripMap from '../components/TripMap';
import StaticTripMap from '../components/StaticTripMap';

function TripSummaryPage() {
  const [tripData, setTripData] = useState(null);
  const [history, setHistory] = useState([]);
  const [status, setStatus] = useState("Initializing...");
  const [wsConnected, setWsConnected] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Controls
  const [focusTrigger, setFocusTrigger] = useState(0); 
  const [focusLocation, setFocusLocation] = useState(null);
  
  // NEW: Map mode toggle (default to interactive)
  const [useInteractiveMap, setUseInteractiveMap] = useState(true);
  
  const wsRef = useRef(null);
  const USER_ID = "6933ecb10ef6129e479b90df";
  
  // Backend URL - Change this if your backend is on a different port
  const BACKEND_URL = "http://localhost:8000";

  // 1. Fetch History from Backend
  useEffect(() => {
    const fetchHistory = async () => {
      setStatus("Loading history...");
      setLoading(true);
      
      try {
        const response = await fetch(`${BACKEND_URL}/summary/history?user_id=${USER_ID}`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(`✅ Loaded ${data.length} trip(s) from backend`);
        
        setHistory(data);
        
        if (data.length > 0) {
          handleSelectTrip(data[0]);
          setStatus(`Loaded ${data.length} trip(s)`);
        } else {
          setStatus("No trips found - upload photos to create one!");
        }
        
      } catch (error) {
        console.error("❌ Error fetching history:", error);
        setStatus(`Error: ${error.message}`);
        setHistory([]);
      } finally {
        setLoading(false);
      }
    };
    
    fetchHistory();
  }, []);

  // 2. WebSocket for Real-time Updates
  useEffect(() => {
    const connectWS = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) return;
      
      try {
        const ws = new WebSocket(`ws://localhost:8000/ws/${USER_ID}`);
        wsRef.current = ws;

        ws.onopen = () => { 
          setWsConnected(true); 
          setStatus("Connected - Live updates enabled"); 
          console.log("✅ WebSocket connected");
        };
        
        ws.onmessage = (event) => {
          try {
            const newTrip = JSON.parse(event.data);
            console.log("📨 New trip received:", newTrip.trip_title);
            
            // Auto-select the new trip
            handleSelectTrip(newTrip);
            setStatus("🎉 New Trip Received!");
            
            // Add to history (avoid duplicates)
            setHistory(prev => {
              const exists = prev.find(t => 
                t.created_at === newTrip.created_at
              );
              if (exists) return prev;
              return [newTrip, ...prev];
            });
          } catch (e) { 
            console.error("WS Parse Error", e); 
          }
        };
        
        ws.onerror = (error) => {
          console.error("❌ WebSocket error:", error);
          setWsConnected(false);
        };
        
        ws.onclose = () => { 
          console.log("WebSocket closed, reconnecting in 3s...");
          setWsConnected(false); 
          setTimeout(connectWS, 3000); 
        };
      } catch (error) {
        console.error("❌ Failed to connect WebSocket:", error);
        setWsConnected(false);
      }
    };
    
    connectWS();
    
    return () => { 
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  // ⚡ HANDLER: Select Trip (Reset View)
  const handleSelectTrip = (trip) => {
    console.log("📍 Selecting trip:", trip.trip_title);
    setTripData(trip);
    setFocusTrigger(Date.now());
    setFocusLocation(null);
    setStatus(`Viewing: ${trip.trip_title}`);
  };

  // ⚡ HANDLER: Select Stop (Zoom In)
  const handleSelectStop = (point) => {
    console.log("🔍 Zooming to:", point);
    setFocusLocation([...point]); 
  };

  // NEW: Toggle between map modes
  const handleToggleMapMode = () => {
    setUseInteractiveMap(prev => !prev);
    // Log current trip data to debug
    if (tripData) {
      console.log('📊 Current trip data:', {
        map_data: tripData.map_data,
        map_image_url: tripData.map_image_url,
        points: tripData.points?.length
      });
    }
  };

  // Determine if we should show static map
  // User preference OR backend forces static mode
  const shouldUseStaticMap = !useInteractiveMap || tripData?.map_data?.type === 'static';

  return (
    <div className="flex h-screen bg-gray-100 overflow-hidden">
      
      {/* SIDEBAR */}
      <div className="w-80 bg-white shadow-xl flex flex-col z-20 border-r border-gray-200">
        <div className="p-4 bg-gradient-to-r from-blue-600 to-indigo-700 text-white shrink-0">
          <h2 className="font-bold text-lg flex items-center gap-2">🗺️ My Trips</h2>
          <div className="flex items-center gap-2 text-xs opacity-90 mt-1">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`}></div>
            <span>{wsConnected ? 'Live' : 'Offline'}</span>
          </div>
        </div>
        
        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-2 scrollbar-thin">
          
          {/* Loading State */}
          {loading && (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="text-sm text-gray-500 mt-2">Loading trips...</p>
            </div>
          )}
          
          {/* A. Current Trip Stops */}
          {!loading && tripData && !shouldUseStaticMap && (
            <div className="mb-4 bg-blue-50 rounded-lg border border-blue-100 p-3">
              <div className="text-xs font-bold text-blue-800 uppercase tracking-wide mb-2 flex justify-between items-center">
                <span>📍 Current Route</span>
                <button 
                  onClick={() => handleSelectTrip(tripData)} 
                  className="text-[10px] bg-white px-2 py-0.5 rounded shadow-sm hover:bg-blue-100 cursor-pointer border border-blue-200"
                >
                  Reset View
                </button>
              </div>
              <div className="space-y-1">
                {tripData.timeline?.map((loc, idx) => (
                  <div 
                    key={idx}
                    onClick={() => handleSelectStop(tripData.points[idx])}
                    className="flex items-center gap-2 text-xs p-2 bg-white rounded border border-blue-100 hover:bg-blue-100 cursor-pointer transition active:scale-95"
                  >
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center text-white font-bold text-[10px] ${
                      idx === 0 ? 'bg-green-500' : 
                      idx === tripData.timeline.length-1 ? 'bg-red-500' : 
                      'bg-blue-500'
                    }`}>
                      {idx + 1}
                    </div>
                    <span className="truncate flex-1 font-medium text-gray-700">{loc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* B. History List */}
          {!loading && (
            <>
              <div className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2 px-1">
                {history.length > 0 ? `Trip History (${history.length})` : 'No Trips Yet'}
              </div>
              <div className="space-y-2">
                {history.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <svg className="mx-auto h-12 w-12 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                    </svg>
                    <p className="text-sm font-medium mb-1">🔭 No trips yet</p>
                    <p className="text-xs">Upload photos to create your first trip!</p>
                  </div>
                ) : (
                  history.map((trip, idx) => (
                    <div 
                      key={trip.created_at || idx}
                      onClick={() => handleSelectTrip(trip)}
                      className={`group p-3 rounded-lg border cursor-pointer transition-all duration-200 
                        ${tripData?.created_at === trip.created_at
                          ? 'bg-gray-100 border-gray-300 shadow-inner' 
                          : 'bg-white border-gray-100 hover:border-blue-300 hover:shadow-sm'
                        }`}
                    >
                      <div className="flex justify-between items-start mb-1">
                        <h3 className={`font-bold text-sm ${
                          tripData?.created_at === trip.created_at ? 'text-blue-700' : 'text-gray-800'
                        }`}>
                          {trip.trip_title}
                        </h3>
                        <span className="text-[10px] text-gray-400">
                          {trip.created_at ? new Date(trip.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ''}
                        </span>
                      </div>
                      <div className="flex gap-2 text-[10px] text-gray-500">
                        <span>{trip.total_distance_km} km</span> • 
                        <span>{trip.total_locations} stops</span> •
                        <span>{trip.total_photos} photos</span>
                      </div>
                      {trip.start_date && (
                        <div className="text-[10px] text-gray-400 mt-1">
                          {trip.start_date} → {trip.end_date}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* MAP AREA */}
      <div className="flex-1 relative flex flex-col min-w-0 bg-gray-50">
        {/* Status Bar with Toggle */}
        <div className="absolute top-4 right-4 z-10 flex gap-2">
          {/* Map Mode Toggle Button */}
          {tripData && (
            <button
              onClick={handleToggleMapMode}
              className="bg-white/90 backdrop-blur shadow border border-gray-200 px-4 py-1.5 rounded-full flex items-center gap-2 hover:bg-white transition-all active:scale-95"
              title={useInteractiveMap ? "Switch to Static Map" : "Switch to Interactive Map"}
            >
              {useInteractiveMap ? (
                <>
                  <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                  <span className="text-xs font-bold text-gray-700">Interactive</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <span className="text-xs font-bold text-gray-700">Static</span>
                </>
              )}
            </button>
          )}
          
          {/* Status Badge */}
          <div className="bg-white/90 backdrop-blur shadow border border-gray-200 px-4 py-1.5 rounded-full flex items-center gap-2 pointer-events-none">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-xs font-bold text-gray-700">{status}</span>
          </div>
        </div>

        {/* Map Component */}
        <div className="flex-1 relative">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                <p className="text-gray-500">Loading map...</p>
              </div>
            </div>
          ) : tripData ? (
            shouldUseStaticMap ? (
              <StaticTripMap tripData={tripData} />
            ) : (
              <TripMap 
                tripData={tripData} 
                focusTrigger={focusTrigger} 
                focusLocation={focusLocation}
              />
            )
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <svg className="mx-auto h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
                <p className="font-medium text-lg mb-2">No Trip Selected</p>
                <p className="text-sm">
                  {history.length === 0 
                    ? 'Upload photos to create your first trip' 
                    : 'Select a trip from the sidebar to view the map'
                  }
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default TripSummaryPage;