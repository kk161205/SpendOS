import { http, HttpResponse } from 'msw'

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || 'http://localhost:8000/api'

export const handlers = [
  // Mock Login endpoint
  http.post(`${API_BASE_URL}/auth/token`, async ({ request }) => {
    // We expect form data username and password
    return HttpResponse.json({
      access_token: 'fake-jwt-token-for-testing',
      token_type: 'bearer'
    })
  }),

  // Mock Analyze Procurement endpoint
  http.post(`${API_BASE_URL}/procurement/analyze`, async ({ request }) => {
    return HttpResponse.json({
      request_id: '1234',
      product_name: 'Test Product',
      status: 'completed',
      total_vendors_evaluated: 1,
      ai_explanation: 'This is a mocked AI response.',
      ranked_vendors: [
        {
          vendor_id: 'v-1',
          vendor_name: 'Mocked Vendor Inc',
          cost_score: 90,
          risk_score: 10,
          reliability_score: 95,
          final_score: 92,
          rank: 1
        }
      ]
    })
  })
]
