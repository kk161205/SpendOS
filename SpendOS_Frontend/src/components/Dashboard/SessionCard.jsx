import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ShoppingCart, Calendar, TrendingUp, AlertTriangle, CheckCircle, ChevronRight, BarChart2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function SessionCard({ session }) {
  const navigate = useNavigate();

  // Handle click to view results
  const handleView = () => {
    navigate(`/dashboard/results`, { state: { session } });
  };

  // Safe formatting for scores
  const getTopVendor = () => {
    if (!session.results?.ranked_vendors?.length) return null;
    return session.results.ranked_vendors[0];
  };

  const topVendor = getTopVendor();
  const dateStr = session.timestamp ? formatDistanceToNow(new Date(session.timestamp), { addSuffix: true }) : 'Recently';

  const getScoreColor = (score) => {
    if (score >= 70) return 'text-green-600 bg-green-50 border-green-200';
    if (score >= 50) return 'text-amber-600 bg-amber-50 border-amber-200';
    return 'text-red-600 bg-red-50 border-red-200';
  };

  return (
    <div 
      className="bg-white rounded-xl shadow-sm border border-gray-200 hover:shadow-lg transition-all duration-200 overflow-hidden cursor-pointer group flex flex-col"
      onClick={handleView}
    >
      <div className="p-5 flex-grow">
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-brand-50 rounded-lg text-brand-600">
              <ShoppingCart className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 group-hover:text-brand-600 transition-colors line-clamp-1">
                {session.product_name}
              </h3>
              <div className="flex items-center text-xs text-gray-500 mt-1">
                <span className="font-medium text-brand-600 uppercase tracking-wider">{session.category}</span>
                <span className="mx-2">•</span>
                <Calendar className="w-3 h-3 mr-1" />
                {dateStr}
              </div>
            </div>
          </div>
        </div>

        {topVendor ? (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-100">
            <div className="text-xs text-gray-500 uppercase font-semibold tracking-wider mb-2">Top Recommended Vendor</div>
            <div className="flex items-center justify-between">
              <div className="font-medium text-gray-900 truncate pr-2">{topVendor.vendor_name}</div>
              <div className={`px-2.5 py-1 flex items-center rounded-md border font-bold text-sm ${getScoreColor(topVendor.final_score)}`}>
                {topVendor.final_score.toFixed(1)}
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-gray-200">
              <div className="flex flex-col">
                <span className="text-[10px] text-gray-500 flex items-center"><TrendingUp className="w-3 h-3 mr-1"/> Cost</span>
                <span className="text-xs font-semibold text-gray-900 mt-0.5">{topVendor.cost_score?.toFixed(0) || '-'}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-gray-500 flex items-center"><CheckCircle className="w-3 h-3 mr-1"/> Rel.</span>
                <span className="text-xs font-semibold text-gray-900 mt-0.5">{topVendor.reliability_score?.toFixed(0) || '-'}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-gray-500 flex items-center"><AlertTriangle className="w-3 h-3 mr-1"/> Risk</span>
                <span className="text-xs font-semibold text-gray-900 mt-0.5">{topVendor.risk_score?.toFixed(0) || '-'}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-100 flex items-center justify-center text-sm text-gray-500 italic">
            No vendor data available
          </div>
        )}
      </div>
      
      <div className="px-5 py-3 bg-gray-50 border-t border-gray-100 flex justify-between items-center text-sm">
        <span className="text-gray-500 flex items-center">
          <BarChart2 className="w-4 h-4 mr-1" />
          {session.results?.total_vendors_evaluated || 0} vendors evaluated
        </span>
        <span className="text-brand-600 font-medium flex items-center opacity-0 group-hover:opacity-100 transform translate-x-2 group-hover:translate-x-0 transition-all duration-200">
          View Results <ChevronRight className="w-4 h-4 ml-1" />
        </span>
      </div>
    </div>
  );
}
