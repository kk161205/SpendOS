import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useSession } from '../../context/SessionContext';
import { PlusCircle, FileSearch } from 'lucide-react';
import SessionCard from './SessionCard';

export default function SessionList() {
  const { user } = useAuth();
  const { sessions, deleteSession } = useSession();
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, {user?.full_name || user?.email?.split('@')[0] || 'User'}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Here's an overview of your recent procurement analyses.
          </p>
        </div>
        <button
          onClick={() => navigate('/dashboard/new')}
          className="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-brand-600 hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-500 transition-colors"
        >
          <PlusCircle className="h-5 w-5 mr-2" />
          New Analysis
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="mt-8 bg-white border-2 border-dashed border-gray-300 rounded-xl p-12 text-center">
          <div className="mx-auto h-16 w-16 bg-gray-50 text-gray-400 rounded-full flex items-center justify-center mb-4">
            <FileSearch className="h-8 w-8" />
          </div>
          <h3 className="mt-2 text-lg font-medium text-gray-900">No analyses yet</h3>
          <p className="mt-1 text-sm text-gray-500 max-w-sm mx-auto">
            Get started by creating your first vendor intelligence analysis. We'll evaluate risks, reliability, and costs for you.
          </p>
          <div className="mt-6">
            <button
              onClick={() => navigate('/dashboard/new')}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-brand-600 hover:bg-brand-700"
            >
              <PlusCircle className="h-4 w-4 mr-2" />
              Start First Analysis
            </button>
          </div>
        </div>
      ) : (
        <div className="mt-8 grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
          {sessions.map((session) => (
            <SessionCard 
              key={session.id} 
              session={session} 
              onDelete={() => deleteSession(session.id)} 
            />
          ))}
        </div>
      )}
    </div>
  );
}
