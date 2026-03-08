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

        {/* Weights Graphic */}
        <div className="bg-gray-50 rounded-2xl p-6 border border-gray-100">
          <h3 className="text-lg font-bold text-gray-900 flex items-center mb-6">
            <Target className="w-5 h-5 mr-2 text-brand-600" /> Decision Weight Allocations
          </h3>
          <div className="space-y-6 mt-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-semibold flex items-center text-gray-700">
                  <TrendingUp className="w-4 h-4 mr-2 text-blue-500" /> Cost Sensitivity
                </span>
                <span className="text-sm font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded">{(weights.cost_weight * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${weights.cost_weight * 100}%` }}></div>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-semibold flex items-center text-gray-700">
                  <Award className="w-4 h-4 mr-2 text-green-500" /> Reliability Focus
                </span>
                <span className="text-sm font-bold bg-green-100 text-green-800 px-2 py-0.5 rounded">{(weights.reliability_weight * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-green-500 h-2 rounded-full" style={{ width: `${weights.reliability_weight * 100}%` }}></div>
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm font-semibold flex items-center text-gray-700">
                  <ShieldAlert className="w-4 h-4 mr-2 text-amber-500" /> Risk Aversion
                </span>
                <span className="text-sm font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded">{(weights.risk_weight * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-amber-500 h-2 rounded-full" style={{ width: `${weights.risk_weight * 100}%` }}></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
