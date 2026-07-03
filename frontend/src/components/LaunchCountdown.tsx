import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

const LAUNCH_DATE = new Date('2026-07-17T00:00:00-07:00');

function getTimeLeft() {
  const diff = LAUNCH_DATE.getTime() - Date.now();
  const clamped = Math.max(diff, 0);
  return {
    days: Math.floor(clamped / (1000 * 60 * 60 * 24)),
    hours: Math.floor((clamped / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((clamped / (1000 * 60)) % 60),
    seconds: Math.floor((clamped / 1000) % 60),
    done: diff <= 0,
  };
}

export default function LaunchCountdown() {
  const { t } = useTranslation();
  const [timeLeft, setTimeLeft] = useState(getTimeLeft);

  useEffect(() => {
    const id = setInterval(() => setTimeLeft(getTimeLeft()), 1000);
    return () => clearInterval(id);
  }, []);

  if (timeLeft.done) {
    return (
      <div className="font-display text-2xl md:text-3xl font-bold text-cyber-green animate-yellow-pulse">
        {t('home.countdown_live')}
      </div>
    );
  }

  const units = [
    { label: t('home.countdown_days'), value: timeLeft.days },
    { label: t('home.countdown_hours'), value: timeLeft.hours },
    { label: t('home.countdown_minutes'), value: timeLeft.minutes },
    { label: t('home.countdown_seconds'), value: timeLeft.seconds },
  ];

  return (
    <div className="flex items-start gap-3 md:gap-4 justify-center md:justify-start font-mono">
      {units.map((unit, i) => (
        <div key={unit.label} className="flex items-start gap-3 md:gap-4">
          <div className="text-center">
            <div className="font-display text-3xl md:text-4xl font-bold text-cyber-cyan tabular-nums">
              {String(unit.value).padStart(2, '0')}
            </div>
            <div className="text-[10px] tracking-widest text-gray-500 mt-1">
              {unit.label}
            </div>
          </div>
          {i < units.length - 1 && (
            <div className="text-2xl md:text-3xl text-cyber-cyan/20 leading-none">:</div>
          )}
        </div>
      ))}
    </div>
  );
}
