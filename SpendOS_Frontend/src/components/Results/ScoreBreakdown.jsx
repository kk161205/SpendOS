import React from 'react';
import { Target, TrendingUp, ShieldAlert, Award, FileText } from 'lucide-react';

export default function ScoreBreakdown({ results }) {
  if (!results) return null;

  const weights = results.scoring_weights_used || { cost_weight: 0.35, reliability_weight: 0.40, risk_weight: 0.25 };
  const evaluatedCount = results.total_vendors_evaluated || results.ranked_vendors?.length || 0;

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Analysis Profile Overview */}
        <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 flex items-center mb-6">
            <FileText className="w-5 h-5 mr-2 text-brand-600" /> Sourcing Scope Summary
          </h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-gray-200">
              <span className="text-sm text-gray-500 font-medium">Vendors Evaluated</span>
              <span className="text-base font-bold text-gray-900">{evaluatedCount}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-gray-200">
              <span className="text-sm text-gray-500 font-medium">Category</span>
              <span className="text-base font-bold text-brand-600">{results.product_category || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-gray-200">
              <span className="text-sm text-gray-500 font-medium">Analyzed Product</span>
              <span className="text-sm font-semibold text-gray-900 text-right max-w-xs">{results.product_name}</span>
            </div>
          </div>
        </div>

        {/* Weights Graphic - Pie Chart */}
        <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100 flex flex-col h-full">
          <h3 className="text-lg font-bold text-gray-900 flex items-center mb-8">
            <Target className="w-5 h-5 mr-2 text-brand-600" /> Decision Weight Allocations
          </h3>

          <div className="flex flex-col sm:flex-row items-center justify-around gap-8 flex-grow">
            {/* Pie Chart SVG */}
            <div className="relative w-48 h-48 drop-shadow-md">
              <svg viewBox="0 0 32 32" className="w-full h-full -rotate-90">
                {/* Reliability Segment (Green) */}
                <circle
                  cx="16" cy="16" r="15.915494"
                  fill="transparent"
                  stroke="#22c55e"
                  strokeWidth="3.5"
                  strokeDasharray={`${weights.reliability_weight * 100} 100`}
                />
                {/* Cost Segment (Blue) */}
                <circle
                  cx="16" cy="16" r="15.915494"
                  fill="transparent"
                  stroke="#3b82f6"
                  strokeWidth="3.5"
                  strokeDasharray={`${weights.cost_weight * 100} 100`}
                  strokeDashoffset={`-${weights.reliability_weight * 100}`}
                />
                {/* Risk Segment (Amber) */}
                <circle
                  cx="16" cy="16" r="15.915494"
                  fill="transparent"
                  stroke="#f59e0b"
                  strokeWidth="3.5"
                  strokeDasharray={`${weights.risk_weight * 100} 100`}
                  strokeDashoffset={`-${(weights.reliability_weight + weights.cost_weight) * 100}`}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center flex-col">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-tighter">Total</span>
                <span className="text-xl font-black text-gray-800">100%</span>
              </div>
            </div>

            {/* Legend */}
            <div className="space-y-4 w-full sm:w-auto">
              <div className="flex items-center space-x-3 p-2 rounded-lg hover:bg-white transition-colors">
                <div className="w-3 h-3 rounded-full bg-blue-500 shadow-sm shadow-blue-200"></div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-gray-500 uppercase">Cost Sensitivity</span>
                  <span className="text-sm font-bold text-gray-900">{(weights.cost_weight * 100).toFixed(0)}%</span>
                </div>
              </div>
              <div className="flex items-center space-x-3 p-2 rounded-lg hover:bg-white transition-colors">
                <div className="w-3 h-3 rounded-full bg-green-500 shadow-sm shadow-green-200"></div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-gray-500 uppercase">Reliability Focus</span>
                  <span className="text-sm font-bold text-gray-900">{(weights.reliability_weight * 100).toFixed(0)}%</span>
                </div>
              </div>
              <div className="flex items-center space-x-3 p-2 rounded-lg hover:bg-white transition-colors">
                <div className="w-3 h-3 rounded-full bg-amber-500 shadow-sm shadow-amber-200"></div>
                <div className="flex flex-col">
                  <span className="text-xs font-bold text-gray-500 uppercase">Risk Aversion</span>
                  <span className="text-sm font-bold text-gray-900">{(weights.risk_weight * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}