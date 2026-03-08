import React, { useState } from "react";
import { useLocation, useNavigate, Navigate } from "react-router-dom";
import VendorRankings from "./VendorRankings";
import ScoreBreakdown from "./ScoreBreakdown";
import AIExplanation from "./AIExplanation";
import { ArrowLeft, FileText, CheckCircle, Save, Download } from "lucide-react";

export default function ResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const session = location.state?.session;

  const [activeTab, setActiveTab] = useState("rankings");

  // If navigated directly without session state, redirect back
  if (!session || !session.results) {
    return <Navigate to="/dashboard" replace />;
  }

  const results = session.results;

  return (
    <div className="max-w-7xl mx-auto pb-12 animate-fade-in">
      {/* Header Bar */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <button
            onClick={() => navigate("/dashboard")}
            className="flex items-center text-sm font-medium text-gray-500 hover:text-brand-600 mb-2 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 mr-1" /> Back to Dashboard
          </button>
          <h1 className="text-3xl font-extrabold text-gray-900 flex items-center tracking-tight">
            Analysis Results
          </h1>
          <p className="mt-1 text-sm font-medium text-brand-600 flex items-center uppercase tracking-widest gap-2">
            <span>{session.product_name}</span>
            <span className="text-gray-300">•</span>
            <span>{session.category}</span>
          </p>
        </div>
      </div>

      {/* Tabs Layout */}
      <div className="bg-white rounded-t-xl shadow-sm border-b border-gray-200">
        <nav className="-mb-px flex space-x-8 px-6" aria-label="Tabs">
          {[
            { id: "rankings", name: "Vendor Rankings" },
            { id: "breakdown", name: "Metrics Breakdown" },
            { id: "ai", name: "AI Recommendation" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                whitespace-nowrap flex py-4 px-1 border-b-2 font-medium text-sm transition-colors
                ${
                  activeTab === tab.id
                    ? "border-brand-500 text-brand-600"
                    : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
                }
              `}
            >
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Content Area */}
      <div className="p-6 sm:p-8 bg-white/50 border border-t-0 border-gray-200 rounded-b-xl min-h-[500px] shadow-sm backdrop-blur-md">
        {activeTab === "rankings" && (
          <VendorRankings vendors={results.ranked_vendors} />
        )}
        {activeTab === "breakdown" && <ScoreBreakdown results={results} />}
        {activeTab === "ai" && (
          <AIExplanation explanation={results.ai_explanation} />
        )}
      </div>
    </div>
  );
}
