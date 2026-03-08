import React from 'react';
import { ExternalLink, CheckCircle, AlertTriangle, DollarSign, Award, Target, MapPin } from 'lucide-react';

export default function VendorCard({ vendor }) {
  if (!vendor) return null;

  const getScoreColor = (score) => {
    if (score >= 70) return 'text-green-600';
    if (score >= 50) return 'text-amber-500';
    return 'text-red-500';
  };

  const getBgColor = (score) => {
    if (score >= 70) return 'bg-green-500';
    if (score >= 50) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden animate-fade-in-up">
      {/* Header */}
      <div className="p-6 border-b border-gray-100 flex justify-between items-start bg-gradient-to-br from-white to-gray-50">
        <div>
          <h3 className="text-xl font-bold text-gray-900 group-hover:text-brand-600 transition-colors">
            {vendor.vendor_name}
          </h3>
          <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500 pr-4">
            {vendor.country && (
              <span className="flex items-center">
                <MapPin className="w-4 h-4 mr-1 text-gray-400" /> {vendor.country}
              </span>
            )}
            {vendor.website && (
              <a href={vendor.website} target="_blank" rel="noopener noreferrer" className="flex items-center text-brand-600 hover:text-brand-800 transition-colors">
                <ExternalLink className="w-4 h-4 mr-1" /> Visit Site
              </a>
            )}
          </div>
        </div>
        <div className="flex flex-col items-end flex-shrink-0">
          <div className={`text-3xl font-black ${getScoreColor(vendor.final_score)}`}>
            {vendor.final_score?.toFixed(1) || '0.0'}
          </div>
          <span className="text-xs text-gray-500 font-semibold uppercase tracking-wider">Overall Score</span>
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Core Metrics */}
        <div className="grid grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <div className="flex items-center mb-2">
              <DollarSign className="w-4 h-4 mr-1.5 text-blue-500" />
              <span className="text-xs font-bold text-gray-600 uppercase">Cost</span>
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">{vendor.cost_score?.toFixed(1) || 'N/A'}</div>
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div className={`h-1.5 rounded-full ${getBgColor(vendor.cost_score)}`} style={{ width: `${Math.min(Math.max(vendor.cost_score || 0, 0), 100)}%` }}></div>
            </div>
          </div>
          
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <div className="flex items-center mb-2">
              <CheckCircle className="w-4 h-4 mr-1.5 text-green-500" />
              <span className="text-xs font-bold text-gray-600 uppercase">Rel.</span>
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">{vendor.reliability_score?.toFixed(1) || 'N/A'}</div>
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div className={`h-1.5 rounded-full ${getBgColor(vendor.reliability_score)}`} style={{ width: `${Math.min(Math.max(vendor.reliability_score || 0, 0), 100)}%` }}></div>
            </div>
          </div>
          
          <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
            <div className="flex items-center mb-2">
              <AlertTriangle className="w-4 h-4 mr-1.5 text-amber-500" />
              <span className="text-xs font-bold text-gray-600 uppercase">Risk</span>
            </div>
            <div className="text-2xl font-bold text-gray-900 mb-1">{vendor.risk_score?.toFixed(1) || 'N/A'}</div>
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div className={`h-1.5 rounded-full ${getBgColor(100 - vendor.risk_score)}`} style={{ width: `${Math.min(Math.max(vendor.risk_score || 0, 0), 100)}%` }}></div>
            </div>
          </div>
        </div>

        {/* AI Explanations */}
        {vendor.risk_reasoning && (
          <div>
            <h4 className="flex items-center text-sm font-bold text-gray-900 mb-2">
              <AlertTriangle className="w-4 h-4 text-amber-500 mr-2" /> Risk Profile Analysis
            </h4>
            <p className="text-sm text-gray-600 leading-relaxed bg-amber-50/50 p-4 rounded-lg border border-amber-100/50">
              {vendor.risk_reasoning}
            </p>
          </div>
        )}

        {vendor.reliability_reasoning && (
          <div>
            <h4 className="flex items-center text-sm font-bold text-gray-900 mb-2">
              <CheckCircle className="w-4 h-4 text-green-500 mr-2" /> Reliability Assessment
            </h4>
            <p className="text-sm text-gray-600 leading-relaxed bg-green-50/50 p-4 rounded-lg border border-green-100/50">
              {vendor.reliability_reasoning}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
