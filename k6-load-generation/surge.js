import http from "k6/http";
export const options = {
  scenarios: { surge: {
    executor: "ramping-arrival-rate", startRate: 0, timeUnit: "1s",
    preAllocatedVUs: 15, maxVUs: 120,
    stages: [
      { target: 0, duration: "20s" },
      { target: 100, duration: "20s" },
      { target: 100, duration: "90s" },
      { target: 0, duration: "10s" },
    ],
  }},
  thresholds: { http_req_duration: ["p(95)<1000", "p(99)<2000"], http_req_failed: ["rate<0.15"] },
};
export default function () {
  http.get(`${__ENV.BASE_URL}/products`);
  http.get(`${__ENV.BASE_URL}/products/search?q=mouse`);
  // 40% chance of order
  if (Math.random() < 0.4) {
    http.post(`${__ENV.BASE_URL}/orders`, JSON.stringify({ product_id: Math.floor(Math.random() * 8) + 1, quantity: 1 }),
      { headers: { "Content-Type": "application/json" } });
  }
  // 10% failure injection for error rate panel
  if (Math.random() < 0.1) {
    http.get(`${__ENV.BASE_URL}/nonexistent`);
    http.post(`${__ENV.BASE_URL}/orders`, JSON.stringify({ product_id: 999 }),
      { headers: { "Content-Type": "application/json" } });
  }
}
