import React, { useState, useCallback, useEffect, useRef } from 'react';
import { ReactFlow, Background, Controls, useNodesState, useEdgesState, BackgroundVariant, type Node, type Edge } from '@xyflow/react';
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
  { id: '2', type: 'entity', position: { x: 300, y: 200 }, data: { id: 'M883', label: 'Mule Acct 101 (SBI)', type: 'MULE', riskScore: 92, status: 'ACTIVE' } },
  { id: '3', type: 'entity', position: { x: 450, y: 350 }, data: { id: 'A441', label: 'ATM - Benz Circle', type: 'ATM', riskScore: 78, status: 'ACTIVE' } }
];

const DEFAULT_FALLBACK_EDGES: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#ef4444', strokeWidth: 2, opacity: 0.8 } },
  { id: 'e2-3', source: '2', target: '3', animated: true, style: { stroke: '#ef4444', strokeWidth: 2, opacity: 0.8 } }
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
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<EntityNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<Node<EntityNodeData> | null>(null);
  
  const [isFreezing, setIsFreezing] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [auditLogs, setAuditLogs] = useState<TerminalLog[]>([]);
  
  const terminalEndRef = useRef<HTMLDivElement>(null);

  const fetchGraphAndLogs = async () => {
    try {
      setIsLoading(true);
      
      // Try ports 8000, 8001, or relative /api
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
        const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements<Node<EntityNodeData>>(
          (data.nodes || []) as Node<EntityNodeData>[], 
          data.edges || [], 
          'TB'
        );

        // Apply risk score color coding to edges
        const nodeMap = new Map<string, number>();
        (data.nodes || []).forEach((n: any) => {
          nodeMap.set(String(n.id), Number(n.data?.riskScore || 0));
        });

        const styledEdges = (layoutedEdges || []).map((e: Edge) => {
          const srcRisk = nodeMap.get(e.source) || 85;
          const stroke = srcRisk >= 80 ? '#ef4444' : (srcRisk >= 50 ? '#f97316' : '#48D878');
          return {
            ...e,
            animated: true,
            style: { stroke, strokeWidth: 2, opacity: 0.8 }
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
      setNodes(DEFAULT_FALLBACK_NODES);
      setEdges(DEFAULT_FALLBACK_EDGES);
      setAuditLogs(DEFAULT_FALLBACK_LOGS);
    } finally {
      setIsLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchGraphAndLogs();
  }, [setNodes, setEdges]);

  // Auto-scroll terminal when new logs arrive
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [auditLogs]);

  const onNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
    setSelectedNode(node as Node<EntityNodeData>);
  }, []);

  const handleFreezeAccount = async () => {
    if (!selectedNode) return;
    setIsFreezing(true);
    
    try {
      const freezeUrls = [
        'http://localhost:8001/api/action/freeze',
        'http://localhost:8000/api/action/freeze',
        '/api/action/freeze'
      ];

      let freezeSuccess = false;
      let responseReceipt: any = null;

      for (const url of freezeUrls) {
        try {
          const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              node_id: selectedNode.data.id || selectedNode.id,
              officer_id: 'OFFICER_IND_774',
              reason: 'Automated high-risk graph interdiction'
            })
          });

          if (response.ok) {
            responseReceipt = await response.json();
            freezeSuccess = true;
            break;
          }
        } catch {
          // try next
        }
      }

      // Optimistically update the UI graph
      setNodes((nds) => 
        nds.map((n) => n.id === selectedNode.id ? { ...n, data: { ...n.data, status: 'FROZEN' as const } } : n)
      );

      if (!freezeSuccess) {
        // Fallback local receipt if offline
        const mockLog: TerminalLog = {
          id: `log-${Date.now()}`,
          action: 'FREEZE_INITIATED',
          targetNodeId: selectedNode.data.id || selectedNode.id,
          previousHash: '26a8743668e9de0b702cba4777e9114a0cadfd14dcb81bc920bfd9718466af59',
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

  return (
    <div className="flex flex-col h-screen bg-[#0F1210] text-gray-200 font-sans overflow-hidden">
      
      {/* 1. Header */}
      <header className="px-6 py-3 border-b border-white/10 bg-white/[0.02] flex justify-between items-center z-20 shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-semibold tracking-wide text-white uppercase">CASE CYB-2026-1024</h1>
          <span className="text-[9px] font-bold bg-[#48D878]/20 text-[#48D878] px-2 py-1 rounded border border-[#48D878]/30 uppercase tracking-widest">
            Live Telemetry
          </span>
        </div>
      </header>

      {/* 2. Main Intelligence Area (75% height) */}
      <div className="flex flex-grow relative h-[75vh]">
        {/* The Visualizer */}
        <div className="flex-grow relative">
          {isLoading && (
             <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#0F1210]/80">
                <div className="text-[11px] text-[#48D878] tracking-widest uppercase font-mono animate-pulse">Syncing...</div>
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
            <Background color="#ffffff" variant={BackgroundVariant.Dots} gap={20} size={1} style={{ opacity: 0.03 }} />
            <Controls className="bg-[#0F1210] border-white/10 fill-gray-400" showInteractive={false} />
          </ReactFlow>
        </div>

        {/* The Action Panel */}
        <aside className="w-96 border-l border-white/10 bg-white/[0.01] backdrop-blur-3xl p-6 flex flex-col z-20 shrink-0 overflow-y-auto">
          <h2 className="text-[10px] font-semibold text-gray-500 tracking-widest uppercase mb-4">Entity Inspection</h2>
          
          {selectedNode ? (
            <div className="space-y-5">
              <div className="p-4 bg-white/[0.03] rounded border border-white/5">
                <div className="text-base font-medium text-gray-100 mb-2">{selectedNode.data.label}</div>
                <div className="flex justify-between items-center py-1 border-b border-white/5">
                  <span className="text-xs text-gray-500">ID</span>
                  <span className="text-xs font-mono text-gray-400">{selectedNode.data.id}</span>
                </div>
                <div className="flex justify-between items-center py-1 border-b border-white/5 mt-1">
                  <span className="text-xs text-gray-500">Classification</span>
                  <span className="text-xs font-semibold text-gray-300">{selectedNode.data.type}</span>
                </div>
                <div className="flex justify-between items-center py-1 mt-1">
                  <span className="text-xs text-gray-500">Threat Level</span>
                  <span className={`text-xs font-bold ${selectedNode.data.riskScore > 80 ? 'text-red-500' : 'text-[#48D878]'}`}>
                    {Number(selectedNode.data.riskScore).toFixed(1)}
                  </span>
                </div>
              </div>

              {selectedNode.data.type === 'MULE' && selectedNode.data.status !== 'FROZEN' && (
                <div className="pt-2">
                  <button 
                    onClick={handleFreezeAccount}
                    disabled={isFreezing}
                    className="w-full py-3 px-4 bg-red-500/10 hover:bg-red-500/20 text-red-500 font-bold text-xs rounded border border-red-500/40 shadow-[0_0_15px_rgba(239,68,68,0.15)] transition-all disabled:opacity-50 tracking-widest uppercase cursor-pointer"
                  >
                    {isFreezing ? 'Executing...' : 'Initiate API Freeze'}
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="text-[11px] text-gray-500 text-center mt-10 uppercase tracking-widest">
              Awaiting Target Selection
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
          {/* We reverse the logs here so the newest appears at the bottom of the terminal */}
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
