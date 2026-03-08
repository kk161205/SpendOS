import { render, screen } from '../../test/test-utils'
import { describe, it, expect } from 'vitest'
import DashboardLayout from '../Dashboard/DashboardLayout'

describe('DashboardLayout', () => {
  it('renders the header and footer correctly', () => {
    render(<DashboardLayout />)
    // Looking for text in the footer
    expect(screen.getByText(/Smart Procurement Platform. All rights reserved./i)).toBeInTheDocument()
    expect(screen.getByText(/Privacy/i)).toBeInTheDocument()
    expect(screen.getByText(/Terms/i)).toBeInTheDocument()
  })
})
