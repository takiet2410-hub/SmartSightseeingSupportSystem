import React, { useMemo } from 'react';

const StaticTripMap = ({ tripData }) => {
  // Build Mapbox Static Image URL if not provided
  const mapUrl = useMemo(() => {
    // First try to get URL from tripData
    const existingUrl = tripData?.map_data?.url || tripData?.map_image_url || '';
    
    if (existingUrl) {
      console.log('✅ Using existing static map URL');
      return existingUrl;
    }
    
    // If no URL but we have points, generate one
    const points = tripData?.points || [];
    const mapboxToken = tripData?.map_data?.mapbox_token || process.env.REACT_APP_MAPBOX_TOKEN;
    
    if (points.length === 0 || !mapboxToken) {
      console.warn('⚠️ Cannot generate static map: missing points or token');
      return '';
    }
    
    console.log('🔧 Generating static map URL from points...');
    return buildMapboxStaticUrl(points, mapboxToken);
  }, [tripData]);

  if (!tripData) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        Select a trip to view map
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* ❌ REMOVED: Trip Stats Bar (The blue banner)
         The code block that was here has been deleted as requested.
      */}

      {/* Static Map Image */}
      <div className="flex-1 relative overflow-auto bg-gray-100">
        {mapUrl ? (
          <div className="relative min-h-full flex items-center justify-center p-4">
            <img 
              src={mapUrl} 
              alt="Trip Map"
              className="max-w-full h-auto rounded-lg shadow-lg"
              onError={(e) => {
                console.error('❌ Failed to load map image:', mapUrl);
                e.target.style.display = 'none';
                e.target.nextElementSibling.style.display = 'flex';
              }}
              onLoad={() => {
                console.log('✅ Static map loaded successfully');
              }}
            />
            {/* Error Placeholder */}
            <div 
              className="hidden absolute inset-0 items-center justify-center bg-gray-200"
              style={{ display: 'none' }}
            >
              <div className="text-center text-gray-500 p-8">
                <svg className="mx-auto h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p className="font-medium text-lg mb-2">Unable to load map image</p>
                <p className="text-sm mb-4">The map image could not be loaded</p>
                <button 
                  onClick={() => window.location.reload()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                  Refresh Page
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-400 p-8">
              <svg className="mx-auto h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
              <p className="font-medium text-lg mb-2">No map available</p>
              <p className="text-sm mb-4">
                {tripData.points?.length > 0 
                  ? 'Missing Mapbox token or map generation failed' 
                  : 'No location data available for this trip'
                }
              </p>
              <button 
                onClick={() => {
                  console.log('🔍 Debug info:', {
                    points: tripData.points,
                    map_data: tripData.map_data,
                    token: process.env.REACT_APP_MAPBOX_TOKEN ? 'Present' : 'Missing'
                  });
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition text-sm"
              >
                Debug Info (Check Console)
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Info Banner */}
      <div className="shrink-0 px-4 py-3 bg-yellow-50 border-t border-yellow-100">
        <div className="flex items-start gap-3">
          <span className="text-2xl">💡</span>
          <div className="flex-1 text-sm">
            <p className="font-semibold text-yellow-900 mb-1">Static Map Mode</p>
            <p className="text-yellow-800">
              This is a non-interactive image. Switch to Interactive mode for zoom, pan, and 3D buildings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Helper function to build Mapbox Static Image URL
function buildMapboxStaticUrl(points, token) {
  if (!points || points.length === 0 || !token) {
    return '';
  }

  try {
    // Convert points from [lat, lon] to [lon, lat] for Mapbox
    const displayPoints = points.map(p => [p[1], p[0]]);
    
    // Sample points if too many (URL length limit)
    let sampledPoints = displayPoints;
    if (displayPoints.length > 15) {
      const step = Math.floor(displayPoints.length / 15);
      sampledPoints = displayPoints.filter((_, i) => i % step === 0);
      // Always include last point
      if (sampledPoints[sampledPoints.length - 1] !== displayPoints[displayPoints.length - 1]) {
        sampledPoints.push(displayPoints[displayPoints.length - 1]);
      }
    }

    // Build path (line connecting points)
    const pathCoords = sampledPoints.map(p => `${p[0]},${p[1]}`).join('|');
    const path = `path-5+007bff-0.6(${pathCoords})`;

    // Build markers for ALL points
    const overlays = [path];
    
    sampledPoints.forEach((point, index) => {
        let color = "3b82f6"; // Blue (default)
        if (index === 0) color = "10b981"; // Green (Start)
        else if (index === sampledPoints.length - 1) color = "ef4444"; // Red (End)
        
        // Add pin: pin-s-{number}+{color}({lon},{lat})
        // Note: Mapbox static supports labels 0-99
        overlays.push(`pin-s-${index + 1}+${color}(${point[0]},${point[1]})`);
    });

    const overlay = overlays.join(',');

    // Calculate center and bounds
    const lons = sampledPoints.map(p => p[0]);
    const lats = sampledPoints.map(p => p[1]);
    const centerLon = lons.reduce((a, b) => a + b) / lons.length;
    const centerLat = lats.reduce((a, b) => a + b) / lats.length;

    // Calculate zoom
    const latRange = Math.max(...lats) - Math.min(...lats);
    const lonRange = Math.max(...lons) - Math.min(...lons);
    const maxRange = Math.max(latRange, lonRange);

    let zoom;
    if (maxRange > 10) zoom = 4;
    else if (maxRange > 5) zoom = 5;
    else if (maxRange > 2) zoom = 6;
    else if (maxRange > 1) zoom = 7;
    else if (maxRange > 0.5) zoom = 8;
    else if (maxRange > 0.2) zoom = 9;
    else if (maxRange > 0.1) zoom = 10;
    else zoom = 11;

    // Build final URL
    const url = `https://api.mapbox.com/styles/v1/mapbox/streets-v12/static/${overlay}/${centerLon},${centerLat},${zoom}/1000x600@2x?access_token=${token}`;
    
    console.log(`✅ Generated static map URL with ${sampledPoints.length} markers`);
    return url;
    
  } catch (error) {
    console.error('❌ Error building static map URL:', error);
    return '';
  }
}

export default StaticTripMap;