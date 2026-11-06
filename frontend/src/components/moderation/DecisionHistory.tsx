import { Loader2, Undo2 } from 'lucide-react';
import { type Decision, canUndoApproval, itemKey, itemThumbnail, itemTitle, typeIcons } from './pendingItems';

interface DecisionHistoryProps {
  history: Decision[];
  onUndo: (decision: Decision) => void;
  /** The decision being undone right now. */
  undoingKey: string | null;
}

/** This session's approvals and rejections, newest first; an approval can be undone. */
export default function DecisionHistory({ history, onUndo, undoingKey }: DecisionHistoryProps) {
  if (!history.length) return <p className="text-sm text-gray-500 py-2">No decisions yet in this session.</p>;
  return (
    <ul className="divide-y divide-cyber-light/10">
      {history.map((d) => {
        const key = itemKey(d.item);
        const thumb = itemThumbnail(d.item);
        const TypeIcon = typeIcons[d.item.type];
        const undoable = d.approved && canUndoApproval(d.item.type);
        return (
          <li key={key} className="flex items-center gap-3 py-2">
            {thumb
              ? <img src={thumb} alt="" className="h-9 w-9 flex-shrink-0 object-contain bg-black/40 border border-cyber-light/20" />
              : <TypeIcon className="h-5 w-5 mx-2 flex-shrink-0 text-gray-500" />}
            <div className="min-w-0 flex-1">
              <div className="text-sm text-white truncate">{itemTitle(d.item)}</div>
              <div className="text-xs font-mono text-gray-500">
                {d.approved ? <span className="text-cyber-green">APPROVED</span> : <span className="text-cyber-pink">REJECTED</span>}
                {' · '}{new Date(d.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
            {undoable ? (
              <button onClick={() => onUndo(d)} disabled={!!undoingKey} title="Put it back in the queue"
                className="btn-cyber text-xs inline-flex items-center gap-1 disabled:opacity-50">
                {undoingKey === key ? <Loader2 className="h-3 w-3 animate-spin" /> : <Undo2 className="h-3 w-3" />} Undo
              </button>
            ) : (
              <span className="text-xs font-mono text-gray-600">{d.approved ? 'now in the parts list' : 'deleted'}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
