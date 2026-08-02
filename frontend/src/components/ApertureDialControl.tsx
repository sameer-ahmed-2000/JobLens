import React, { useRef, useState } from 'react';

interface ApertureDialControlProps {
  displayFloor: number; // 0.0 to 1.0
  notifyFloor: number;  // 0.0 to 1.0
  onChange: (display: number, notify: number) => void;
}

export const ApertureDialControl: React.FC<ApertureDialControlProps> = ({
  displayFloor,
  notifyFloor,
  onChange,
}) => {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [activeHandle, setActiveHandle] = useState<'display' | 'notify' | null>(null);
  const [focusedHandle, setFocusedHandle] = useState<'display' | 'notify' | null>(null);

  const radius = 70;
  const strokeWidth = 8;
  const center = 100;

  // Convert percentage (0 to 1) to X, Y coordinates on circle
  const getCoords = (value: number) => {
    // 0.0 starts at top (-Math.PI / 2) and runs clockwise
    const angle = value * 2 * Math.PI - Math.PI / 2;
    return {
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    };
  };

  // Convert client coordinate of pointer to a 0.0 - 1.0 percentage
  const calculateValueFromCoords = (clientX: number, clientY: number) => {
    if (!svgRef.current) return 0;
    const rect = svgRef.current.getBoundingClientRect();
    const x = clientX - (rect.left + rect.width / 2);
    const y = clientY - (rect.top + rect.height / 2);

    let angleRad = Math.atan2(y, x); // -PI to PI
    // Align with top start (shift by +PI/2)
    let angleShifted = angleRad + Math.PI / 2;
    if (angleShifted < 0) {
      angleShifted += 2 * Math.PI;
    }
    const val = angleShifted / (2 * Math.PI);
    return Math.min(Math.max(val, 0), 1);
  };

  // Pointer dragging event handlers
  const handlePointerDown = (handle: 'display' | 'notify') => (e: React.PointerEvent) => {
    e.preventDefault();
    setActiveHandle(handle);
    setFocusedHandle(handle);
    (e.target as Element).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!activeHandle) return;
    const rawVal = calculateValueFromCoords(e.clientX, e.clientY);
    const roundedVal = Math.round(rawVal * 100) / 100; // Round to nearest 1%

    if (activeHandle === 'display') {
      // displayFloor must be <= notifyFloor
      const maxVal = notifyFloor;
      const newVal = Math.min(roundedVal, maxVal);
      onChange(newVal, notifyFloor);
    } else {
      // notifyFloor must be >= displayFloor
      const minVal = displayFloor;
      const newVal = Math.max(roundedVal, minVal);
      onChange(displayFloor, newVal);
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!activeHandle) return;
    (e.target as Element).releasePointerCapture(e.pointerId);
    setActiveHandle(null);
  };

  // Keyboard navigation handler
  const handleKeyDown = (handle: 'display' | 'notify') => (e: React.KeyboardEvent) => {
    let step = 0.01; // default step 1%
    if (e.shiftKey) step = 0.05; // 5% step with shift

    let newVal = handle === 'display' ? displayFloor : notifyFloor;

    if (e.key === 'ArrowUp' || e.key === 'ArrowRight') {
      e.preventDefault();
      newVal = Math.min(newVal + step, 1.0);
    } else if (e.key === 'ArrowDown' || e.key === 'ArrowLeft') {
      e.preventDefault();
      newVal = Math.max(newVal - step, 0.0);
    } else if (e.key === 'Home') {
      e.preventDefault();
      newVal = handle === 'display' ? 0.0 : displayFloor;
    } else if (e.key === 'End') {
      e.preventDefault();
      newVal = handle === 'display' ? notifyFloor : 1.0;
    } else {
      return;
    }

    const roundedVal = Math.round(newVal * 100) / 100;

    if (handle === 'display') {
      onChange(Math.min(roundedVal, notifyFloor), notifyFloor);
    } else {
      onChange(displayFloor, Math.max(roundedVal, displayFloor));
    }
  };

  // Coords for SVGs
  const displayCoords = getCoords(displayFloor);
  const notifyCoords = getCoords(notifyFloor);

  // SVG Arc drawing string helper: from start (0.0) to end
  const getArcPath = (startVal: number, endVal: number) => {
    const start = getCoords(startVal);
    const end = getCoords(endVal);
    const diff = endVal - startVal;
    const largeArcFlag = diff > 0.5 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`;
  };

  // Standard camera lens increments around dial (every 10%, 0.5 to 1.0 are critical)
  const ticks = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];

  return (
    <div className="flex flex-col items-center justify-center bg-surface p-6 rounded-2xl border border-gray-800 select-none space-y-4">
      
      {/* Circle Dial Area */}
      <div className="relative w-[200px] h-[200px]">
        <svg
          ref={svgRef}
          width="200"
          height="200"
          viewBox="0 0 200 200"
          className="w-full h-full"
          onPointerMove={handlePointerMove}
        >
          {/* Tick Marks & Readout values around the ring */}
          {ticks.map((t, idx) => {
            const angle = t * 2 * Math.PI - Math.PI / 2;
            const cos = Math.cos(angle);
            const sin = Math.sin(angle);
            // Tick line start/end
            const tickStartRadius = radius - 6;
            const tickEndRadius = radius - 2;
            const x1 = center + tickStartRadius * cos;
            const y1 = center + tickStartRadius * sin;
            const x2 = center + tickEndRadius * cos;
            const y2 = center + tickEndRadius * sin;

            // Labels placement radius
            const labelRadius = radius - 16;
            const lx = center + labelRadius * cos;
            const ly = center + labelRadius * sin;

            // Highlight ticks that are active (above display threshold)
            const isActive = t >= displayFloor;
            const isNotifyActive = t >= notifyFloor;
            const tickColor = isNotifyActive
              ? 'var(--color-signal-amber)'
              : isActive
              ? 'var(--color-focus-confirm)'
              : '#3C3B37';

            return (
              <g key={idx}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={tickColor}
                  strokeWidth="1.5"
                />
                {idx % 2 === 0 && (
                  <text
                    x={lx}
                    y={ly + 3.5}
                    textAnchor="middle"
                    className="font-mono text-[9px] font-bold fill-gray-500"
                  >
                    {Math.round(t * 100)}
                  </text>
                )}
              </g>
            );
          })}

          {/* Base Inactive Track (Underlay) */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="#32302A"
            strokeWidth={strokeWidth}
          />

          {/* 1. Visible Match Arc: from displayFloor to notifyFloor */}
          {notifyFloor > displayFloor && (
            <path
              d={getArcPath(displayFloor, notifyFloor)}
              fill="none"
              stroke="var(--color-focus-confirm)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />
          )}

          {/* 2. Premium Alert Arc: from notifyFloor to 1.0 */}
          {notifyFloor < 1.0 && (
            <path
              d={getArcPath(notifyFloor, 1.0)}
              fill="none"
              stroke="var(--color-signal-amber)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />
          )}

          {/* Handle 1: Display Floor Knob (Teal focus-confirm) */}
          <g
            role="slider"
            aria-label="Display Floor Match Threshold"
            aria-valuenow={Math.round(displayFloor * 100)}
            aria-valuemin={0}
            aria-valuemax={Math.round(notifyFloor * 100)}
            tabIndex={0}
            onKeyDown={handleKeyDown('display')}
            onFocus={() => setFocusedHandle('display')}
            onBlur={() => setFocusedHandle(null)}
            onPointerDown={handlePointerDown('display')}
            onPointerUp={handlePointerUp}
            className="cursor-grab active:cursor-grabbing focus:outline-none"
          >
            {/* Outline Glow if Keyboard Focused */}
            {focusedHandle === 'display' && (
              <circle
                cx={displayCoords.x}
                cy={displayCoords.y}
                r="11"
                fill="none"
                stroke="var(--color-focus-confirm)"
                strokeWidth="2"
                opacity="0.5"
              />
            )}
            <circle
              cx={displayCoords.x}
              cy={displayCoords.y}
              r="8"
              fill="#1A1917"
              stroke="var(--color-focus-confirm)"
              strokeWidth="3.5"
              className="shadow-sm transition-transform duration-100 hover:scale-110"
            />
          </g>

          {/* Handle 2: Notify Floor Knob (Amber signal-amber) */}
          <g
            role="slider"
            aria-label="Notify Floor Match Threshold"
            aria-valuenow={Math.round(notifyFloor * 100)}
            aria-valuemin={Math.round(displayFloor * 100)}
            aria-valuemax={100}
            tabIndex={0}
            onKeyDown={handleKeyDown('notify')}
            onFocus={() => setFocusedHandle('notify')}
            onBlur={() => setFocusedHandle(null)}
            onPointerDown={handlePointerDown('notify')}
            onPointerUp={handlePointerUp}
            className="cursor-grab active:cursor-grabbing focus:outline-none"
          >
            {/* Outline Glow if Keyboard Focused */}
            {focusedHandle === 'notify' && (
              <circle
                cx={notifyCoords.x}
                cy={notifyCoords.y}
                r="11"
                fill="none"
                stroke="var(--color-signal-amber)"
                strokeWidth="2"
                opacity="0.5"
              />
            )}
            <circle
              cx={notifyCoords.x}
              cy={notifyCoords.y}
              r="8"
              fill="#1A1917"
              stroke="var(--color-signal-amber)"
              strokeWidth="3.5"
              className="shadow-sm transition-transform duration-100 hover:scale-110"
            />
          </g>
        </svg>

        {/* Center Readouts */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
          <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">APERTURE DIAL</span>
          <div className="flex items-baseline space-x-1 font-mono">
            <span className="text-xl font-bold text-focus-confirm">{Math.round(displayFloor * 100)}</span>
            <span className="text-xs text-gray-600">/</span>
            <span className="text-xl font-bold text-signal-amber">{Math.round(notifyFloor * 100)}</span>
            <span className="text-[10px] text-gray-400 font-semibold">%</span>
          </div>
          <span className="text-[9px] font-bold text-gray-400 uppercase tracking-tighter mt-0.5">DISPLAY / NOTIFY</span>
        </div>
      </div>

      {/* Manual readout explanation */}
      <div className="w-full grid grid-cols-2 gap-4 text-center font-mono text-xs border-t border-gray-800 pt-3.5">
        <div className="space-y-0.5">
          <span className="block text-[9px] uppercase font-bold text-gray-500">DISPLAY FLOOR</span>
          <span className="text-focus-confirm font-bold text-sm">f / {displayFloor.toFixed(2)}</span>
        </div>
        <div className="space-y-0.5">
          <span className="block text-[9px] uppercase font-bold text-gray-500">NOTIFY FLOOR</span>
          <span className="text-signal-amber font-bold text-sm">f / {notifyFloor.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
};
