import React from "react";

export default function Home() {
  const modules = [
    {
      name: "Shield Policy Engine",
      role: "Deterministic Authorization",
      status: "Skeleton Initialized",
      desc: "Centralized policy enforcement & action guardrails.",
      color: "from-blue-500 to-indigo-600",
    },
    {
      name: "Fraud Scoring Agent",
      role: "ML + LLM Investigation",
      status: "Directories Created",
      desc: "Analyzes transactions, triggers automated or manual reviews.",
      color: "from-cyan-500 to-blue-600",
    },
    {
      name: "Payment Recovery Agent",
      role: "Recovery + Tools + RAG",
      status: "Directories Created",
      desc: "Negotiates recoveries and handles dunning steps via tools.",
      color: "from-emerald-500 to-teal-600",
    },
    {
      name: "Growth Decisions Agent",
      role: "Growth + Tools + RAG",
      status: "Directories Created",
      desc: "Assesses risk-adjusted limits and credit expansions.",
      color: "from-purple-500 to-pink-600",
    },
  ];

  const files = [
    { path: "backend/app/main.py", type: "FastAPI Entry" },
    { path: "frontend/app/page.tsx", type: "Next.js UI" },
    { path: "docker-compose.yml", type: "Services Stack" },
    { path: "data/raw/fraud/", type: "Data Lake Shell" },
    { path: "policies/", type: "Guardrail Policies" },
  ];

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-slate-950 px-4 py-16 sm:px-6 lg:px-8">
      {/* Background Glows */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/3 w-[300px] h-[300px] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-4xl space-y-12">
        {/* Header Section */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-semibold tracking-wide uppercase">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Day 1 Setup Complete
          </div>
          <h1 className="text-4xl sm:text-6xl font-black tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            AgentShield
          </h1>
          <p className="text-lg text-slate-400 max-w-2xl mx-auto font-medium">
            Centralized deterministic authorization and risk policy enforcement for financial AI agents.
          </p>
        </div>

        {/* Modules Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {modules.map((mod, idx) => (
            <div
              key={idx}
              className="group relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur-md transition-all hover:border-slate-700 hover:bg-slate-900/60"
            >
              <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity duration-300 from-cyan-500 to-indigo-500" />
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-xl font-bold text-white group-hover:text-cyan-400 transition-colors">
                    {mod.name}
                  </h3>
                  <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider mt-0.5">
                    {mod.role}
                  </p>
                </div>
                <span className="text-xs font-medium px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300">
                  {mod.status}
                </span>
              </div>
              <p className="text-sm text-slate-400 leading-relaxed">{mod.desc}</p>
            </div>
          ))}
        </div>

        {/* Verified Environment Section */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/20 p-6 backdrop-blur-md">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <svg
              className="w-5 h-5 text-indigo-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            Initialized Workspace Blueprint
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-400">
              <thead>
                <tr className="border-b border-slate-800 text-slate-500 font-semibold uppercase tracking-wider text-xs">
                  <th className="pb-3">Component / Folder</th>
                  <th className="pb-3">Day 1 Role</th>
                  <th className="pb-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/40">
                {files.map((file, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/10">
                    <td className="py-3 font-mono text-cyan-400/90 text-xs">{file.path}</td>
                    <td className="py-3 text-slate-300 font-medium">{file.type}</td>
                    <td className="py-3 text-right text-emerald-400 font-semibold text-xs flex items-center justify-end gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                      Created
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-xs text-slate-600 font-medium">
          AgentShield &bull; Day 1 Buildathon Framework &bull; Designed for Scalable AI Authorization
        </div>
      </div>
    </div>
  );
}
