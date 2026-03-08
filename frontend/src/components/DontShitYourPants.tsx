import { useState, useEffect, useRef, useCallback } from 'react';

type Location = 'room' | 'bathroom';

interface GameState {
  location: Location;
  pantsOn: boolean;
  doorOpen: boolean;
  sitting: boolean;
  gameOver: boolean;
  won: boolean;
  timeLeft: number;
}

const INITIAL_STATE: GameState = {
  location: 'room',
  pantsOn: true,
  doorOpen: false,
  sitting: false,
  gameOver: false,
  won: false,
  timeLeft: 36,
};

const INITIAL_MESSAGES = [
  'DON\'T SHIT YOUR PANTS  v1.0',
  'by Rete Interactive (web port)',
  '',
  'You are standing in your living room.',
  'You are wearing pants.',
  'You REALLY need to take a shit.',
  '',
  'There is a door to the north.',
  '',
  'Type HELP for a list of commands.',
];

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function parseCommand(
  input: string,
  state: GameState,
): { messages: string[]; newState: Partial<GameState> } {
  const cmd = input.trim().toLowerCase();
  const msgs: string[] = [];
  const ns: Partial<GameState> = {};

  // --- SHIT COMMAND (the main event) ---
  const shitCmds = [
    'shit', 'poop', 'defecate', 'crap', 'dump', 'go',
    'take a shit', 'take a dump', 'take a crap', 'go to the bathroom',
    'go to bathroom', 'use bathroom', 'relieve yourself',
  ];
  if (shitCmds.includes(cmd)) {
    if (state.pantsOn) {
      msgs.push('You shit your pants.');
      msgs.push('');
      msgs.push('[ GAME OVER ]');
      ns.gameOver = true;
    } else if (state.location !== 'bathroom') {
      msgs.push('You shit on the floor.');
      msgs.push('Your pants are off, but you\'re nowhere near a toilet.');
      msgs.push('Disgusting.');
      msgs.push('');
      msgs.push('[ GAME OVER ]');
      ns.gameOver = true;
    } else if (!state.sitting) {
      msgs.push('You shit standing up. It goes everywhere.');
      msgs.push('You should have sat down first.');
      msgs.push('');
      msgs.push('[ GAME OVER ]');
      ns.gameOver = true;
    } else {
      msgs.push('You sit and...');
      msgs.push('');
      msgs.push('Sweet, sweet relief washes over you.');
      msgs.push('');
      msgs.push('YOU DID IT! YOU DIDN\'T SHIT YOUR PANTS!');
      msgs.push('');
      msgs.push('Achievement unlocked: [ DON\'T SHIT YOUR PANTS ]');
      ns.gameOver = true;
      ns.won = true;
    }
    return { messages: msgs, newState: ns };
  }

  // --- HELP ---
  if (['help', '?', 'commands'].includes(cmd)) {
    msgs.push('Available commands:');
    msgs.push('  LOOK              - examine your surroundings');
    msgs.push('  INVENTORY / I     - check what you have');
    msgs.push('  TAKE OFF PANTS    - self-explanatory');
    msgs.push('  OPEN DOOR         - open the door');
    msgs.push('  NORTH / GO NORTH  - go through the door');
    msgs.push('  SIT               - sit on the toilet');
    msgs.push('  SHIT              - the whole point');
    msgs.push('  FLUSH             - be responsible');
    msgs.push('  QUIT              - escape this nightmare');
    return { messages: msgs, newState: {} };
  }

  // --- LOOK ---
  if (['look', 'look around', 'examine', 'l', 'examine room', 'look room', 'x'].includes(cmd)) {
    if (state.location === 'room') {
      msgs.push('You are in your living room.');
      msgs.push(`You are ${state.pantsOn ? 'wearing pants' : 'not wearing pants'}.`);
      msgs.push(`There is a door to the north. It is ${state.doorOpen ? 'open' : 'closed'}.`);
    } else {
      msgs.push('You are in the bathroom.');
      msgs.push(`You are ${state.pantsOn ? 'wearing pants' : 'not wearing pants'}.`);
      msgs.push(`There is a toilet here. You are ${state.sitting ? 'sitting on it' : 'not sitting on it'}.`);
      msgs.push('The door back to the living room is to the south.');
    }
    return { messages: msgs, newState: {} };
  }

  // --- INVENTORY ---
  if (['inventory', 'i', 'inv', 'items'].includes(cmd)) {
    if (state.pantsOn) {
      msgs.push('You are wearing: pants (currently clean — for now)');
    } else {
      msgs.push('You are wearing: nothing from the waist down.');
      msgs.push('Your pants are somewhere on the floor.');
    }
    return { messages: msgs, newState: {} };
  }

  // --- TAKE OFF PANTS ---
  const pantsOffCmds = [
    'take off pants', 'remove pants', 'drop pants', 'lower pants',
    'pull down pants', 'undress', 'take pants off', 'pants off',
    'drop trousers', 'remove trousers', 'take off trousers',
    'unzip', 'underpants', 'take off underwear', 'remove underwear',
    'disrobe',
  ];
  if (pantsOffCmds.includes(cmd)) {
    if (!state.pantsOn) {
      msgs.push('Your pants are already off.');
    } else {
      msgs.push('You take off your pants.');
      ns.pantsOn = false;
    }
    return { messages: msgs, newState: ns };
  }

  // --- PUT ON PANTS ---
  const pantsOnCmds = ['put on pants', 'wear pants', 'put pants on', 'dress', 'pants on', 'put trousers on'];
  if (pantsOnCmds.includes(cmd)) {
    if (state.pantsOn) {
      msgs.push('You\'re already wearing pants.');
    } else {
      msgs.push('You put your pants back on. Bold choice given the situation.');
      ns.pantsOn = true;
    }
    return { messages: msgs, newState: ns };
  }

  // --- OPEN DOOR ---
  const openDoorCmds = ['open door', 'open', 'door', 'unlock door'];
  if (openDoorCmds.includes(cmd)) {
    if (state.location === 'bathroom') {
      msgs.push('The door back to the living room is already accessible.');
    } else if (state.doorOpen) {
      msgs.push('The door is already open.');
    } else {
      msgs.push('You open the door. The bathroom is through here.');
      ns.doorOpen = true;
    }
    return { messages: msgs, newState: ns };
  }

  // --- CLOSE DOOR ---
  if (['close door', 'shut door', 'close'].includes(cmd)) {
    if (!state.doorOpen) {
      msgs.push('The door is already closed.');
    } else {
      msgs.push('You close the door. ...Why??');
      ns.doorOpen = false;
    }
    return { messages: msgs, newState: ns };
  }

  // --- GO NORTH / ENTER BATHROOM ---
  const northCmds = [
    'north', 'n', 'go north', 'go to bathroom', 'go bathroom',
    'enter bathroom', 'bathroom', 'enter door', 'go through door',
    'run north', 'sprint north',
  ];
  if (northCmds.includes(cmd)) {
    if (state.location === 'bathroom') {
      msgs.push('You\'re already in the bathroom. Focus!');
    } else if (!state.doorOpen) {
      msgs.push('The door is closed.');
    } else {
      msgs.push('You hurry into the bathroom.');
      ns.location = 'bathroom';
    }
    return { messages: msgs, newState: ns };
  }

  // --- GO SOUTH / LEAVE BATHROOM ---
  const southCmds = ['south', 's', 'go south', 'leave', 'exit', 'go back', 'leave bathroom', 'exit bathroom'];
  if (southCmds.includes(cmd)) {
    if (state.location === 'room') {
      msgs.push('The bathroom is to the north.');
    } else {
      msgs.push('You leave the bathroom. Hmm.');
      ns.location = 'room';
      ns.sitting = false;
    }
    return { messages: msgs, newState: ns };
  }

  // --- SIT ---
  const sitCmds = ['sit', 'sit down', 'sit on toilet', 'use toilet', 'toilet', 'sit on the toilet', 'sit down on toilet'];
  if (sitCmds.includes(cmd)) {
    if (state.location !== 'bathroom') {
      msgs.push('There\'s nothing to sit on here.');
    } else if (state.sitting) {
      msgs.push('You\'re already sitting on the toilet.');
    } else {
      msgs.push('You sit down on the toilet.');
      ns.sitting = true;
    }
    return { messages: msgs, newState: ns };
  }

  // --- STAND UP ---
  if (['stand', 'stand up', 'get up', 'rise'].includes(cmd)) {
    if (!state.sitting) {
      msgs.push('You\'re already standing.');
    } else {
      msgs.push('You stand up. Brave.');
      ns.sitting = false;
    }
    return { messages: msgs, newState: ns };
  }

  // --- FLUSH ---
  if (['flush', 'flush toilet'].includes(cmd)) {
    if (state.location !== 'bathroom') {
      msgs.push('There\'s no toilet here.');
    } else if (state.won) {
      msgs.push('You flush the toilet. Very responsible.');
    } else {
      msgs.push('The toilet is empty. Don\'t waste water.');
    }
    return { messages: msgs, newState: {} };
  }

  // --- EXAMINE SPECIFIC OBJECTS ---
  if (['examine pants', 'look at pants', 'inspect pants', 'smell pants', 'x pants'].includes(cmd)) {
    msgs.push(state.pantsOn
      ? 'Perfectly normal pants. Currently unstained. Let\'s keep it that way.'
      : 'Your pants are on the floor. Waiting patiently.');
    return { messages: msgs, newState: {} };
  }
  if (['examine toilet', 'look at toilet', 'inspect toilet', 'smell toilet', 'x toilet'].includes(cmd)) {
    if (state.location !== 'bathroom') {
      msgs.push('There\'s no toilet here.');
    } else {
      msgs.push('A gleaming white toilet. Your salvation.');
    }
    return { messages: msgs, newState: {} };
  }
  if (['examine door', 'look at door', 'inspect door', 'x door'].includes(cmd)) {
    if (state.location !== 'room') {
      msgs.push('The door is behind you.');
    } else {
      msgs.push(`A wooden door to the north. It is ${state.doorOpen ? 'open' : 'closed'}.`);
    }
    return { messages: msgs, newState: {} };
  }

  // --- FUNNY / FLAVOUR COMMANDS ---
  if (['smell', 'sniff', 'smell air'].includes(cmd)) {
    msgs.push('The air has a certain... urgency to it.');
    return { messages: msgs, newState: {} };
  }
  if (['run', 'sprint', 'hurry', 'rush', 'run faster'].includes(cmd)) {
    msgs.push('Your panicked shuffle could technically be called running.');
    return { messages: msgs, newState: {} };
  }
  if (['jump', 'hop', 'leap'].includes(cmd)) {
    msgs.push('Jumping is NOT recommended right now.');
    return { messages: msgs, newState: {} };
  }
  if (['eat', 'drink', 'eat something', 'drink something', 'eat food'].includes(cmd)) {
    msgs.push('You don\'t have time for that!');
    return { messages: msgs, newState: {} };
  }
  if (['scream', 'yell', 'shout'].includes(cmd)) {
    msgs.push('AAAHHH! This accomplishes nothing. The timer disagrees.');
    return { messages: msgs, newState: {} };
  }
  if (['cry', 'weep', 'sob'].includes(cmd)) {
    msgs.push('There\'s no time for crying. Clench and focus.');
    return { messages: msgs, newState: {} };
  }
  if (['dance', 'wiggle', 'boogie'].includes(cmd)) {
    msgs.push('This is absolutely NOT the time to dance.');
    return { messages: msgs, newState: {} };
  }
  if (['wait', 'rest', 'relax', 'pause'].includes(cmd)) {
    msgs.push('The timer strongly disagrees with your plan.');
    return { messages: msgs, newState: {} };
  }
  if (['xyzzy', 'plugh', 'plover'].includes(cmd)) {
    msgs.push('Nothing happens, but your bowels have opinions.');
    return { messages: msgs, newState: {} };
  }
  if (['konami', 'konami code', 'up up down down'].includes(cmd)) {
    msgs.push('That\'s what got you INTO this game.');
    return { messages: msgs, newState: {} };
  }
  if (['pray', 'meditate', 'wish'].includes(cmd)) {
    msgs.push('Your deity sends thoughts and prayers. You need a toilet.');
    return { messages: msgs, newState: {} };
  }
  if (['clench', 'hold', 'hold it', 'hold on'].includes(cmd)) {
    msgs.push('You clench with all your might. The timer disagrees.');
    return { messages: msgs, newState: {} };
  }
  if (['read', 'read book', 'read magazine'].includes(cmd)) {
    msgs.push('You cannot read right now. FOCUS.');
    return { messages: msgs, newState: {} };
  }
  if (['call', 'phone', 'call for help'].includes(cmd)) {
    msgs.push('911: "What\'s your emergency?" You: "I need to poop." 911: "..."');
    return { messages: msgs, newState: {} };
  }
  if (['kill', 'kill self', 'suicide', 'die'].includes(cmd)) {
    msgs.push('Stay positive. Get to the toilet.');
    return { messages: msgs, newState: {} };
  }

  // Programmer easter eggs
  if (cmd === 'sudo shit') {
    msgs.push('sudo: shit: command not found');
    msgs.push('The pants care not for root privileges.');
    return { messages: msgs, newState: {} };
  }
  if (cmd === 'ls' || cmd === 'dir') {
    const files = state.location === 'room'
      ? ['door/', 'pants', 'urgency', 'will_to_live']
      : ['toilet', 'sink', 'salvation', 'relief'];
    msgs.push(files.join('  '));
    return { messages: msgs, newState: {} };
  }
  if (cmd === 'pwd') {
    msgs.push(state.location === 'room' ? '/home/user/living_room' : '/home/user/bathroom');
    return { messages: msgs, newState: {} };
  }
  if (cmd === 'cd bathroom' || cmd === 'cd /bathroom') {
    if (state.location === 'bathroom') {
      msgs.push('Already in /bathroom');
    } else if (!state.doorOpen) {
      msgs.push('cd: bathroom: Permission denied (door is closed)');
    } else {
      msgs.push('Changed directory to /bathroom');
      ns.location = 'bathroom';
    }
    return { messages: msgs, newState: ns };
  }
  if (cmd.startsWith('cd ')) {
    msgs.push(`cd: ${cmd.slice(3)}: No such directory`);
    return { messages: msgs, newState: {} };
  }
  if (cmd === 'ps' || cmd === 'ps aux') {
    msgs.push('  PID  COMMAND');
    msgs.push(' 1337  bowels          [running, URGENT]');
    msgs.push(' 1338  pants           [at risk]');
    msgs.push(' 1339  self_control    [degrading]');
    msgs.push(' 1340  timer           [countdown]');
    return { messages: msgs, newState: {} };
  }
  if (cmd === 'git log') {
    msgs.push('commit a1b2c3d (HEAD -> main)');
    msgs.push('Author: You <you@example.com>');
    msgs.push('');
    msgs.push('    ate too much at lunch');
    return { messages: msgs, newState: {} };
  }
  if (cmd === 'git blame') {
    msgs.push('You have no one to blame but yourself.');
    return { messages: msgs, newState: {} };
  }
  if (cmd === 'git stash') {
    msgs.push('You cannot stash this. It is coming regardless.');
    return { messages: msgs, newState: {} };
  }
  if (cmd === 'npm install' || cmd === 'yarn' || cmd === 'bun install') {
    msgs.push('Now is NOT the time to install dependencies.');
    return { messages: msgs, newState: {} };
  }
  if (cmd.startsWith('git ')) {
    msgs.push('You can\'t commit your way out of this one.');
    return { messages: msgs, newState: {} };
  }

  // Catch-all
  msgs.push(`You can't "${input.trim()}" right now.`);
  return { messages: msgs, newState: {} };
}

