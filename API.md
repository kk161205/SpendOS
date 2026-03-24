# 📖 SpendOS API Documentation

SpendOS provides a RESTful API for managing user sessions and triggering AI-driven procurement analyses.

---

## 🔐 Authentication

SpendOS uses **JWT Authentication** stored in **HttpOnly Cookies**.

### 1. User Registration
`POST /api/auth/register`
- **Payload**:
  ```json
  {
    "email": "user@example.com",
    "password": "Password123!",
    "full_name": "SpendOS User"
  }
  ```

### 2. User Login
`POST /api/auth/token` (Form Data)
- **Response**: `200 OK` with 3 HttpOnly cookies (`access_token`, `refresh_token`, `csrf_token`) and a JSON object containing the `csrf_token` for the header.

---

## 🔎 Procurement Analysis

### 1. Trigger Analysis
`POST /api/procurement/analyze`
- **Payload**:
  ```json
  {
    "product_name": "Solar Inverters (5kW)",
    "product_category": "Energy Infrastructure",
    "quantity": 50,
    "budget_usd": 25000,
    "shipping_destination": "Nairobi, Kenya",
    "delivery_deadline_days": 30
  }
  ```
- **Response**:
  ```json
  {
    "task_id": "8dc643dc-2721-4b37-bbfb-61cacc47a67e",
    "status": "pending"
  }
  ```

### 2. Real-time Status (SSE)
`GET /api/procurement/events/{task_id}`
- **Description**: Streams JSON updates as the AI pipeline progresses through discovery, scoring, and ranking.

### 3. Historical Data
`GET /api/procurement/history`
- **Output**: A paginated list of all past analyses.

---

## 📊 CSV Export

`GET /api/procurement/export/{session_id}`
- **Description**: Generates and streams a CSV report for the specified session.
- **Headers**: `Content-Disposition: attachment; filename=procurement_results_...csv`
