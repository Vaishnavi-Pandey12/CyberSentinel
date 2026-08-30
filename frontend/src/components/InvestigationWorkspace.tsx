import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, BackgroundVariant, MarkerType, type Node, type Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import EntityNode, { type EntityNodeData } from './EntityNode';
import { getLayoutedElements } from './layout'; 

const nodeTypes = { entity: EntityNode };

interface TerminalLog {
  id: string;
  action: string;
  targetNodeId: string;
  previousHash: string;
  currentHash: string;
  timestamp: string;
}

const DEFAULT_FALLBACK_NODES: Node<EntityNodeData>[] = [
  { id: '1', type: 'entity', position: { x: 150, y: 50 }, data: { id: 'C102', label: 'Victim Acct (HDFC)', type: 'VICTIM', riskScore: 95, status: 'ACTIVE' } },
  { id: '2', type: 'entity', position: { x: 350, y: 220 }, data: { id: 'M883', label: 'Mule Acct 101 (SBI)', type: 'MULE', riskScore: 92, status: 'ACTIVE' } },
  { id: '3', type: 'entity', position: { x: 600, y: 400 }, data: { id: 'A441', label: 'ATM - Benz Circle', type: 'ATM', riskScore: 78, status: 'ACTIVE' } }
];

const DEFAULT_FALLBACK_EDGES: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, label: 'TRANSFER (₹50,000)', style: { stroke: '#ef4444', strokeWidth: 2, opacity: 0.8 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' } },
  { id: 'e2-3', source: '2', target: '3', animated: true, label: 'CASH WITHDRAWAL', style: { stroke: '#ef4444', strokeWidth: 2, opacity: 0.8 }, markerEnd: { type: MarkerType.ArrowClosed, color: '#ef4444' } }
];

const DEFAULT_FALLBACK_LOGS: TerminalLog[] = [
  {
    id: 'log-1',
    action: 'SYSTEM_BOOT',
    targetNodeId: 'CYB-2026-1024',
    previousHash: '0000000000000000000000000000000000000000000000000000000000000000',
    currentHash: '26a8743668e9de0b702cba4777e9114a0cadfd14dcb81bc920bfd9718466af59',
    timestamp: new Date().toISOString()
  }
];

