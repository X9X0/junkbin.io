export default function SuspenseFallback() {
  return (
    <div className="min-h-screen bg-cyber-black flex items-center justify-center font-mono">
      <div className="text-center space-y-3 px-4">
        <div className="text-cyber-yellow text-xs tracking-[0.6em] animate-pulse">
          ⚠ WARNING ⚠
        </div>
        <div className="font-display text-sm md:text-base font-bold text-white tracking-[0.15em]">
          NO USER SERVICEABLE PARTS INSIDE
        </div>
        <div className="text-gray-700 text-xs tracking-widest mt-2 blink">
          █
        </div>
      </div>
    </div>
  );
}
