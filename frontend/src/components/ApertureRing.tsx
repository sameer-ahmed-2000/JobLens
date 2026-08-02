import React from 'react';

interface ApertureRingProps {
  score: number;
  size?: 'normal' | 'mini';
  className?: string;
}

export const ApertureRing: React.FC<ApertureRingProps> = ({ score, size = 'normal', className = '' }) => {
  const isNormal = size === 'normal';
  const radius = isNormal ? 20 : 13;
  const strokeWidth = isNormal ? 3.5 : 2.5;
  const viewBoxSize = isNormal ? 52 : 36;
  const center = viewBoxSize / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(Math.max(Math.round(score), 0), 100);
  const strokeDashoffset = circumference - (pct / 100) * circumference;

  // Generate 6 mechanical aperture blade segment lines
  const bladesCount = 6;
  const bladeLength = isNormal ? 8 : 5.5;
  const blades = [];

  for (let i = 0; i < bladesCount; i++) {
    const angleRad = (i * 2 * Math.PI) / bladesCount;
    // Outer coordinate on radius
    const x1 = center + radius * Math.cos(angleRad);
    const y1 = center + radius * Math.sin(angleRad);
    // Tangent angle offset inward for blade edge effect
    const tangentAngle = angleRad + Math.PI / 2.5;
    const x2 = x1 - bladeLength * Math.cos(tangentAngle);
    const y2 = y1 - bladeLength * Math.sin(tangentAngle);

    blades.push({ x1, y1, x2, y2 });
  }

  return (
    <div className={`relative inline-flex items-center justify-center shrink-0 select-none ${className}`}>
      <svg
        width={viewBoxSize}
        height={viewBoxSize}
        viewBox={`0 0 ${viewBoxSize} ${viewBoxSize}`}
        className="transform -rotate-90"
      >
        {/* Background track circle */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="#32302A"
          strokeWidth={strokeWidth}
        />
        {/* Foreground active percentage match arc */}
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="var(--color-focus-confirm)"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
        {/* Camera aperture blade segments overlay */}
        {blades.map((b, idx) => (
          <line
            key={idx}
            x1={b.x1}
            y1={b.y1}
            x2={b.x2}
            y2={b.y2}
            stroke="#1A1917"
            strokeWidth={isNormal ? 1.5 : 1}
            opacity="0.8"
          />
        ))}
      </svg>
      {/* Central mono-number readout */}
      <span
        className={`absolute font-mono font-bold text-text-warm tracking-tighter ${
          isNormal ? 'text-xs mt-[1px]' : 'text-[9px] mt-[0.5px]'
        }`}
      >
        {pct}
      </span>
    </div>
  );
};