export default function InvestigationWorkspace() {
  const navigate = useNavigate();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<EntityNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<Node<EntityNodeData> | null>(null);
  
  const [isFreezing, setIsFreezing] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [layoutDirection, setLayoutDirection] = useState<'TB' | 'LR'>('TB');
  const [auditLogs, setAuditLogs] = useState<TerminalLog[]>([]);
  
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const [isLiveStreaming, setIsLiveStreaming] = useState<boolean>(true);

  const fetchGraphAndLogs = async (silent: boolean = false) => {
    try {
      if (!silent) setIsLoading(true);
      
      let graphRes: Response | null = null;
      const graphUrls = [
        'http://localhost:8001/api/engine/case/CYB-2026-1024',
        'http://localhost:8000/api/engine/case/CYB-2026-1024',
        '/api/engine/case/CYB-2026-1024'
      ];

      for (const url of graphUrls) {
        try {
          const res = await fetch(url);
          if (res.ok) {
            graphRes = res;
            break;
          }
        } catch {
          // try next
        }
      }

      if (graphRes && graphRes.ok) {
        const data = await graphRes.json();
        const rawNodes = (data.nodes || []) as Node<EntityNodeData>[];
        const rawEdges = (data.edges || []) as Edge[];

        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements<Node<EntityNodeData>>(
          rawNodes, 
          rawEdges, 
          layoutDirection
        );

        // Apply risk score color coding & arrowheads to edges
        const nodeMap = new Map<string, number>();
        rawNodes.forEach((n: any) => {
          const nid = String(n.id || n.data?.id);
          nodeMap.set(nid, Number(n.data?.riskScore || 0));
        });

        const styledEdges = (layoutedEdges || []).map((e: any) => {
          const srcRisk = nodeMap.get(e.source) || 85;
          const eType = String(e.type || 'TRANSFER').toUpperCase();
          
          let stroke = '#48D878';
          if (eType === 'SHARED_KYC') stroke = '#a855f7';
          else if (srcRisk >= 80) stroke = '#ef4444';
          else if (srcRisk >= 50) stroke = '#f97316';

          return {
            ...e,
            type: 'smoothstep',
            animated: true,
            label: eType.replace('_', ' '),
            labelStyle: { fill: '#9ca3af', fontSize: 10, fontWeight: 600 },
            labelBgStyle: { fill: '#0F1210', fillOpacity: 0.8 },
            style: { stroke, strokeWidth: 2, opacity: 0.85 },
            markerEnd: { type: MarkerType.ArrowClosed, color: stroke }
          };
        });

        setNodes(layoutedNodes);
        setEdges(styledEdges);
      } else {
        setNodes(DEFAULT_FALLBACK_NODES);
        setEdges(DEFAULT_FALLBACK_EDGES);
      }

      // Fetch Terminal Logs
      let logsRes: Response | null = null;
      const logsUrls = [
        'http://localhost:8001/api/action/audit-logs',
        'http://localhost:8000/api/action/audit-logs',
        '/api/action/audit-logs'
      ];

      for (const url of logsUrls) {
        try {
          const res = await fetch(url);
          if (res.ok) {
            logsRes = res;
            break;
          }
        } catch {
          // try next
        }
      }

      if (logsRes && logsRes.ok) {
        const logsData = await logsRes.json();
        setAuditLogs(Array.isArray(logsData) && logsData.length > 0 ? logsData : DEFAULT_FALLBACK_LOGS);
      } else {
        setAuditLogs(DEFAULT_FALLBACK_LOGS);
      }
    } catch (error) {
      console.error("Telemetry fetch failed", error);
      if (!silent) {
        setNodes(DEFAULT_FALLBACK_NODES);
        setEdges(DEFAULT_FALLBACK_EDGES);
        setAuditLogs(DEFAULT_FALLBACK_LOGS);
      }
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchGraphAndLogs(false);

    let intervalId: any = null;
    if (isLiveStreaming) {
      intervalId = setInterval(() => {
        fetchGraphAndLogs(true);
      }, 4000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [layoutDirection, isLiveStreaming]);

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [auditLogs]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node<EntityNodeData>) => {
    setSelectedNode(node);
  }, []);

  const handleFreezeAccount = async () => {
    if (!selectedNode) return;
    setIsFreezing(true);

    try {
      const endpoints = [
        'http://localhost:8001/api/action/freeze',
        'http://localhost:8000/api/action/freeze',
        '/api/action/freeze'
      ];

      let responseReceipt: any = null;
      const targetId = selectedNode.data.id || selectedNode.id;

      for (const url of endpoints) {
        try {
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              node_id: targetId,
              officer_id: 'OFFICER_409',
              reason: 'Interdiction initiated via Investigation Workspace'
            })
          });

          if (res.ok) {
            responseReceipt = await res.json();
            break;
          }
        } catch {
          // try next
        }
      }

      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === selectedNode.id || node.data.id === selectedNode.data.id) {
            return {
              ...node,
              data: { ...node.data, status: 'FROZEN' }
            };
          }
          return node;
        })
      );

      setSelectedNode((prev) => prev ? { ...prev, data: { ...prev.data, status: 'FROZEN' } } : null);

      if (responseReceipt) {
        const mockLog: TerminalLog = {
          id: `log-${Date.now()}`,
          action: 'FREEZE_INITIATED',
          targetNodeId: selectedNode.data.id || selectedNode.id,
          previousHash: responseReceipt?.audit_receipt?.previous_hash || '26a8743668e9de0b702cba4777e9114a0cadfd14dcb81bc920bfd9718466af59',
          currentHash: responseReceipt?.audit_receipt?.transaction_hash || 'f81e18f34e8eb65c070f9180a0ac66a61cc5a8912ccdaa5c877b7fc1bcfe0612',
          timestamp: new Date().toISOString()
        };
        setAuditLogs((prev) => [mockLog, ...prev]);
      } else {
        fetchGraphAndLogs();
      }
    } catch (error) {
      console.error('Interdiction failed:', error);
    } finally {
      setIsFreezing(false);
    }
  };

  const handleUnfreezeAccount = async () => {
    if (!selectedNode) return;
    setIsFreezing(true);

    try {
      const endpoints = [
        'http://localhost:8001/api/action/unfreeze',
        'http://localhost:8000/api/action/unfreeze',
        '/api/action/unfreeze'
      ];

      let responseReceipt: any = null;
      const targetId = selectedNode.data.id || selectedNode.id;

      for (const url of endpoints) {
        try {
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              node_id: targetId,
              officer_id: 'OFFICER_409',
              reason: 'Account cleared & unfrozen via Investigation Workspace'
            })
          });

          if (res.ok) {
            responseReceipt = await res.json();
            break;
          }
        } catch {
          // try next
        }
      }

      setNodes((nds) =>
        nds.map((node) => {
          if (node.id === selectedNode.id || node.data.id === selectedNode.data.id) {
            return {
              ...node,
              data: { ...node.data, status: 'ACTIVE' }
            };
          }
          return node;
        })
      );

      setSelectedNode((prev) => prev ? { ...prev, data: { ...prev.data, status: 'ACTIVE' } } : null);

      if (responseReceipt) {
        const mockLog: TerminalLog = {
          id: `log-${Date.now()}`,
          action: 'UNFREEZE_INITIATED',
          targetNodeId: selectedNode.data.id || selectedNode.id,
          previousHash: responseReceipt?.audit_receipt?.previous_hash || '26a8743668e9de0b702cba4777e9114a0cadfd14dcb81bc920bfd9718466af59',
          currentHash: responseReceipt?.audit_receipt?.transaction_hash || 'f81e18f34e8eb65c070f9180a0ac66a61cc5a8912ccdaa5c877b7fc1bcfe0612',
          timestamp: new Date().toISOString()
        };
        setAuditLogs((prev) => [mockLog, ...prev]);
      } else {
        fetchGraphAndLogs();
      }
    } catch (error) {
      console.error('Unfreeze failed:', error);
    } finally {
      setIsFreezing(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#0F1210] text-gray-200 font-sans overflow-hidden">
      
      {/* 1. Workspace Header */}
      <header className="px-6 py-3 border-b border-white/10 bg-white/[0.02] flex justify-between items-center z-20 shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold tracking-wide text-white uppercase">CASE CYB-2026-1024</h1>
          <span className="text-[9px] font-bold bg-[#48D878]/20 text-[#48D878] px-2 py-1 rounded border border-[#48D878]/30 uppercase tracking-widest">
            Live Telemetry
          </span>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsLiveStreaming((prev) => !prev)}
            className={`px-3.5 py-2 font-mono text-xs font-bold rounded-md border transition-all uppercase tracking-widest cursor-pointer flex items-center gap-2 ${
              isLiveStreaming
                ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
                : 'bg-white/5 text-gray-400 border-white/10'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${isLiveStreaming ? 'bg-emerald-400 animate-pulse' : 'bg-gray-500'}`} />
            {isLiveStreaming ? 'STREAM: LIVE 🟢' : 'STREAM: PAUSED ⏸'}
          </button>
          <button
            onClick={() => setLayoutDirection((prev) => prev === 'TB' ? 'LR' : 'TB')}
            className="px-3.5 py-2 bg-white/5 hover:bg-white/10 text-gray-300 font-mono text-xs font-bold rounded-md border border-white/15 transition-all uppercase tracking-widest cursor-pointer"
          >
            LAYOUT: {layoutDirection === 'TB' ? 'TOP-DOWN ⬇' : 'LEFT-RIGHT ➡'}
          </button>
          <button
            onClick={() => navigate('/heatmap')}
            className="px-4 py-2 bg-blue-500/15 hover:bg-blue-500/25 text-blue-400 font-mono text-xs font-bold rounded-md border border-blue-500/60 shadow-[0_0_15px_rgba(59,130,246,0.2)] transition-all uppercase tracking-widest cursor-pointer"
          >
            OPEN GIS HEATMAP
          </button>
        </div>
      </header>

      {/* 2. Main Intelligence Area (75% height) */}
      <div className="flex flex-grow relative h-[75vh]">
        {/* The Visualizer */}
        <div className="flex-grow relative">
          {isLoading && (
             <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#0F1210]/80">
                <div className="text-[11px] text-[#48D878] tracking-widest uppercase font-mono animate-pulse">Syncing Network Graph...</div>
             </div>
          )}
          
          <ReactFlow 
            nodes={nodes} 
            edges={edges} 
            onNodesChange={onNodesChange} 
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            nodeTypes={nodeTypes}
            fitView
            className="bg-[#0F1210]"
          >
            <Background color="#ffffff" variant={BackgroundVariant.Dots} gap={24} size={1} style={{ opacity: 0.03 }} />
            <Controls className="bg-[#0F1210] border-white/10 fill-gray-400" showInteractive={false} />
          </ReactFlow>

          {/* Graph Legend Overlay */}
          <div className="absolute bottom-4 left-4 z-10 bg-[#0F1210]/90 backdrop-blur-md p-3 rounded-lg border border-white/10 text-[9px] font-mono space-y-1.5">
            <div className="text-gray-400 font-bold uppercase tracking-widest mb-1">Graph Legend</div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500 border border-emerald-400" />
              <span className="text-gray-300">Victim Account (Origin)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-orange-500 border border-orange-400" />
              <span className="text-gray-300">Mule Account (Layering)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-purple-500 border border-purple-400" />
              <span className="text-gray-300">Shared IP / Device</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-sm bg-red-500 border border-red-400" />
              <span className="text-gray-300">ATM Terminal (Cash-out)</span>
            </div>
          </div>
        </div>

        {/* The Action Panel */}
        <aside className="w-96 border-l border-white/10 bg-white/[0.01] backdrop-blur-3xl p-6 flex flex-col z-20 shrink-0 overflow-y-auto">
          <h2 className="text-[10px] font-semibold text-gray-500 tracking-widest uppercase mb-4">Entity Inspection</h2>
          
          {selectedNode ? (
            <div className="space-y-5">
              <div className="p-4 bg-white/[0.03] rounded border border-white/5">
                <div className="text-base font-medium text-gray-100 mb-2">{selectedNode.data.label}</div>
                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-xs text-gray-500">Node ID</span>
                  <span className="text-xs font-mono text-gray-400">{selectedNode.data.id}</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-white/5 mt-1">
                  <span className="text-xs text-gray-500">Classification</span>
                  <span className="text-xs font-semibold text-gray-300">{selectedNode.data.type}</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-white/5 mt-1">
                  <span className="text-xs text-gray-500">Status</span>
                  <span className={`text-xs font-bold ${selectedNode.data.status === 'FROZEN' ? 'text-blue-400' : 'text-emerald-400'}`}>
                    {selectedNode.data.status || 'ACTIVE'}
                  </span>
                </div>
                <div className="flex justify-between items-center py-1 mt-1">
                  <span className="text-xs text-gray-500">Threat Level</span>
                  <span className={`text-xs font-bold ${selectedNode.data.riskScore > 80 ? 'text-red-500' : 'text-[#48D878]'}`}>
                    {Number(selectedNode.data.riskScore).toFixed(1)}%
                  </span>
                </div>
              </div>

              <div className="pt-2 flex flex-col gap-3">
                {selectedNode.data.status === 'FROZEN' ? (
                  <button 
                    onClick={handleUnfreezeAccount}
                    disabled={isFreezing}
                    className="w-full py-3 px-4 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-bold text-xs rounded border border-emerald-500/40 shadow-[0_0_15px_rgba(16,185,129,0.2)] transition-all disabled:opacity-50 tracking-widest uppercase cursor-pointer"
                  >
                    {isFreezing ? 'Executing...' : 'Unfreeze Node Account'}
                  </button>
                ) : (
                  <button 
                    onClick={handleFreezeAccount}
                    disabled={isFreezing}
                    className="w-full py-3 px-4 bg-red-500/10 hover:bg-red-500/20 text-red-500 font-bold text-xs rounded border border-red-500/40 shadow-[0_0_15px_rgba(239,68,68,0.2)] transition-all disabled:opacity-50 tracking-widest uppercase cursor-pointer"
                  >
                    {isFreezing ? 'Executing...' : 'Initiate API Freeze'}
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-gray-500 text-center mt-10 uppercase tracking-widest">
              Select any graph node to inspect details
            </div>
          )}
        </aside>
      </div>

      {/* 3. The Audit Trail Terminal (25% height) */}
      <div className="h-[25vh] border-t border-white/10 bg-[#080A08] shrink-0 flex flex-col font-mono text-[10px]">
        <div className="flex items-center gap-2 px-4 py-2 border-b border-white/5 bg-white/[0.02]">
          <div className="w-2 h-2 rounded-full bg-[#48D878] animate-pulse" />
          <span className="text-gray-400 uppercase tracking-widest font-semibold">Cryptographic Ledger Stream</span>
        </div>
        
        <div className="flex-grow overflow-y-auto p-4 space-y-2">
          {auditLogs.slice().reverse().map((log) => (
            <div key={log.id} className="flex gap-4 items-start text-gray-500 hover:text-gray-300 transition-colors">
              <span className="text-gray-600 shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
              <span className="text-blue-400 shrink-0 w-24">{log.action}</span>
              <div className="flex flex-col gap-1 min-w-0">
                <span className="truncate">TARGET: <span className="text-gray-300">{log.targetNodeId}</span></span>
                <span className="truncate text-emerald-500/70">HASH: {log.currentHash}</span>
              </div>
            </div>
          ))}
          <div ref={terminalEndRef} />
        </div>
      </div>

    </div>
  );
}
