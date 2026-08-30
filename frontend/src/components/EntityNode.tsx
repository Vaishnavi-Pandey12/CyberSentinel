import { Handle, Position, NodeProps, Node } from '@xyflow/react';

export interface EntityNodeData extends Record<string, unknown> {
  id: string;
  label: string;
  type: 'VICTIM' | 'MULE' | 'ATM' | 'DEVICE';
  riskScore: number;
  status: 'ACTIVE' | 'FROZEN' | 'INVESTIGATING';
}

export default function EntityNode({ data }: NodeProps<Node<EntityNodeData>>) {
  const isFrozen = data.status === 'FROZEN';
  const score = data.riskScore || 0;

  // CyberSentinel strict risk color coding
  const getRiskStyling = (risk: number) => {
    if (risk >= 85) return { text: 'text-red-500', border: 'border-red-500/50', glow: 'shadow-[0_0_15px_rgba(239,68,68,0.2)]' }; // CRITICAL
    if (risk >= 70) return { text: 'text-orange-500', border: 'border-orange-500/50', glow: 'shadow-[0_0_15px_rgba(249,115,22,0.2)]' }; // HIGH
    if (risk >= 50) return { text: 'text-yellow-500', border: 'border-yellow-500/50', glow: 'shadow-[0_0_15px_rgba(234,179,8,0.2)]' }; // MEDIUM
    return { text: 'text-[#48D878]', border: 'border-[#48D878]/40', glow: 'shadow-[0_0_10px_rgba(72,216,120,0.1)]' }; // LOW
  };

  const style = getRiskStyling(score);
  
  // Override styling if operational status is FROZEN
  const activeStyle = isFrozen 
    ? { text: 'text-blue-400', border: 'border-blue-500/50', glow: 'shadow-[0_0_15px_rgba(59,130,246,0.3)]' }
    : style;

  return (
    <div className={`bg-white/[0.03] backdrop-blur-md border ${activeStyle.border} ${activeStyle.glow} rounded-lg p-4 min-w-[200px] text-gray-200 transition-all`}>
      <Handle type="target" position={Position.Top} className="w-2 h-2 bg-gray-500 border-none" />
      
      <div className="flex justify-between items-center mb-4">
        <span className="text-[10px] font-semibold tracking-widest uppercase text-gray-400">
          {data.type}
        </span>
        {isFrozen && (
          <span className="text-[9px] font-bold bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30 uppercase tracking-wider">
            Frozen
          </span>
        )}
      </div>
      
      <div className="text-sm font-medium tracking-wide mb-1 truncate" title={data.id}>
        {data.label}
      </div>
      
      <div className="flex justify-between items-end mt-5">
        <span className="text-[10px] uppercase tracking-wider text-gray-500">Risk Score</span>
        <span className={`text-base font-bold ${activeStyle.text}`}>
          {score}
        </span>
      </div>

      <Handle type="source" position={Position.Bottom} className="w-2 h-2 bg-gray-500 border-none" />
    </div>
  );
}
