import React, { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';

interface HeatmapLayerProps {
  points: [number, number, number][]; // [lat, lng, intensity]
  radius?: number;
  blur?: number;
  maxZoom?: number;
  minOpacity?: number;
  gradient?: Record<number, string>;
}

export const HeatmapLayer: React.FC<HeatmapLayerProps> = ({
  points,
  radius = 28,
  blur = 18,
  minOpacity = 0.35,
  gradient = {
    0.2: '#3b82f6', // Low concentration: Blue
    0.4: '#06b6d4', // Low-to-Moderate: Cyan
    0.6: '#eab308', // Moderate concentration: Yellow/Amber
    0.8: '#f97316', // High concentration: Orange
    1.0: '#ef4444', // Hotspot area: Deep Crimson/Red
  },
}) => {
  const map = useMap();

  useEffect(() => {
    if (!map || !points || points.length === 0) return;

    // Self-contained high-performance Canvas Heatmap Layer
    const CanvasHeatLayer = (L.Layer as any).extend({
      onAdd: function (leafletMap: L.Map) {
        this._map = leafletMap;
        this._canvas = L.DomUtil.create('canvas', 'leaflet-heatmap-layer') as HTMLCanvasElement;
        this._canvas.style.position = 'absolute';
        this._canvas.style.pointerEvents = 'none';

        const pane = leafletMap.getPane('overlayPane');
        if (pane) {
          pane.appendChild(this._canvas);
        }

        this._update = this._update.bind(this);
        leafletMap.on('moveend zoomend resize viewreset', this._update, this);
        this._update();
      },

      onRemove: function (leafletMap: L.Map) {
        if (this._canvas && this._canvas.parentNode) {
          this._canvas.parentNode.removeChild(this._canvas);
        }
        leafletMap.off('moveend zoomend resize viewreset', this._update, this);
      },

      _createGradient: function () {
        const gradCanvas = document.createElement('canvas');
        gradCanvas.width = 1;
        gradCanvas.height = 256;
        const ctx = gradCanvas.getContext('2d');
        if (!ctx) return null;

        const grad = ctx.createLinearGradient(0, 0, 0, 256);
        for (const [stop, color] of Object.entries(gradient)) {
          grad.addColorStop(parseFloat(stop), color);
        }
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 1, 256);
        return ctx.getImageData(0, 0, 1, 256).data;
      },

      _createCircle: function (r: number, b: number) {
        const circleCanvas = document.createElement('canvas');
        const r2 = r + b;
        circleCanvas.width = r2 * 2;
        circleCanvas.height = r2 * 2;
        const ctx = circleCanvas.getContext('2d');
        if (!ctx) return circleCanvas;

        ctx.shadowOffsetX = r2 * 2;
        ctx.shadowOffsetY = r2 * 2;
        ctx.shadowBlur = b;
        ctx.shadowColor = 'black';

        ctx.beginPath();
        ctx.arc(-r2, -r2, r, 0, Math.PI * 2, true);
        ctx.closePath();
        ctx.fill();

        return circleCanvas;
      },

      _update: function () {
        if (!this._map || !this._canvas) return;

        const size = this._map.getSize();
        const bounds = this._map.getBounds();
        const topLeft = this._map.containerPointToLayerPoint([0, 0]);

        L.DomUtil.setPosition(this._canvas, topLeft);

        this._canvas.width = size.x;
        this._canvas.height = size.y;

        const ctx = this._canvas.getContext('2d');
        if (!ctx) return;
        ctx.clearRect(0, 0, size.x, size.y);

        const r = radius;
        const b = blur;
        const circle = this._createCircle(r, b);
        const r2 = r + b;

        // Draw grayscale alpha mask
        for (let i = 0; i < points.length; i++) {
          const [lat, lng, intensity] = points[i];
          if (bounds.contains([lat, lng])) {
            const point = this._map.latLngToContainerPoint([lat, lng]);
            ctx.globalAlpha = Math.min(1, Math.max(minOpacity, intensity || 0.5));
            ctx.drawImage(circle, point.x - r2, point.y - r2);
          }
        }

        // Colorize with gradient palette
        const gradData = this._createGradient();
        if (!gradData) return;

        const image = ctx.getImageData(0, 0, size.x, size.y);
        const data = image.data;

        for (let i = 0; i < data.length; i += 4) {
          const alpha = data[i + 3];
          if (alpha > 0) {
            const offset = alpha * 4;
            data[i] = gradData[offset];         // R
            data[i + 1] = gradData[offset + 1]; // G
            data[i + 2] = gradData[offset + 2]; // B
          }
        }

        ctx.putImageData(image, 0, 0);
      },
    });

    const layer = new CanvasHeatLayer();
    layer.addTo(map);

    return () => {
      if (map && layer) {
        try {
          map.removeLayer(layer);
        } catch {
          // Ignore removal errors on component unmount
        }
      }
    };
  }, [map, points, radius, blur, minOpacity, gradient]);

  return null;
};
