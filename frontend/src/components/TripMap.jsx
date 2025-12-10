import React, { useEffect, useRef, useState, useMemo, memo } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

// ⚡ CSS Optimization
const MARKER_STYLES = `
  .custom-marker {
    width: 24px; height: 24px; cursor: pointer;
    will-change: transform;
    z-index: 10;
  }
  .marker-inner {
    width: 100%; height: 100%; border-radius: 50%;
    border: 2px solid white; display: flex;
    align-items: center; justify-content: center;
    color: white; font-weight: bold; font-family: sans-serif;
    font-size: 11px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.5); 
    background-color: #3b82f6; 
    transition: transform 0.15s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  }
  
  .custom-marker:hover .marker-inner {
    transform: scale(1.3);
    box-shadow: 0 4px 8px rgba(0,0,0,0.4);
    z-index: 20;
  }
`;

const TripMap = ({ tripData, focusTrigger, focusLocation }) => {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const markersRef = useRef([]); 
  const [error, setError] = useState(null);

  const token = useMemo(() => 
    process.env.REACT_APP_MAPBOX_TOKEN || tripData?.map_data?.mapbox_token, 
  [tripData]);

  // --- 1. Map Initialization ---
  useEffect(() => {
    if (map.current || !token || !mapContainer.current) return;

    const originalDPR = window.devicePixelRatio;
    try {
        Object.defineProperty(window, 'devicePixelRatio', { get: () => 1.0, configurable: true });
    } catch (e) {
        console.warn("Could not patch devicePixelRatio", e);
    }

    mapboxgl.accessToken = token;

    try {
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/streets-v11?optimize=true',
        powerPreference: 'high-performance',
        center: [106.6, 10.8],
        zoom: 12,
        pitch: 0,
        bearing: 0,
        maxPitch: 0,
        minPitch: 0,
        minZoom: 3,
        maxZoom: 18,
        projection: 'mercator',
        dragRotate: false,
        touchZoomRotate: false,
        touchPitch: false,
        pitchWithRotate: false,
        antialias: false,
        preserveDrawingBuffer: false,
        boxZoom: false,
        attributionControl: false,
        trackResize: true,
        fadeDuration: 0,
        maxTileCacheSize: 10
      });

      try {
          Object.defineProperty(window, 'devicePixelRatio', { get: () => originalDPR, configurable: true });
      } catch (e) {}

      map.current.on('load', () => {
        if (!map.current) return;
        cullHeavyLayers(map.current);
        if (tripData?.points) updateMapMarkers(tripData);
      });

    } catch (err) {
      setError(err.message);
    }

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [token]);

  // --- 2. Markers & Route ---
  useEffect(() => {
    if (map.current && map.current.isStyleLoaded()) {
      updateMapMarkers(tripData);
    }
  }, [tripData]);

  // --- 3. Instant Jump ---
  useEffect(() => {
    if (!map.current || !focusLocation) return;
    map.current.jumpTo({
      center: [focusLocation[1], focusLocation[0]], 
      zoom: 16
    });

    const index = tripData.points.findIndex(p => p[0] === focusLocation[0] && p[1] === focusLocation[1]);
    if (index !== -1 && markersRef.current[index]) {
      const marker = markersRef.current[index];
      if (!marker.getPopup().isOpen()) marker.togglePopup();
    }
  }, [focusLocation]);

  // --- 4. Instant FitBounds ---
  useEffect(() => {
    if (!map.current || !tripData?.points?.length) return;
    const bounds = new mapboxgl.LngLatBounds();
    tripData.points.forEach(p => bounds.extend([p[1], p[0]]));
    map.current.fitBounds(bounds, { padding: 40, duration: 0, animate: false }); 
  }, [focusTrigger]);

  const cullHeavyLayers = (mapInstance) => {
    const layers = mapInstance.getStyle().layers;
    const blacklist = ['building', 'poi', 'transit', 'barrier', 'admin', 'water-shadow', 'road-label', 'waterway-label'];
    layers.forEach(layer => {
      if (blacklist.some(key => layer.id.includes(key))) {
        mapInstance.setLayoutProperty(layer.id, 'visibility', 'none');
      }
    });
  };

  const createArrowImage = (mapInstance) => {
      if (mapInstance.hasImage('custom-arrow')) return;
      const size = 20;
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#666'; 
      ctx.beginPath();
      // Arrow pointing Right (East) - important for rotation alignment
      ctx.moveTo(0, 0); ctx.lineTo(size, size / 2); ctx.lineTo(0, size);
      ctx.closePath();
      ctx.fill();
      const imageData = ctx.getImageData(0, 0, size, size);
      mapInstance.addImage('custom-arrow', imageData, { sdf: true });
  };

  const updateMapMarkers = (data) => {
    if (!map.current || !data?.points) return;

    // A. Prepare Coordinates
    const routeCoordinates = data.points.map(p => [p[1], p[0]]);

    // B. Prepare Segments (for Arrows)
    // We create individual LineString features for every leg of the trip
    // This allows us to place exactly one arrow on "line-center" of each leg
    const segmentFeatures = [];
    for (let i = 0; i < routeCoordinates.length - 1; i++) {
        segmentFeatures.push({
            type: 'Feature',
            geometry: {
                type: 'LineString',
                coordinates: [routeCoordinates[i], routeCoordinates[i+1]]
            },
            properties: {}
        });
    }

    const lineSourceId = 'trip-route';
    const arrowSourceId = 'trip-arrows-segments';

    createArrowImage(map.current);

    // --- 1. Draw the Continuous Line ---
    if (map.current.getSource(lineSourceId)) {
        map.current.getSource(lineSourceId).setData({
            type: 'Feature',
            properties: {},
            geometry: { type: 'LineString', coordinates: routeCoordinates }
        });
    } else {
        map.current.addSource(lineSourceId, {
            type: 'geojson',
            data: { type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: routeCoordinates } }
        });

        map.current.addLayer({
            id: 'trip-route-line',
            type: 'line',
            source: lineSourceId,
            layout: { 'line-join': 'round', 'line-cap': 'round' },
            paint: { 'line-color': '#888', 'line-width': 3, 'line-dasharray': [2, 1] }
        });
    }

    // --- 2. Draw the Directional Arrows (One per segment) ---
    if (map.current.getSource(arrowSourceId)) {
        map.current.getSource(arrowSourceId).setData({
            type: 'FeatureCollection',
            features: segmentFeatures
        });
    } else {
        map.current.addSource(arrowSourceId, {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: segmentFeatures }
        });

        map.current.addLayer({
            id: 'trip-route-arrows',
            type: 'symbol',
            source: arrowSourceId, // Use the segments source
            layout: {
                'symbol-placement': 'line-center', // <--- Places 1 icon at the center of the segment
                'icon-image': 'custom-arrow',
                'icon-size': 0.6,
                'icon-allow-overlap': true,
                'icon-rotation-alignment': 'map', // Aligns with the line geometry
                'icon-rotate': 0, 
                'icon-padding': 0
            },
            paint: { 'icon-color': '#555' }
        });
    }

    // --- 3. Draw Markers ---
    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    const points = data.points;

    points.forEach((point, index) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'custom-marker'; 

      const inner = document.createElement('div');
      inner.className = 'marker-inner';
      
      const color = index === 0 ? '#10b981' : (index === points.length - 1 ? '#ef4444' : '#3b82f6');
      inner.style.backgroundColor = color;
      inner.textContent = `${index + 1}`;
      
      wrapper.appendChild(inner);

      const popup = new mapboxgl.Popup({ offset: 20, closeButton: false, closeOnClick: true, maxWidth: '150px' })
        .setHTML(`<div style="font-size:12px; font-weight:bold;">${data.timeline?.[index] || `Stop ${index + 1}`}</div>`);

      const marker = new mapboxgl.Marker({ element: wrapper })
        .setLngLat([point[1], point[0]])
        .setPopup(popup)
        .addTo(map.current);

      markersRef.current.push(marker);
    });
  };

  if (error) return <div className="text-red-500 p-4 font-bold">Map Error: {error}</div>;

  return (
    <>
      <style>{MARKER_STYLES}</style>
      <div ref={mapContainer} className="absolute inset-0 w-full h-full" />
    </>
  );
};

const arePropsEqual = (prev, next) => {
  return (
    prev.focusTrigger === next.focusTrigger &&
    prev.focusLocation === next.focusLocation &&
    (prev.tripData === next.tripData || 
      (prev.tripData?.points?.length === next.tripData?.points?.length &&
       prev.tripData?.points?.[0] === next.tripData?.points?.[0]))
  );
};

export default memo(TripMap, arePropsEqual);