function getArt(state: GameState): string {
  // Sitting on toilet
  if (state.sitting) {
    return [
      '  (*_*)',
      '   \\|/',
      '  __|___',
      ' (      )',
      '  ------',
      '   | |',
    ].join('\n');
  }

  // Bathroom — standing near toilet
  if (state.location === 'bathroom') {
    if (state.pantsOn) {
      return [
        '  (o_o)   ___',
        '   \\|/  (   )',
        '   _|_   ---',
        '  [===]  | |',
        '   | |',
        '  _| |_',
      ].join('\n');
    }
    return [
      '  (o_o)   ___',
      '   \\|/  (   )',
      '    |    ---',
      '    |   | |',
      '   | |',
      '  _| |_',
    ].join('\n');
  }

  // Room — door closed, pants on
  if (state.pantsOn && !state.doorOpen) {
    return [
      '  (o_o)  +--+',
      '   \\|/   |  |',
      '   _|_   +--+',
      '  [===]',
      '   | |',
      '  _| |_',
    ].join('\n');
  }

  // Room — door closed, no pants
  if (!state.pantsOn && !state.doorOpen) {
    return [
      '  (>_<)  +--+',
      '   \\|/   |  |',
      '    |    +--+',
      '    |',
      '   | |',
      '  _| |_',
    ].join('\n');
  }

  // Room — door open, pants on
  if (state.pantsOn) {
    return [
      '  (o_o)  +  +',
      '   \\|/   |  |',
      '   _|_   +  +',
      '  [===]',
      '   | |',
      '  _| |_',
    ].join('\n');
  }

  // Room — door open, no pants
  return [
    '  (>_<)  +  +',
    '   \\|/   |  |',
    '    |    +  +',
    '    |',
    '   | |',
    '  _| |_',
  ].join('\n');
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function DontShitYourPants({ isOpen, onClose }: Props) {
  const [state, setState] = useState<GameState>(INITIAL_STATE);
  const [history, setHistory] = useState<string[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [cmdHistory, setCmdHistory] = useState<string[]>([]);
  const [cmdIndex, setCmdIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const timerGameOverFiredRef = useRef(false);

  // Reset on open
  useEffect(() => {
    if (isOpen) {
      setState(INITIAL_STATE);
      setHistory(INITIAL_MESSAGES);
      setInput('');
      setCmdHistory([]);
      setCmdIndex(-1);
      timerGameOverFiredRef.current = false;
    }
  }, [isOpen]);

  // Auto-scroll log
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [history]);

  // Focus input
  useEffect(() => {
    if (isOpen) {
      const t = setTimeout(() => inputRef.current?.focus(), 100);
      return () => clearTimeout(t);
    }
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  // Countdown timer
  useEffect(() => {
    if (!isOpen || state.gameOver) return;
    const interval = setInterval(() => {
      setState(prev => {
        if (prev.timeLeft <= 1) {
          return { ...prev, timeLeft: 0, gameOver: true };
        }
        return { ...prev, timeLeft: prev.timeLeft - 1 };
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [isOpen, state.gameOver]);

  // Timer game over message (fires once when time hits 0)
  useEffect(() => {
    if (state.timeLeft === 0 && !state.won && !timerGameOverFiredRef.current) {
      timerGameOverFiredRef.current = true;
      setHistory(prev => [
        ...prev,
        '',
        'The pressure becomes too great.',
        'You shit your pants.',
        '',
        '[ GAME OVER ]',
      ]);
    }
  }, [state.timeLeft, state.won]);

  // Urgency warning at 10 seconds
  const urgencyFiredRef = useRef(false);
  useEffect(() => {
    if (state.timeLeft === 10 && !urgencyFiredRef.current && !state.gameOver) {
      urgencyFiredRef.current = true;
      setHistory(prev => [...prev, '', '** CRITICAL URGENCY — HURRY! **', '']);
    }
  }, [state.timeLeft, state.gameOver]);

  // Reset urgency ref on new game
  useEffect(() => {
    if (isOpen) {
      urgencyFiredRef.current = false;
    }
  }, [isOpen]);

  const handleSubmit = useCallback(() => {
    if (!input.trim() || state.gameOver) return;
    const cmd = input.trim();
    setCmdHistory(prev => [cmd, ...prev]);
    setCmdIndex(-1);
    setHistory(prev => [...prev, `> ${cmd}`]);
    const { messages, newState } = parseCommand(cmd, state);
    setHistory(prev => [...prev, ...messages]);
    setState(prev => ({ ...prev, ...newState }));
    setInput('');
  }, [input, state]);

  if (!isOpen) return null;

  const timerColor =
    state.timeLeft <= 10
      ? 'text-red-400 animate-pulse'
      : state.timeLeft <= 20
        ? 'text-yellow-400'
        : 'text-green-400';

  const art = getArt(state);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/90" onClick={onClose} />

      {/* Game window */}
      <div
        className="relative w-full max-w-lg font-mono"
        style={{
          background: '#000',
          border: '2px solid #22c55e',
          boxShadow: '0 0 40px rgba(34,197,94,0.25), inset 0 0 40px rgba(0,20,0,0.5)',
        }}
      >
        {/* Title bar */}
        <div
          className="flex justify-between items-center px-4 py-2 border-b"
          style={{ borderColor: 'rgba(34,197,94,0.3)', background: 'rgba(0,20,0,0.8)' }}
        >
          <span className={`text-sm font-bold tabular-nums ${timerColor}`}>
            TIMER: {formatTime(state.timeLeft)}
          </span>
          <span className="text-xs text-green-700 tracking-widest">DON'T SHIT YOUR PANTS</span>
          <button
            onClick={onClose}
            className="text-sm text-green-700 hover:text-green-400 transition-colors tracking-wider"
          >
            QUIT
          </button>
        </div>

        {/* ASCII art / scene */}
        <div
          className="flex items-start justify-center gap-6 py-4 px-6"
          style={{ background: 'rgba(0,10,0,0.6)' }}
        >
          <pre
            className="text-green-500 text-xs leading-tight select-none"
            style={{ minWidth: '14ch' }}
          >
            {art}
          </pre>
          <div className="text-xs text-green-700 leading-relaxed pt-1">
            <div className="text-green-500 font-bold mb-1">
              {state.location === 'room' ? '[ LIVING ROOM ]' : '[ BATHROOM ]'}
            </div>
            {state.pantsOn
              ? <div>wearing: <span className="text-green-400">pants</span></div>
              : <div>wearing: <span className="text-red-400">nothing (below waist)</span></div>
            }
            {state.location === 'bathroom' && (
              <div>
                sitting:{' '}
                <span className={state.sitting ? 'text-green-400' : 'text-green-700'}>
                  {state.sitting ? 'yes' : 'no'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Text log */}
        <div
          ref={logRef}
          className="h-48 overflow-y-auto px-4 py-2 text-sm leading-relaxed"
          style={{
            background: '#000',
            scrollbarWidth: 'thin',
            scrollbarColor: '#14532d #000',
          }}
        >
          {history.map((line, i) => {
            const isCmd = line.startsWith('>');
            const isWin = line.includes('YOU DID IT') || line.includes('Achievement');
            const isLose = line.includes('GAME OVER');
            const isUrgent = line.includes('CRITICAL URGENCY');
            return (
              <div
                key={i}
                className={
                  isCmd
                    ? 'text-green-300'
                    : isWin
                      ? 'text-yellow-400 font-bold'
                      : isLose
                        ? 'text-red-400 font-bold'
                        : isUrgent
                          ? 'text-red-400 animate-pulse'
                          : 'text-green-600'
                }
              >
                {line || '\u00A0'}
              </div>
            );
          })}
        </div>

        {/* Input */}
        <div
          className="flex items-center px-4 py-2 border-t gap-2"
          style={{ borderColor: 'rgba(34,197,94,0.3)', background: 'rgba(0,10,0,0.8)' }}
        >
          <span className="text-green-500 select-none">&gt;</span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') {
                handleSubmit();
              } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                const idx = Math.min(cmdIndex + 1, cmdHistory.length - 1);
                setCmdIndex(idx);
                setInput(cmdHistory[idx] ?? '');
              } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                const idx = Math.max(cmdIndex - 1, -1);
                setCmdIndex(idx);
                setInput(idx === -1 ? '' : cmdHistory[idx]);
              }
            }}
            disabled={state.gameOver}
            className="flex-1 bg-transparent text-green-400 outline-none text-sm"
            style={{ caretColor: '#22c55e' }}
            placeholder={
              state.gameOver
                ? state.won
                  ? 'YOU WIN — press ESC to close'
                  : 'GAME OVER — press ESC to close'
                : 'enter command...'
            }
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
          />
        </div>

        {/* Footer hint */}
        <div
          className="text-center text-xs text-green-900 py-1"
          style={{ background: 'rgba(0,10,0,0.8)' }}
        >
          ↑/↓ command history · ESC to quit · Konami code to replay
        </div>
      </div>
    </div>
  );
}
