import React, { useState } from 'react';
import VendorCard from './VendorCard';

export default function VendorRankings({ vendors = [] }) {
  const [expandedVendorId, setExpandedVendorId] = useState(vendors[0]?.vendor_id || null);

  if (!vendors.length) {
    return (
      <div className="text-center py-12 text-gray-500">
        No vendors could be thoroughly evaluated for this query.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-bold text-gray-900">Ranked Vendors ({vendors.length})</h2>
        <div className="text-sm text-gray-500">Sorted by best composite score</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-start">
        {/* Left column: List of vendors */}
        <div className="md:col-span-5 flex flex-col space-y-3">
          {vendors.map((vendor, index) => {
            const isSelected = expandedVendorId === vendor.vendor_id;
            return (
              <button
                key={vendor.vendor_id}
                onClick={() => setExpandedVendorId(vendor.vendor_id)}
                className={`
                  w-full text-left transition-all duration-200 flex items-center p-4 border rounded-xl 
                  ${isSelected
                    ? 'border-brand-500 bg-brand-50 ring-1 ring-brand-500 shadow-sm' 
                    : 'border-gray-200 bg-white hover:border-brand-300 hover:bg-gray-50'}
                `}
              >
                <div className={`
                  flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold mr-4
                  ${index === 0 ? 'bg-yellow-100 text-yellow-700 border-2 border-yellow-200' : 
                    index === 1 ? 'bg-gray-200 text-gray-700' :
                    index === 2 ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-500'}
                `}>
                  #{index + 1}
                </div>
                <div className="flex-1 min-w-0 pr-2">
                  <h4 className="text-sm font-bold text-gray-900 truncate">{vendor.vendor_name}</h4>
                  <p className="text-xs text-gray-500">{vendor.country || 'Unknown location'}</p>
                </div>
                <div className="flex flex-col items-end flex-shrink-0">
                  <span className={`text-lg font-black ${
                    vendor.final_score >= 70 ? 'text-green-600' : 
                    vendor.final_score >= 50 ? 'text-amber-500' : 'text-red-500'
                  }`}>
                    {vendor.final_score.toFixed(1)}
                  </span>
                  <span className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">Score</span>
                </div>
              </button>
            )
          })}
        </div>

        {/* Right column: Details panel (VendorCard) */}
        <div className="md:col-span-7 sticky top-24">
          {vendors.map((vendor) => (
            vendor.vendor_id === expandedVendorId && (
              <VendorCard key={vendor.vendor_id} vendor={vendor} />
            )
          ))}
        </div>
      </div>
    </div>
  );
}
